from __future__ import annotations

import json
import uuid
import pytest
from starlette.testclient import TestClient

from browser_agent.config import get_settings
from browser_agent.api import create_app
from browser_agent.crypto.kms import (
    LocalKmsProvider,
    AwsKmsProvider,
    VaultKmsProvider,
    encrypt_session_vault_payload,
    decrypt_session_vault_payload,
)
from browser_agent.services.self_healing import HeuristicSelfHealingEngine
from browser_agent.services.live_telemetry import LiveTelemetryBroadcaster, ExecutionAbortedException
from browser_agent.auth import (
    generate_oidc_pkce,
    build_oidc_auth_url,
    exchange_oidc_code_for_token,
    create_access_token,
    ActorContext,
)
from browser_agent.orchestrator import Orchestrator


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed = True

    def commit(self):
        pass


class FakeBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, key, payload):
        self.published.append((topic, key, payload))


class FakeElement:
    def __init__(self, visible=True):
        self._visible = visible
        self.clicked = False
        self.filled_value = None

    def count(self):
        return 1 if self._visible else 0

    def is_visible(self, timeout=None):
        return self._visible

    def click(self, timeout=None):
        self.clicked = True

    def fill(self, val, timeout=None):
        self.filled_value = val


class FakePage:
    def __init__(self, candidates=None, visible_selectors=None):
        self.candidates = candidates or []
        self.visible_selectors = visible_selectors or {}

    def locator(self, sel):
        return self

    @property
    def first(self):
        return self

    def count(self):
        return 1 if self.visible_selectors.get(getattr(self, "_current_sel", "")) else 0

    def is_visible(self, timeout=None):
        return self.visible_selectors.get(getattr(self, "_current_sel", ""), False)

    def __call__(self, sel):
        self._current_sel = sel
        return self

    def evaluate(self, script):
        return self.candidates


# --- 1. KMS Envelope Encryption 測試 ---

def test_kms_local_provider_envelope_encryption_roundtrip():
    provider = LocalKmsProvider("01234567890123456789012345678901", default_key_id="kek-v1")
    raw_payload = {"cookies": [{"name": "session_id", "value": "secret_abc"}], "origins": []}
    tenant_id = "tenant-enterprise-1"

    ciphertext, meta = encrypt_session_vault_payload(raw_payload, tenant_id=tenant_id, provider=provider)
    assert meta["encryption"]["encrypted"] is True
    assert meta["encryption"]["algorithm"] == "AES-256-GCM"
    assert meta["encryption"]["kms_provider"] == "local"
    assert "encrypted_dek" in meta["encryption"]

    # 成功解密
    decrypted = decrypt_session_vault_payload(ciphertext, meta, tenant_id=tenant_id, provider=provider)
    assert decrypted == raw_payload

    # 跨租戶竄改測試：使用不同 tenant_id 解密時應被 AAD 拒絕
    with pytest.raises(ValueError, match="failed to decrypt session vault payload"):
        decrypt_session_vault_payload(ciphertext, meta, tenant_id="tenant-attacker-2", provider=provider)


def test_kms_providers_status_and_mock_capabilities():
    local = LocalKmsProvider("01234567890123456789012345678901")
    assert local.status()["status"] == "active"

    aws = AwsKmsProvider("arn:aws:kms:us-east-1:123456789012:key/test-key")
    assert aws.status()["provider"] == "aws"

    vault = VaultKmsProvider("http://localhost:8200", "token", "transit-key")
    assert vault.status()["provider"] == "vault"


# --- 2. Heuristic Self-Healing 測試 ---

def test_heuristic_self_healing_fallback_cascade():
    engine = HeuristicSelfHealingEngine(confidence_threshold=0.6)

    class MockPageFallback:
        def locator(self, sel):
            class Loc:
                def __init__(self, s):
                    self.s = s
                @property
                def first(self):
                    return self
                def count(self):
                    return 1 if self.s == "#fallback-btn" else 0
                def is_visible(self, timeout=None):
                    return self.s == "#fallback-btn"
            return Loc(sel)

    page = MockPageFallback()
    loc, heal_info = engine.resolve_target(
        page=page,
        target="#missing-primary-btn",
        action="click",
        fallback_selectors=["#secondary-missing", "#fallback-btn"],
    )
    assert heal_info is not None
    assert heal_info["self_healed"] is True
    assert heal_info["strategy"] == "fallback_cascade"
    assert heal_info["repaired_target"] == "#fallback-btn"


def test_heuristic_self_healing_dom_feature_matching():
    engine = HeuristicSelfHealingEngine(confidence_threshold=0.5)

    class MockPageDOM:
        def locator(self, sel):
            class Loc:
                def __init__(self, s):
                    self.s = s
                @property
                def first(self):
                    return self
                def count(self):
                    return 1 if "login" in self.s or "Submit" in self.s or "auth" in self.s else 0
                def is_visible(self, timeout=None):
                    return False  # 主選擇器一律不可見
            return Loc(sel)

        def evaluate(self, script):
            # 模擬 DOM 中的按鈕候選清單
            return [
                {
                    "index": 0,
                    "tag": "button",
                    "type": "submit",
                    "text": "Sign In to Account",
                    "id": "btn-login-submit",
                    "name": "login_submit",
                    "aria_label": "Submit Login",
                    "role": "button",
                    "class_name": "btn btn-primary",
                    "placeholder": "",
                    "is_visible": True,
                }
            ]

    page = MockPageDOM()
    loc, heal_info = engine.resolve_target(
        page=page,
        target="#old-login-button",
        action="click",
        instruction="Click the login button to continue",
    )
    assert heal_info is not None
    assert heal_info["self_healed"] is True
    assert heal_info["strategy"] == "heuristic_feature_match"
    assert "#btn-login-submit" in heal_info["repaired_target"] or "login" in heal_info["repaired_target"]
    assert heal_info["confidence"] >= 0.5


# --- 3. Multi-Priority Queues 測試 ---

def test_multi_priority_queue_routing_high_and_batch():
    session = FakeSession()
    bus = FakeBus()
    orch = Orchestrator(session, bus)

    class MockTask:
        def __init__(self, priority):
            self.id = uuid.uuid4()
            self.tenant_id = uuid.uuid4()
            self.status = "pending_approval"
            self.priority = priority
            self.approved_by = None
            self.approved_at = None
            self.correlation_id = "test-cid"
            self.metadata_ = {}

    # 1. 高優先級任務 (priority=10)
    high_task = MockTask(priority=10)
    orch.approve_task(high_task, uuid.uuid4(), "approver@example.com", "Approve high")
    assert bus.published[0][0] == "agent.tasks.high"
    assert bus.published[0][2]["priority"] == 10

    # 2. 批次低優先級任務 (priority=-1)
    batch_task = MockTask(priority=-1)
    orch.approve_task(batch_task, uuid.uuid4(), "approver@example.com", "Approve batch")
    assert bus.published[1][0] == "agent.tasks.batch"
    assert bus.published[1][2]["priority"] == -1

    # 3. 預設標準任務 (priority=0)
    default_task = MockTask(priority=0)
    orch.approve_task(default_task, uuid.uuid4(), "approver@example.com", "Approve default")
    assert bus.published[2][0] == "agent.tasks.queued"
    assert bus.published[2][2]["priority"] == 0


# --- 4. Live Telemetry & Abort 測試 ---

def test_live_telemetry_broadcaster_publish_and_abort():
    broadcaster = LiveTelemetryBroadcaster()
    task_id = str(uuid.uuid4())

    # 發布畫面幀
    test_frame = b"fake_jpeg_binary_bytes_12345"
    broadcaster.publish_frame(task_id, test_frame, step_no=1, action="click", url="https://example.com")

    latest = broadcaster.get_latest_frame(task_id)
    assert latest is not None
    assert latest["task_id"] == task_id
    assert latest["step_no"] == 1
    assert "data:image/jpeg;base64," in latest["data"]

    # Abort 標記與查詢
    assert broadcaster.is_aborted(task_id) is False
    broadcaster.request_abort(task_id, reason="Emergency cancel")
    assert broadcaster.is_aborted(task_id) is True
    assert broadcaster.get_abort_info(task_id)["reason"] == "Emergency cancel"


# --- 5. OIDC PKCE & Auth Code 流程測試 ---

def test_oidc_pkce_and_auth_url():
    state, verifier, challenge = generate_oidc_pkce()
    assert len(state) >= 16
    assert len(verifier) >= 32
    assert len(challenge) >= 32

    settings = get_settings()
    auth_url = build_oidc_auth_url(settings, state, challenge)
    assert "response_type=code" in auth_url
    assert f"state={state}" in auth_url
    assert f"code_challenge={challenge}" in auth_url

    # 測試 Mock Exchange 回調交換
    tokens = exchange_oidc_code_for_token(settings, "mock-code", verifier)
    assert "email" in tokens
    assert "roles" in tokens


# --- 6. V1.3 API 端點整合測試 ---

def test_v13_api_endpoints():
    app = create_app()
    client = TestClient(app)

    # 測試 OIDC login 導頁端點
    login_resp = client.get("/v1/auth/oidc/login")
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "auth_url" in data
    assert "state" in data

    # 測試 OIDC callback 端點並獲取 Session Cookie
    state = data["state"]
    cb_resp = client.get(f"/v1/auth/oidc/callback?code=test-code-123&state={state}")
    assert cb_resp.status_code == 200
    cb_data = cb_resp.json()
    assert cb_data["authenticated"] is True
    assert "ba_session" in cb_resp.cookies

    # 測試使用 ba_session Cookie 造訪受保護端點
    me_resp = client.get("/v1/auth/me", cookies={"ba_session": cb_resp.cookies["ba_session"]})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == cb_data["email"]

    # 測試 Logout 清除 Cookie
    logout_resp = client.post("/v1/auth/logout")
    assert logout_resp.status_code == 200

    # 測試 KMS 狀態端點
    actor = ActorContext(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="ops@example.com",
        roles=("admin",),
    )
    admin_token = create_access_token(actor, settings=get_settings())
    headers = {"Authorization": f"Bearer {admin_token}"}

    kms_resp = client.get("/v1/ops/kms/status", headers=headers)
    assert kms_resp.status_code == 200
    assert kms_resp.json()["status"] == "active"

    # 測試 Queues 狀態端點
    queues_resp = client.get("/v1/ops/queues", headers=headers)
    assert queues_resp.status_code == 200
    assert queues_resp.json()["multi_priority_enabled"] is True
    assert "agent.tasks.high" in queues_resp.json()["topics"]["high"]

    # 測試 Live Frame 端點
    task_id = str(uuid.uuid4())
    frame_resp = client.get(f"/v1/tasks/{task_id}/live-frame", headers=headers)
    assert frame_resp.status_code == 200
    assert frame_resp.json()["frame_available"] is False


# --- 7. Helm Chart 檔案結構與 YAML 語法校驗 ---

def test_helm_chart_files_structure():
    import os
    import yaml

    helm_dir = os.path.join("deploy", "helm", "browser-agent")
    assert os.path.isdir(helm_dir)

    # 驗證 Chart.yaml
    chart_path = os.path.join(helm_dir, "Chart.yaml")
    assert os.path.isfile(chart_path)
    with open(chart_path, "r", encoding="utf-8") as f:
        chart_data = yaml.safe_load(f)
    assert chart_data["name"] == "browser-agent"
    assert chart_data["version"] in {"1.3.0", "1.4.0"}
    assert chart_data["appVersion"] in {"1.3.0", "1.4.0"}

    # 驗證 values.yaml
    values_path = os.path.join(helm_dir, "values.yaml")
    assert os.path.isfile(values_path)
    with open(values_path, "r", encoding="utf-8") as f:
        values_data = yaml.safe_load(f)
    assert "replicaCount" in values_data
    assert "config" in values_data
    assert values_data["config"]["multiPriorityEnabled"] is True
    assert values_data["config"]["selfHealingEnabled"] is True

    # 驗證 templates 目錄下的關鍵清單
    templates_dir = os.path.join(helm_dir, "templates")
    expected_files = [
        "_helpers.tpl",
        "configmap.yaml",
        "secret.yaml",
        "api-deployment.yaml",
        "worker-deployment.yaml",
        "service.yaml",
        "ingress.yaml",
        "keda-scaledobject.yaml",
        "servicemonitor.yaml",
    ]
    for ef in expected_files:
        assert os.path.isfile(os.path.join(templates_dir, ef)), f"Missing Helm template: {ef}"

    # 驗證 GitOps 範本
    gitops_file = os.path.join("deploy", "gitops", "argocd-application.yaml")
    assert os.path.isfile(gitops_file)
    with open(gitops_file, "r", encoding="utf-8") as f:
        gitops_data = yaml.safe_load(f)
    assert gitops_data["kind"] == "Application"
    assert gitops_data["metadata"]["name"] == "browser-agent-prod"


# --- 8. 向後相容性與生命週期進階測試 ---

def test_plaintext_session_backward_compatibility():
    """驗證舊版本未加密之明文 storage_state 仍可透明正常讀取"""
    legacy_payload = {"cookies": [{"name": "old_auth", "value": "legacy_val"}], "origins": []}
    legacy_bytes = json.dumps(legacy_payload).encode("utf-8")

    # 無 encryption metadata
    decrypted = decrypt_session_vault_payload(legacy_bytes, metadata={}, tenant_id="any-tenant")
    assert decrypted == legacy_payload


def test_task_abort_api_and_broadcaster_event():
    """驗證 Abort API 發起中斷與 Broadcaster 狀態連動"""
    from browser_agent import models
    import browser_agent.api as api

    app = create_app()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    task_id = uuid.uuid4()
    mock_task = models.Task(
        id=task_id,
        tenant_id=tenant_id,
        title="Test Abort",
        instructions="Run long task",
        risk_level="low",
        status="executing",
    )

    class _AbortFakeSession:
        def get(self, entity, eid):
            if entity is models.Task and eid == task_id:
                return mock_task
            return None
        def add(self, item): pass
        def commit(self): pass
        def close(self): pass

    app.dependency_overrides[api.get_session] = lambda: _AbortFakeSession()
    client = TestClient(app)

    actor = ActorContext(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        tenant_id=tenant_id,
        email="ops@example.com",
        roles=("admin",),
    )
    admin_token = create_access_token(actor, settings=get_settings())
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 呼叫 abort 端點
    abort_resp = client.post(f"/v1/tasks/{task_id}/abort", headers=headers)
    assert abort_resp.status_code == 200
    assert abort_resp.json()["aborted"] is True

    # 驗證 Broadcaster 收到 abort 標記
    from browser_agent.services.live_telemetry import get_telemetry_broadcaster
    broadcaster = get_telemetry_broadcaster()
    assert broadcaster.is_aborted(str(task_id)) is True


def test_session_validate_api_endpoint():
    """驗證 POST /v1/sessions/{session_name}/validate 成功與失敗場景"""
    from browser_agent import models
    import browser_agent.api as api

    app = create_app()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # 模擬 Session Artifact
    encrypted_bytes, enc_meta = encrypt_session_vault_payload(
        {"cookies": [{"name": "auth_token", "value": "xyz"}], "origins": []},
        tenant_id=str(tenant_id),
    )

    art = models.TaskArtifact(
        id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        artifact_type="storage_state",
        uri="test-vault://session1.enc",
        metadata_={
            "session_name": "corp-admin-sess",
            **enc_meta,
        },
    )

    class _SessionFakeDb:
        def execute(self, stmt):
            from types import SimpleNamespace
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [art]))
        def close(self): pass

    app.dependency_overrides[api.get_session] = lambda: _SessionFakeDb()

    # 模擬 artifact store read_bytes
    import browser_agent.services.artifacts as artifacts_svc
    original_builder = artifacts_svc.build_artifact_store_from_settings

    class FakeStore:
        def read_bytes(self, uri):
            return encrypted_bytes

    api.build_artifact_store_from_settings = lambda s: FakeStore()

    client = TestClient(app)
    actor = ActorContext(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        tenant_id=tenant_id,
        email="ops@example.com",
        roles=("admin",),
    )
    admin_token = create_access_token(actor, settings=get_settings())
    headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        # 1. 成功驗證
        val_resp = client.post("/v1/sessions/corp-admin-sess/validate", headers=headers)
        assert val_resp.status_code == 200
        assert val_resp.json()["valid"] is True
        assert val_resp.json()["cookies_count"] == 1
        assert val_resp.json()["encryption"]["encrypted"] is True

        # 2. 不存在的 Session 回傳 404
        val_404 = client.post("/v1/sessions/non-existent/validate", headers=headers)
        assert val_404.status_code == 404
    finally:
        api.build_artifact_store_from_settings = original_builder



