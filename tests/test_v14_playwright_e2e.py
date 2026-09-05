import os
import time
import uuid
import socket
import threading
from types import SimpleNamespace
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from browser_agent.api import create_app, get_session
from browser_agent import models


class PlaywrightFakeSession:
    def __init__(self):
        self.added = []
        self.tasks = {}
        sample_task_id = uuid.uuid4()
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


@pytest.fixture(scope="module")
def live_server():
    port = get_free_port()
    app = create_app()
    
    fake_session = PlaywrightFakeSession()
    app.dependency_overrides[get_session] = lambda: fake_session

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    timeout = 10
    start = time.time()
    ready = False
    import urllib.request
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{base_url}/operations", timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.1)

    assert ready, f"Server failed to start on {base_url} within {timeout}s"

    yield base_url

    server.should_exit = True


def test_playwright_operations_center_v14_ui(live_server):
    """
    真實 Playwright Chromium 瀏覽器測試：
    驗證 /operations 頁面渲染、V1.4 徽章、引擎切換、HITL 控制列與面板互動，並進行畫面截圖。
    """
    os.makedirs("tests/artifacts", exist_ok=True)
    screenshot_path = "tests/artifacts/v14_operations_playwright_test.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. 導航至 Operations Center
        page.goto(f"{live_server}/operations", wait_until="domcontentloaded")
        page.wait_for_selector("#dlp-shield-badge", timeout=5000)

        # 2. 標題與版本檢驗
        title = page.title()
        assert "Operations Center" in title
        h1_text = page.locator("h1").inner_text()
        assert "Operations Center" in h1_text
        assert "v1.4" in h1_text.lower()

        # 3. 頂部 V1.4 徽章檢驗
        dlp_badge = page.locator("#dlp-shield-badge")
        assert dlp_badge.is_visible()
        assert "DLP" in dlp_badge.inner_text()

        fed_badge = page.locator("#cluster-fed-badge")
        assert fed_badge.is_visible()
        assert ("FEDERATION" in fed_badge.inner_text() or "Cluster" in fed_badge.inner_text())

        # 4. 跨瀏覽器引擎下拉選單與矩陣按鈕
        engine_select = page.locator("#browser-engine-select")
        assert engine_select.is_visible()
        options = engine_select.locator("option").all_inner_texts()
        assert any("chromium" in o.lower() for o in options)
        assert any("firefox" in o.lower() for o in options)
        assert any("webkit" in o.lower() for o in options)

        # 模擬切換到 firefox
        engine_select.select_option("firefox")
        assert engine_select.input_value() == "firefox"

        # 檢查 Launch Matrix 按鈕
        matrix_btn = page.locator("#create-matrix-task")
        assert matrix_btn.is_visible()
        assert "Matrix" in matrix_btn.inner_text()

        # 5. HITL 雙向遠端接管控制列（驗證元素可見性與未選取任務時的防呆鎖定）
        pause_btn = page.locator("#btn-pause-takeover")
        assert pause_btn.is_visible()
        assert pause_btn.is_disabled()  # 尚未選取任務時防呆鎖定

        resume_btn = page.locator("#btn-resume-takeover")
        assert resume_btn.is_visible()
        assert resume_btn.is_disabled()

        send_btn = page.locator("#btn-send-keys")
        assert send_btn.is_visible()
        assert send_btn.is_disabled()

        key_input = page.locator("#remote-key-input")
        assert key_input.is_visible()
        assert key_input.is_disabled()

        # 模擬接管啟動：移除 disabled 進行文字輸入測試
        page.evaluate("document.getElementById('remote-key-input').disabled = false")
        key_input.fill("Hello V1.4 HITL Interactive Session")
        assert key_input.input_value() == "Hello V1.4 HITL Interactive Session"

        # 6. 三大 V1.4 專屬面板
        matrix_panel = page.locator("#matrix-comparison-section")
        assert matrix_panel.is_visible()

        dlp_panel = page.locator("#dlp-section")
        assert dlp_panel.is_visible()

        fed_panel = page.locator("#federation-section")
        assert fed_panel.is_visible()

        # 7. 截取真實渲染畫面
        page.screenshot(path=screenshot_path, full_page=True)
        assert os.path.exists(screenshot_path)
        assert os.path.getsize(screenshot_path) > 1000

        browser.close()
