from __future__ import annotations

from dataclasses import dataclass

@dataclass
class BrowserResult:
    final_url: str | None
    title: str | None
    html: str
    artifacts: list[dict]
    observations: list[dict]

class BrowserRunner:
    def __init__(self, headless: bool = True, timeout_seconds: int = 120, record_video: bool = False):
        self.headless = headless
        self.timeout_seconds = timeout_seconds
        self.record_video = record_video

    def execute(
        self,
        task: dict,
        artifact_store,
        allowed_domains: set[str],
        storage_state: dict | None = None,
    ) -> BrowserResult:
        import os
        import json
        import tempfile
        from playwright.sync_api import sync_playwright

        plan = (task.get("metadata") or {}).get("plan") or []
        start_url = (task.get("metadata") or {}).get("start_url")
        metadata = task.get("metadata") or {}
        should_record_video = metadata.get("record_video", self.record_video)
        save_session_as = metadata.get("save_session_as")

        artifacts = []
        observations = []

        with tempfile.TemporaryDirectory() as temp_dir:
            video_dir = os.path.join(temp_dir, "videos") if should_record_video else None
            if video_dir:
                os.makedirs(video_dir, exist_ok=True)

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )

                context_kwargs = {
                    "viewport": {"width": 1440, "height": 900},
                    "java_script_enabled": True,
                }
                if storage_state:
                    context_kwargs["storage_state"] = storage_state
                if video_dir:
                    context_kwargs["record_video_dir"] = video_dir
                    context_kwargs["record_video_size"] = {"width": 1280, "height": 720}

                context = browser.new_context(**context_kwargs)
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
                        stored = artifact_store.write_bytes(
                            str(task["id"]),
                            "screenshot",
                            shot,
                            suffix=".png",
                            content_type="image/png",
                        )
                        artifacts.append(_stored_artifact_payload("screenshot", stored))
                    else:
                        observation["error"] = f"unsupported action: {action}"
                    observations.append(observation)

                final_url = page.url
                title = page.title()
                html = page.content()

                stored_html = artifact_store.write_bytes(
                    str(task["id"]),
                    "html",
                    html.encode("utf-8"),
                    suffix=".html",
                    content_type="text/html; charset=utf-8",
                )
                artifacts.append(_stored_artifact_payload("html", stored_html))

                # 若指定 save_session_as，保存 storage_state
                if save_session_as:
                    try:
                        saved_state = context.storage_state()
                        saved_state_bytes = json.dumps(saved_state, indent=2).encode("utf-8")
                        stored_session = artifact_store.write_bytes(
                            str(task["id"]),
                            "storage_state",
                            saved_state_bytes,
                            suffix=".json",
                            content_type="application/json",
                        )
                        payload = _stored_artifact_payload("storage_state", stored_session)
                        payload["metadata"] = {
                            **(payload.get("metadata") or {}),
                            "session_name": save_session_as,
                            "cookies_count": len(saved_state.get("cookies", [])),
                        }
                        artifacts.append(payload)
                    except Exception as sess_exc:
                        observations.append({"session_vault_error": str(sess_exc)})

                # 關閉 context 以完成錄影輸出
                page.close()
                context.close()
                browser.close()

            # 若有錄影，尋找 WebM 影片並寫入 artifact store
            if video_dir and os.path.exists(video_dir):
                for fname in os.listdir(video_dir):
                    if fname.endswith(".webm"):
                        fpath = os.path.join(video_dir, fname)
                        with open(fpath, "rb") as vf:
                            vbytes = vf.read()
                        stored_video = artifact_store.write_bytes(
                            str(task["id"]),
                            "video",
                            vbytes,
                            suffix=".webm",
                            content_type="video/webm",
                        )
                        payload = _stored_artifact_payload("video", stored_video)
                        payload["metadata"] = {
                            **(payload.get("metadata") or {}),
                            "video_filename": fname,
                        }
                        artifacts.append(payload)
                        break

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


def _stored_artifact_payload(artifact_type: str, stored) -> dict:
    return {
        "type": artifact_type,
        "uri": stored.uri,
        "sha256": stored.sha256,
        "content_type": stored.content_type,
        "size_bytes": stored.size_bytes,
        "backend": stored.backend,
        "metadata": stored.metadata,
    }
