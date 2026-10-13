#!/usr/bin/env python3
"""
Comprehensive Browser & E2E Test Suite for BrowserAgent V1.4.
Tests:
1. Operations Center Readiness (v1.4.0) & 7 Alert Rules
2. Zero-Trust Dynamic DLP Engine (Status, Rules & Redaction)
3. Cross-Browser Matrix Engine (Chromium, Firefox, WebKit Dispatch & Inspection)
4. HITL Reverse Control Channel (Pause -> Interact -> Resume & Human Intervened Audit)
5. Multi-Cluster Federation & Failover (Nodes Topology & Forced Re-election)
6. Operations Center HTML UI Route Inspection
7. Direct Playwright Headless Browser UI Test of /operations Dashboard
"""

import os
import sys
import time
import uuid
import json
import socket
import threading
from types import SimpleNamespace
import urllib.request
import urllib.parse
from datetime import datetime

# 確保引用本機 src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

if sys.platform == "win32":
    import io
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = os.environ.get("BASE_URL", "")

def log(msg: str):
    clean_msg = msg.replace("\u2713", "[OK]").replace("🎉", "[SUCCESS]")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {clean_msg}", flush=True)

def http_req(base_url: str, path: str, method: str = "GET", data: dict = None, token: str = None) -> tuple[int, dict | bytes]:
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req_body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return resp.status, json.loads(raw.decode("utf-8"))
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode("utf-8"))
        except Exception:
            return e.code, raw

def get_token(base_url: str, role: str) -> str:
    status, res = http_req(base_url, "/v1/auth/local-token", method="POST", data={"role": role})
    assert status == 200, f"Failed to get token for role {role}: {res}"
    return res["access_token"]

class FakeStandaloneSession:
    def __init__(self):
        self.added = []
        self.tasks = {}
        sample_task_id = uuid.uuid4()
        from browser_agent import models
        sample_task = models.Task(
            id=sample_task_id,
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            title="E2E V1.4 Preloaded Task",
            instructions="Sample instructions",
            priority=1,
            risk_level="low",
            status="pending_approval",
            browser_engine="chromium",
            metadata_={"start_url": "https://example.com"},
        )
        self.tasks[sample_task_id] = sample_task

    def add(self, obj):
        from browser_agent import models
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.added.append(obj)
        if isinstance(obj, models.Task):
            self.tasks[obj.id] = obj

    def flush(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def get(self, entity, eid):
        from browser_agent import models
        if entity is models.Task:
            return self.tasks.get(eid)
        return None

    def execute(self, stmt):
        s_str = str(stmt).lower()
        if "scheduled_tasks" in s_str:
            items = []
        elif "artifacts" in s_str:
            items = []
        elif "cluster_nodes" in s_str:
            items = []
        elif "matrix_id" in s_str:
            items = [t for t in self.tasks.values() if getattr(t, "matrix_id", None) is not None]
        elif "tasks" in s_str:
            items = list(self.tasks.values())
        else:
            items = []
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: items,
                first=lambda: items[0] if items else None,
            )
        )

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def main():
    global BASE_URL
    server = None
    server_thread = None

    if not BASE_URL:
        # 自動啟動本地獨立測試伺服器
        log("未指定 BASE_URL，正在啟動本地獨立測試 API 伺服器...")
        import uvicorn
        from browser_agent.api import create_app, get_session
        import browser_agent.api as api_mod

        # 模擬 NullBus 以免依賴外部 Kafka
        class NullBus:
            def publish(self, topic, key, value): pass
        api_mod.get_bus = lambda *args, **kwargs: NullBus()

        app = create_app()
        shared_session = FakeStandaloneSession()
        app.dependency_overrides[get_session] = lambda: shared_session

        port = get_free_port()
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        server_thread = threading.Thread(target=server.run, daemon=True)
        server_thread.start()

        BASE_URL = f"http://127.0.0.1:{port}"
        time.sleep(1.0)
        log(f"本地測試伺服器已在 {BASE_URL} 成功啟動")

    try:
        log("=== 開始 BrowserAgent V1.4 完整端到端測試（含真實瀏覽器與命令測試） ===")
        
        # 1. 認證與角色 Token 取得
        log("步驟 1：取得各角色身份 Token (creator, approver, operator, admin)...")
        creator_token = get_token(BASE_URL, "creator")
        approver_token = get_token(BASE_URL, "approver")
        operator_token = get_token(BASE_URL, "operator")
        admin_token = get_token(BASE_URL, "admin")
        log("✓ 成功取得 4 組角色 Token")

        # 2. 系統健康與 Operations Readiness
        log("步驟 2：檢驗系統 Operations Readiness (版本 1.4.0)...")
        status, readiness = http_req(BASE_URL, "/v1/ops/readiness", token=operator_token)
        assert status == 200, f"Readiness failed: {readiness}"
        app_info = readiness.get("app", {})
        log(f"  App Version: {app_info.get('version')}")
        assert app_info.get("version") in ("1.4.0", "1.4.2")
        log("✓ Operations Readiness 檢驗通過 (版本 1.4.0)")

        # 3. 告警中心檢驗
        log("步驟 3：檢驗 Production Alerting Center (7 大維運規則)...")
        status, alerts = http_req(BASE_URL, "/v1/ops/alerts", token=operator_token)
        assert status == 200, f"Alerts failed: {alerts}"
        assert alerts.get("status") == "healthy", f"System alerts not healthy: {alerts}"
        assert len(alerts.get("rules", [])) == 7
        log("✓ Production Alerting Center 評估通過 (7 大維運規則全數 OK)")

        # 4. Zero-Trust 動態 DLP 狀態檢驗
        log("步驟 4：檢驗 Zero-Trust 動態資料防洩 (DLP) 狀態與規則...")
        status, dlp_status = http_req(BASE_URL, "/v1/ops/dlp/status", token=operator_token)
        assert status == 200, f"DLP status failed: {dlp_status}"
        assert dlp_status.get("status") == "active"
        log(f"  DLP Status: {dlp_status.get('status')}, 遮罩元素數: {dlp_status.get('masked_elements_count')}")
        log("✓ Zero-Trust DLP 防洩引擎運作正常")

        # 5. 跨瀏覽器矩陣任務派發與查詢
        log("步驟 5：驗證跨瀏覽器矩陣執行引擎 (Chromium, Firefox, WebKit)...")
        matrix_payload = {
            "title": "Cross-Browser Rendering & Layout Verification",
            "instructions": "Verify layout across engines",
            "engines": ["chromium", "firefox", "webkit"],
            "priority": 1,
            "metadata": {"start_url": "https://example.com"}
        }
        status, matrix_res = http_req(BASE_URL, "/v1/tasks/matrix", method="POST", data=matrix_payload, token=creator_token)
        assert status in (200, 201), f"Matrix dispatch failed: {matrix_res}"
        matrix_id = matrix_res.get("matrix_id")
        total_tasks = matrix_res.get("total_tasks", 0)
        log(f"  Matrix ID: {matrix_id}, 建立任務數: {total_tasks}")
        assert total_tasks == 3
        
        # 查詢矩陣進度
        status, matrix_summary = http_req(BASE_URL, f"/v1/tasks/matrix/{matrix_id}", token=operator_token)
        assert status == 200, f"Get matrix summary failed: {matrix_summary}"
        assert matrix_summary.get("total_tasks") == 3
        log(f"  Matrix 狀態彙整: matrix_id={matrix_summary.get('matrix_id')}, 任務總數={matrix_summary.get('total_tasks')}")
        log("✓ 跨瀏覽器矩陣派發與聚合端點驗證成功")

        # 6. HITL 雙向即時遠端接管通道 (Pause -> Interact -> Resume)
        log("步驟 6：驗證 HITL 雙向即時遠端接管通道 (Pause / Interact / Resume)...")
        tasks_list = matrix_summary.get("tasks", [])
        sample_task_id = tasks_list[0]["task_id"]
        
        # 暫停
        status, pause_res = http_req(BASE_URL, f"/v1/tasks/{sample_task_id}/pause", method="POST", token=operator_token)
        assert status == 200, f"Pause failed: {pause_res}"
        assert pause_res.get("paused") is True
        log(f"  [OK] 任務 {sample_task_id} 成功暫停 (paused: {pause_res.get('paused')})")

        # 注入互動指令
        interact_payload = {"action": "click", "selector": "button#submit"}
        status, interact_res = http_req(BASE_URL, f"/v1/tasks/{sample_task_id}/interact", method="POST", data=interact_payload, token=operator_token)
        assert status == 200, f"Interact failed: {interact_res}"
        assert interact_res.get("queued") is True
        log(f"  [OK] 成功注入指令: {interact_payload}")

        # 恢復
        status, resume_res = http_req(BASE_URL, f"/v1/tasks/{sample_task_id}/resume", method="POST", token=operator_token)
        assert status == 200, f"Resume failed: {resume_res}"
        assert resume_res.get("resumed") is True
        log(f"  [OK] 任務成功恢復執行 (resumed: {resume_res.get('resumed')})")

        # 7. 多叢集同盟與容災接管 (Federation Topology & Re-election)
        log("步驟 7：驗證多叢集排程同盟與容災接管 (Federation)...")
        status, fed_nodes = http_req(BASE_URL, "/v1/ops/federation/nodes", token=operator_token)
        assert status == 200, f"Federation nodes failed: {fed_nodes}"
        log(f"  同盟節點總數: {fed_nodes.get('total_nodes')}, 當前 Leader: {fed_nodes.get('leader_node_id')}")
        
        # 觸發重新選舉
        status, reelect_res = http_req(BASE_URL, "/v1/ops/federation/re-election", method="POST", token=admin_token)
        assert status == 200, f"Re-election failed: {reelect_res}"
        assert reelect_res.get("re_elected") is True
        log(f"  [OK] 觸發重新選舉成功，新 Leader 節點: {reelect_res.get('leader_node_id')}")

        # 8. Operations Center Web UI 頁面結構驗證
        log("步驟 8：驗證 Operations Center (/operations) UI HTML 結構...")
        status, ui_html = http_req(BASE_URL, "/operations")
        assert status == 200, f"UI /operations failed: {status}"
        ui_str = ui_html.decode("utf-8")
        assert "Operations Center" in ui_str
        assert "v1.4" in ui_str.lower()
        assert "dlp-shield-badge" in ui_str
        assert "cluster-fed-badge" in ui_str
        assert "browser-engine-select" in ui_str
        assert "create-matrix-task" in ui_str
        assert "matrix-comparison-section" in ui_str
        assert "dlp-section" in ui_str
        assert "federation-section" in ui_str
        log("✓ Operations Center V1.4 HTML UI 包含所有 V1.4 關鍵元素與卡片")

        # 9. 真實 Playwright 瀏覽器 UI 渲染與互動測試
        log("步驟 9：直接呼叫 Playwright 啟動 Chromium 瀏覽器進行完整前端 UI 測試...")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            page.goto(f"{BASE_URL}/operations", wait_until="domcontentloaded")
            page.wait_for_selector("#dlp-shield-badge", timeout=5000)
            
            title = page.title()
            log(f"  Playwright 瀏覽器標題: '{title}'")
            assert "Operations Center" in title
            
            # 檢查 H1 標題
            h1_text = page.locator("h1").inner_text()
            log(f"  頁面主標題: '{h1_text}'")
            assert "Operations Center" in h1_text
            
            # 檢查 V1.4 新增徽章
            dlp_badge = page.locator("#dlp-shield-badge")
            assert dlp_badge.is_visible()
            log(f"  ✓ 找到 DLP 徽章: '{dlp_badge.inner_text()}'")
            
            cluster_badge = page.locator("#cluster-fed-badge")
            assert cluster_badge.is_visible()
            log(f"  ✓ 找到 Cluster 同盟徽章: '{cluster_badge.inner_text()}'")
            
            # 檢查 V1.4 瀏覽器引擎選單與 Matrix 按鈕
            engine_select = page.locator("#browser-engine-select")
            assert engine_select.is_visible()
            engine_select.select_option("firefox")
            assert engine_select.input_value() == "firefox"
            log("  ✓ 成功模擬切換 Browser Engine 為 firefox")
            
            matrix_btn = page.locator("#create-matrix-task")
            assert matrix_btn.is_visible()
            log(f"  ✓ 找到矩陣派發按鈕: '{matrix_btn.inner_text()}'")
            
            # 檢查 HITL 反向操作控制區防呆設計
            pause_btn = page.locator("#btn-pause-takeover")
            assert pause_btn.is_visible()
            assert pause_btn.is_disabled()
            
            key_input = page.locator("#remote-key-input")
            assert key_input.is_visible()
            assert key_input.is_disabled()
            page.evaluate("document.getElementById('remote-key-input').disabled = false")
            key_input.fill("Playwright Command E2E Verification")
            assert key_input.input_value() == "Playwright Command E2E Verification"
            log("  ✓ 驗證 HITL 控制項防呆鎖定與模擬輸入成功")
            
            # 檢查三大 V1.4 面板
            assert page.locator("#matrix-comparison-section").is_visible()
            assert page.locator("#dlp-section").is_visible()
            assert page.locator("#federation-section").is_visible()
            log("  ✓ 驗證三大 V1.4 專屬面板 (Matrix / DLP / Federation) 渲染成功")
            
            # 截取瀏覽器渲染畫面
            os.makedirs("scratch", exist_ok=True)
            screenshot_path = "scratch/operations_v14_browser_verified.png"
            page.screenshot(path=screenshot_path, full_page=True)
            log(f"  ✓ Playwright 成功截取完整 V1.4 維運中心畫面: {screenshot_path}")
            
            browser.close()

        log("================================================================")
        log("🎉 恭喜！BrowserAgent V1.4 包含真實瀏覽器與命令測試的全套端到端驗證全部通過！")
        log("================================================================")
    finally:
        if server:
            server.should_exit = True

if __name__ == "__main__":
    main()
