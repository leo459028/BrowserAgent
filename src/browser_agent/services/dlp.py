from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# 脫敏正規表達式清單
DLP_RULES: list[tuple[str, re.Pattern, str]] = [
    # 1. Bearer Token
    ("bearer_token", re.compile(r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{15,})"), r"Bearer [REDACTED_TOKEN]"),
    # 2. OpenAI / Provider API Keys
    ("api_key", re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,})\b"), r"sk-[REDACTED_KEY]"),
    # 3. 信用卡號 (16 碼)
    ("credit_card", re.compile(r"\b(\d{4})[ -]?(\d{4})[ -]?(\d{4})[ -]?(\d{4})\b"), r"****-****-****-\4"),
    # 4. 身分字號 / SSN (US standard)
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), r"***-**-****"),
    # 5. 明文密碼鍵值對
    (
        "password_kv",
        re.compile(r"(?i)(password|secret|passwd|client_secret)[\"']?\s*[:=]\s*[\"']?([^\s,\"'\\]{4,})[\"']?"),
        r'\1: "[REDACTED]"',
    ),
]

DLP_CSS_MASK = """
input[type="password"],
[data-sensitive="true"],
input[name*="card"],
input[name*="cvv"],
input[name*="ssn"],
input[autocomplete*="cc-"] {
    filter: blur(8px) !important;
    background-color: #1a202c !important;
    color: transparent !important;
    text-shadow: none !important;
}
"""


class ZeroTrustDLPService:
    """
    零信任動態情境資料防洩 (Zero-Trust DLP) 引擎
    負責在 Playwright 畫面渲染、截圖、WebM 錄影與日誌記錄前執行像素級與文字級脫敏
    """

    def __init__(self, enabled: bool = True, mask_passwords: bool = True, redact_tokens: bool = True):
        self.enabled = enabled
        self.mask_passwords = mask_passwords
        self.redact_tokens = redact_tokens
        self._masked_elements_count = 0
        self._redacted_strings_count = 0

    def mask_page(self, page: Any) -> int:
        """
        向 Playwright Page 注入脫敏 CSS 樣式，將密碼框與敏感標籤以高斯模糊遮罩
        """
        if not self.enabled or not self.mask_passwords:
            return 0
        try:
            # 統計頁面上符合遮罩條件之元素數量
            selector = 'input[type="password"], [data-sensitive="true"], input[name*="card"], input[name*="cvv"], input[name*="ssn"], input[autocomplete*="cc-"]'
            count = page.locator(selector).count()
            if count > 0:
                page.add_style_tag(content=DLP_CSS_MASK)
                self._masked_elements_count += count
                logger.debug("DLP masked %d sensitive elements on page", count)
            return count
        except Exception as e:
            logger.warning("Failed to inject DLP mask CSS into page: %s", e)
            return 0

    def redact_text(self, text: str) -> tuple[str, int]:
        """
        以正規表達式掃描字串並遮蔽敏感 Token、卡號、密碼等
        回傳 (脫敏後字串, 脫敏計數)
        """
        if not self.enabled or not self.redact_tokens or not text:
            return text, 0

        redacted = text
        total_matches = 0
        for rule_name, pattern, replacement in DLP_RULES:
            matches = pattern.findall(redacted)
            if matches:
                total_matches += len(matches)
                redacted = pattern.sub(replacement, redacted)

        if total_matches > 0:
            self._redacted_strings_count += total_matches
        return redacted, total_matches

    def redact_data(self, data: Any) -> Any:
        """
        遞迴脫敏字典、列表與物件中的文字內容
        """
        if not self.enabled or not self.redact_tokens:
            return data

        if isinstance(data, str):
            redacted, _ = self.redact_text(data)
            return redacted
        elif isinstance(data, dict):
            return {k: self.redact_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact_data(item) for item in data]
        return data

    def get_status(self) -> dict[str, Any]:
        """
        查詢 DLP 引擎運行狀態與防護統計
        """
        return {
            "enabled": self.enabled,
            "mask_passwords": self.mask_passwords,
            "redact_tokens": self.redact_tokens,
            "masked_elements_count": self._masked_elements_count,
            "redacted_strings_count": self._redacted_strings_count,
            "active_rules": [rule[0] for rule in DLP_RULES],
            "status": "active" if self.enabled else "disabled",
        }


_dlp_service_instance: ZeroTrustDLPService | None = None


def get_dlp_service() -> ZeroTrustDLPService:
    global _dlp_service_instance
    if _dlp_service_instance is None:
        from ..config import get_settings
        settings = get_settings()
        _dlp_service_instance = ZeroTrustDLPService(
            enabled=settings.dlp_enabled,
            mask_passwords=settings.dlp_mask_passwords,
            redact_tokens=settings.dlp_redact_tokens,
        )
    return _dlp_service_instance
