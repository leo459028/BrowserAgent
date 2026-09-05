from __future__ import annotations

import time
import uuid
import pytest
from starlette.testclient import TestClient

from browser_agent.config import get_settings
from browser_agent.api import create_app
from browser_agent.services.dlp import ZeroTrustDLPService, get_dlp_service
from browser_agent.services.federation import ClusterFederationManager, get_federation_manager
from browser_agent.services.live_telemetry import LiveTelemetryBroadcaster
from browser_agent.auth import create_access_token, ActorContext
from browser_agent.orchestrator import Orchestrator
from browser_agent import models


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = False
        self.tasks = {}

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.added.append(obj)
        if isinstance(obj, models.Task):
            self.tasks[obj.id] = obj

    def flush(self):
        self.flushed = True

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def get(self, entity, eid):
        if entity is models.Task:
            return self.tasks.get(eid)
        return None

    def execute(self, stmt):
        from types import SimpleNamespace
        tasks_list = list(self.tasks.values())
        if "matrix_id" in str(stmt):
            tasks_list = [t for t in tasks_list if getattr(t, "matrix_id", None) is not None]
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: tasks_list,
                first=lambda: tasks_list[0] if tasks_list else None,
            )
        )



class FakeBus:
    def __init__(self):
        self.published = []

    def publish(self, topic, key, payload):
        self.published.append((topic, key, payload))


class FakeLocator:
    def __init__(self, count_val=1):
        self._count = count_val

    def count(self):
        return self._count


class FakePage:
    def __init__(self, sensitive_count=2):
        self._sensitive_count = sensitive_count
        self.added_styles = []
        self.clicks = []
        self.typed_text = []

    def locator(self, selector):
        return FakeLocator(self._sensitive_count)

    def add_style_tag(self, content=None):
        self.added_styles.append(content)


# --- 1. 跨瀏覽器引擎與矩陣派發測試 ---

def test_cross_browser_matrix_task_creation_and_attributes():
    session = FakeSession()
    bus = FakeBus()
    orch = Orchestrator(session, bus)

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    matrix_id = "matrix-test-12345"

    for engine in ["chromium", "firefox", "webkit"]:
        payload = {
            "title": f"Test on {engine}",
            "instructions": "Open site and check page",
            "priority": 1,
            "risk_level": "low",
            "browser_engine": engine,
            "matrix_id": matrix_id,
            "metadata": {"start_url": "https://example.com", "browser_engine": engine, "matrix_id": matrix_id},
        }
        task = orch.create_task(tenant_id, user_id, payload)
        assert task.browser_engine == engine
        assert task.matrix_id == matrix_id
        assert task.status == "pending_approval"


# --- 2. 雙向即時遠端接管 (HITL) 測試 ---

def test_remote_takeover_broadcaster_pause_action_and_resume():
    broadcaster = LiveTelemetryBroadcaster()
    task_id = str(uuid.uuid4())

    # 1. 預設未暫停
    assert broadcaster.is_paused(task_id) is False

    # 2. 暫停進入 HITL 接管模式
    broadcaster.pause_task(task_id, operator="operator@example.com", reason="Solve captcha")
    assert broadcaster.is_paused(task_id) is True
    pause_info = broadcaster.get_pause_info(task_id)
    assert pause_info["operator"] == "operator@example.com"
    assert pause_info["reason"] == "Solve captcha"

    # 3. 下發反向操作指令 (點擊與鍵盤輸入)
    broadcaster.queue_action(task_id, {"action": "click", "x": 350.5, "y": 210.0})
    broadcaster.queue_action(task_id, {"action": "type", "text": "my_secure_code_123"})
    broadcaster.queue_action(task_id, {"action": "press", "key": "Enter"})

    actions = broadcaster.get_and_clear_pending_actions(task_id)
    assert len(actions) == 3
    assert actions[0]["action"] == "click"
    assert actions[0]["x"] == 350.5
    assert actions[1]["action"] == "type"
    assert actions[1]["text"] == "my_secure_code_123"
    assert actions[2]["action"] == "press"

    # 取出後隊列應為空
    assert len(broadcaster.get_and_clear_pending_actions(task_id)) == 0

    # 4. 恢復自動化推進
    broadcaster.resume_task(task_id, operator="operator@example.com")
    assert broadcaster.is_paused(task_id) is False

    # 5. 檢核人機介入歷程記錄
    interventions = broadcaster.get_interventions(task_id)
    assert len(interventions) == 1
    assert interventions[0]["operator"] == "operator@example.com"
    assert "duration_seconds" in interventions[0]


# --- 3. Zero-Trust DLP 動態資料防洩測試 ---

def test_zero_trust_dlp_page_masking():
    dlp = ZeroTrustDLPService(enabled=True, mask_passwords=True, redact_tokens=True)
    fake_page = FakePage(sensitive_count=3)

    masked_count = dlp.mask_page(fake_page)
    assert masked_count == 3
    assert len(fake_page.added_styles) == 1
    assert "filter: blur(8px)" in fake_page.added_styles[0]


def test_zero_trust_dlp_text_and_data_redaction():
    dlp = ZeroTrustDLPService(enabled=True, mask_passwords=True, redact_tokens=True)

    # 1. Bearer Token 脫敏
    raw_token = "Authorization header with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token_payload_xyz"
    redacted_token, count1 = dlp.redact_text(raw_token)
    assert count1 >= 1
    assert "Bearer [REDACTED_TOKEN]" in redacted_token
    assert "token_payload_xyz" not in redacted_token

    # 2. API Key 脫敏
    raw_key = "Using OpenAI key sk-abcdef1234567890abcdef1234567890 to call model"
    redacted_key, count2 = dlp.redact_text(raw_key)
    assert count2 >= 1
    assert "sk-[REDACTED_KEY]" in redacted_key

    # 3. 信用卡號脫敏
    raw_card = "Customer payment card: 4111-2222-3333-4444 on checkout"
    redacted_card, count3 = dlp.redact_text(raw_card)
    assert count3 >= 1
    assert "****-****-****-4444" in redacted_card

    # 4. 身分證/SSN 脫敏
    raw_ssn = "User SSN is 123-45-6789 for KYC"
    redacted_ssn, count4 = dlp.redact_text(raw_ssn)
    assert count4 >= 1
    assert "***-**-****" in redacted_ssn

    # 5. 遞迴字典結構脫敏
    nested_data = {
        "user": "alice",
        "auth": "Bearer secret_jwt_token_1234567890",
        "nested": {
            "card": "5555 6666 7777 8888",
            "items": ["sk-test12345678901234567890", "normal_item"]
        }
    }
    redacted_dict = dlp.redact_data(nested_data)
    assert "Bearer [REDACTED_TOKEN]" in redacted_dict["auth"]
    assert "****-****-****-8888" in redacted_dict["nested"]["card"]
    assert "sk-[REDACTED_KEY]" in redacted_dict["nested"]["items"][0]
    assert redacted_dict["nested"]["items"][1] == "normal_item"


# --- 4. 多叢集排程同盟與高可用容災測試 ---

def test_cluster_federation_heartbeat_and_election():
    mgr = ClusterFederationManager(node_id="node-us-east-1", region="us-east-1", lease_ttl_seconds=5)

    # 初始時本機節點應為 Leader
    topo = mgr.get_topology()
    assert topo["cluster_status"] == "healthy"
    assert topo["leader_node_id"] == "node-us-east-1"
    assert topo["total_nodes"] == 1

    # 註冊另一個區域的備援節點
    mgr.register_heartbeat("node-eu-west-1", "eu-west-1", active_schedules_count=2, is_leader=False)
    topo2 = mgr.get_topology()
    assert topo2["total_nodes"] == 2
    assert topo2["healthy_nodes"] == 2


def test_cluster_federation_failover_when_leader_times_out():
    # 租約 TTL 設為 0.1 秒以利快速觸發超時
    mgr = ClusterFederationManager(node_id="node-primary", region="us-east", lease_ttl_seconds=0.1)
    mgr.register_heartbeat("node-backup", "eu-central", is_leader=False)

    # 人工將主節點的心跳時間調早以模擬當機
    mgr._memory_nodes["node-primary"]["last_heartbeat"] = time.time() - 2.0
    # 備援節點保持鮮活
    mgr._memory_nodes["node-backup"]["last_heartbeat"] = time.time()

    # 觸發領導權評估 -> 備援節點自動晉升為新 Leader
    new_leader = mgr.evaluate_leadership()
    assert new_leader == "node-backup"
    assert mgr._memory_nodes["node-backup"]["is_leader"] is True
    assert mgr._memory_nodes["node-primary"]["status"] == "offline"


# --- 5. V1.4 API 端點整合與 RBAC 測試 ---

def test_v14_api_endpoints_and_rbac():
    import browser_agent.api as api
    from browser_agent.kafka import NullBus

    app = create_app()
    fake_session = FakeSession()
    app.dependency_overrides[api.get_session] = lambda: fake_session
    original_get_bus = api.get_bus
    api.get_bus = lambda servers: NullBus()

    try:
        client = TestClient(app)
        settings = get_settings()

        # 產生多角色 Token
        def _token(role: str) -> str:
            actor = ActorContext(
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                email=f"{role}@example.com",
                roles=(role,),
            )
            return create_access_token(actor, settings=settings)

        creator_h = {"Authorization": f"Bearer {_token('creator')}"}
        operator_h = {"Authorization": f"Bearer {_token('operator')}"}
        admin_h = {"Authorization": f"Bearer {_token('admin')}"}

        # 1. 測試 DLP 狀態端點
        dlp_resp = client.get("/v1/ops/dlp/status", headers=operator_h)
        assert dlp_resp.status_code == 200
        dlp_data = dlp_resp.json()
        assert dlp_data["status"] == "active"
        assert "password_kv" in dlp_data["active_rules"]


        # 2. 測試 Federation 拓撲端點
        fed_resp = client.get("/v1/ops/federation/nodes", headers=operator_h)
        assert fed_resp.status_code == 200
        fed_data = fed_resp.json()
        assert fed_data["cluster_status"] in {"healthy", "degraded"}
        assert "nodes" in fed_data

        # 3. 測試 Federation 心跳註冊
        hb_resp = client.post("/v1/ops/federation/heartbeat", headers=operator_h, json={
            "node_id": "api-test-node-99",
            "region": "ap-northeast-1",
            "active_schedules_count": 5,
            "metadata": {"load": 0.12},
        })
        assert hb_resp.status_code == 200
        assert hb_resp.json()["registered"] is True

        # 4. 測試 Federation 強制重選 (限 admin)
        re_resp = client.post("/v1/ops/federation/re-election", headers=admin_h, json={
            "target_node_id": "api-test-node-99"
        })
        assert re_resp.status_code == 200
        assert re_resp.json()["re_elected"] is True
        assert re_resp.json()["leader_node_id"] == "api-test-node-99"

        # 5. 測試建立單一任務帶有 V1.4 browser_engine
        task_resp = client.post("/v1/tasks", headers=creator_h, json={
            "title": "Firefox specific inspection",
            "instructions": "Navigate and check rendering",
            "browser_engine": "firefox",
            "metadata": {"start_url": "https://example.com"},
        })
        assert task_resp.status_code == 200
        t_data = task_resp.json()
        assert t_data["browser_engine"] == "firefox"
        task_id = t_data["task_id"]

        # 6. 測試雙向接管 API: pause, interact, resume
        pause_resp = client.post(f"/v1/tasks/{task_id}/pause", headers=operator_h, json={
            "reason": "Test pause for HITL"
        })
        assert pause_resp.status_code == 200
        assert pause_resp.json()["paused"] is True

        interact_resp = client.post(f"/v1/tasks/{task_id}/interact", headers=operator_h, json={
            "action": "click",
            "x": 100.0,
            "y": 250.0
        })
        assert interact_resp.status_code == 200
        assert interact_resp.json()["queued"] is True

        resume_resp = client.post(f"/v1/tasks/{task_id}/resume", headers=operator_h)
        assert resume_resp.status_code == 200
        assert resume_resp.json()["resumed"] is True

        # 7. 測試一鍵派發跨瀏覽器矩陣任務
        matrix_resp = client.post("/v1/tasks/matrix", headers=creator_h, json={
            "title": "E2E Matrix Task Suite",
            "instructions": "Verify layout across engines",
            "engines": ["chromium", "firefox", "webkit"],
            "metadata": {"start_url": "https://example.com"},
        })
        assert matrix_resp.status_code == 200
        m_data = matrix_resp.json()
        assert m_data["total_tasks"] == 3
        matrix_id = m_data["matrix_id"]

        # 8. 測試矩陣任務聚合查詢
        summary_resp = client.get(f"/v1/tasks/matrix/{matrix_id}", headers=operator_h)
        assert summary_resp.status_code == 200
        s_data = summary_resp.json()
        assert s_data["matrix_id"] == matrix_id
        assert len(s_data["tasks"]) == 3
        engines_dispatched = {t["browser_engine"] for t in s_data["tasks"]}
        assert engines_dispatched == {"chromium", "firefox", "webkit"}
    finally:
        api.get_bus = original_get_bus


# --- 6. Operations Center V1.4 UI 渲染檢查 ---

def test_operations_ui_renders_v14_elements():
    client = TestClient(create_app())
    res = client.get("/operations")
    assert res.status_code == 200
    html = res.text

    # V1.4 標題與相容性文字
    assert "Browser Agent v1.4 Operations Center (維運中心)" in html
    assert "Browser Agent v1.2 Operations Center" in html

    # V1.4 徽章
    assert "id=\"dlp-shield-badge\"" in html
    assert "id=\"cluster-fed-badge\"" in html

    # V1.4 Create Task 控制項
    assert "id=\"browser-engine-select\"" in html
    assert "id=\"create-matrix-task\"" in html
    assert "id=\"dlp-toggle\"" in html

    # V1.4 雙向接管控制條 (HITL)
    assert "id=\"btn-pause-takeover\"" in html
    assert "id=\"btn-resume-takeover\"" in html
    assert "id=\"btn-send-keys\"" in html
    assert "id=\"remote-key-input\"" in html
    assert "id=\"takeover-status-pill\"" in html

    # V1.4 面板
    assert "id=\"matrix-comparison-section\"" in html
    assert "id=\"dlp-section\"" in html
    assert "id=\"federation-section\"" in html
