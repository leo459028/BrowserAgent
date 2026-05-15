from __future__ import annotations

from dataclasses import dataclass
from playwright.sync_api import sync_playwright

@dataclass
class BrowserResult:
    final_url: str | None
    title: str | None
    html: str
    artifacts: list[dict]
    observations: list[dict]

class BrowserRunner:
    def __init__(self, headless: bool = True, timeout_seconds: int = 120):
        self.headless = headless
        self.timeout_seconds = timeout_seconds

    def execute(self, task: dict, artifact_store, allowed_domains: set[str]) -> BrowserResult:
        plan = (task.get("metadata") or {}).get("plan") or []
        start_url = (task.get("metadata") or {}).get("start_url")

        artifacts = []
        observations = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                java_script_enabled=True,
            )
            page = context.new_page()

            if start_url:
                self._ensure_allowed(start_url, allowed_domains)
                page.goto(start_url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)

            for i, step in enumerate(plan, start=1):
                action = step.get("action")
                target = step.get("target")
                value = step.get("value")
                url = step.get("url")
                observation = {"step_no": i, "action": action, "target": target}

                if action == "goto":
                    self._ensure_allowed(url or target, allowed_domains)
                    page.goto(url or target, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)
                elif action == "click":
                    page.locator(target).first.click(timeout=self.timeout_seconds * 1000)
                elif action == "fill":
                    page.locator(target).first.fill(value or "", timeout=self.timeout_seconds * 1000)
                elif action == "press":
                    page.locator(target).first.press(value or "Enter", timeout=self.timeout_seconds * 1000)
                elif action == "wait":
                    page.wait_for_timeout(int(step.get("ms", 1000)))
                elif action == "extract_text":
                    observation["value"] = page.locator(target).first.inner_text(timeout=self.timeout_seconds * 1000)
                elif action == "screenshot":
                    shot = page.screenshot(full_page=True)
                    stored = artifact_store.write_bytes(str(task["id"]), "screenshot", shot, suffix=".png")
                    artifacts.append({"type": "screenshot", "uri": stored.uri, "sha256": stored.sha256})
                else:
                    observation["error"] = f"unsupported action: {action}"
                observations.append(observation)

            final_url = page.url
            title = page.title()
            html = page.content()

            stored_html = artifact_store.write_bytes(str(task["id"]), "html", html.encode("utf-8"), suffix=".html")
            artifacts.append({"type": "html", "uri": stored_html.uri, "sha256": stored_html.sha256})

            browser.close()

        return BrowserResult(
            final_url=final_url,
            title=title,
            html=html,
            artifacts=artifacts,
            observations=observations,
        )

    def _ensure_allowed(self, url: str | None, allowed_domains: set[str]) -> None:
        if not url:
            return
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        if host and allowed_domains and not any(host == d or host.endswith("." + d) for d in allowed_domains):
            raise ValueError(f"blocked domain: {host}")
