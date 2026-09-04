from __future__ import annotations

import json
import logging
import threading
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def dispatch_alert_webhook(
    rule_id: str,
    note: str,
    settings,
    actor_email: str = "system",
    level: str = "warning",
) -> bool:
    webhook_url = getattr(settings, "alert_webhook_url", "")
    if not webhook_url:
        return False

    timeout = float(getattr(settings, "alert_webhook_timeout_seconds", 3.0))

    payload = {
        "text": f"🚨 [BrowserAgent Alert] Rule: {rule_id} | Level: {level.upper()}\nNote: {note}\nOperator: {actor_email}",
        "content": f"🚨 **[BrowserAgent Alert]** `{rule_id}` ({level.upper()})\n> {note}\n*Dispatched by: {actor_email}*",
        "rule_id": rule_id,
        "level": level,
        "note": note,
        "actor": actor_email,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": getattr(settings, "app_name", "browser-agent"),
        "environment": getattr(settings, "app_env", "local"),
    }

    def _send_request():
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "BrowserAgent-AlertDispatcher/1.1"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.getcode()
                logger.info("webhook alert dispatched successfully, status: %s", status_code)
        except Exception:
            try:
                logger.warning("failed to dispatch alert webhook to %s", webhook_url)
            except Exception:
                pass

    thread = threading.Thread(target=_send_request, daemon=True)
    thread.start()
    return True
