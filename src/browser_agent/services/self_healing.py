from __future__ import annotations

import difflib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class HeuristicSelfHealingEngine:
    """
    啟發式選擇器自我修復引擎 (Heuristic Self-Healing Engine)
    當目標網頁發生改版或動態 Class 變更導致 Selector 失效時，
    自動執行階層式降級探測與 DOM 特徵相似度比對，實現無損自癒。
    100% 遵守 Heuristic 規範，不依賴外部非可控 LLM。
    """

    def __init__(self, confidence_threshold: float = 0.65):
        self.confidence_threshold = confidence_threshold

    def resolve_target(
        self,
        page: Any,
        target: str | None,
        action: str,
        fallback_selectors: list[str] | None = None,
        instruction: str | None = None,
        timeout_ms: int = 1500,
    ) -> tuple[Any, dict[str, Any] | None]:
        """
        嘗試解析 target，若失效則啟動自癒。
        回傳 (locator, heal_info_dict_or_None)
        """
        if not target:
            return None, None

        # 1. 嘗試主選擇器
        try:
            loc = page.locator(target).first
            if loc.count() > 0 and loc.is_visible(timeout=timeout_ms):
                return loc, None
        except Exception:
            pass

        logger.info("Primary selector '%s' failed for action '%s'. Initiating self-healing...", target, action)

        # 2. 策略一：Fallback Selectors Cascade 依序探測
        if fallback_selectors:
            for fallback in fallback_selectors:
                if not fallback or fallback == target:
                    continue
                try:
                    loc = page.locator(fallback).first
                    if loc.count() > 0 and loc.is_visible(timeout=timeout_ms):
                        heal_info = {
                            "self_healed": True,
                            "strategy": "fallback_cascade",
                            "original_target": target,
                            "repaired_target": fallback,
                            "confidence": 1.0,
                        }
                        logger.info("Self-healed via fallback selector: %s -> %s", target, fallback)
                        return loc, heal_info
                except Exception:
                    continue

        # 3. 策略二：啟發式 DOM 候選特徵比對 (Heuristic Feature Matching)
        try:
            candidates = self._extract_dom_candidates(page, action)
            if candidates:
                best_candidate, score, repaired_selector = self._match_best_candidate(
                    candidates, target, action, instruction
                )
                if best_candidate and score >= self.confidence_threshold:
                    loc = page.locator(repaired_selector).first
                    if loc.count() > 0:
                        heal_info = {
                            "self_healed": True,
                            "strategy": "heuristic_feature_match",
                            "original_target": target,
                            "repaired_target": repaired_selector,
                            "confidence": round(score, 2),
                            "candidate_tag": best_candidate.get("tag"),
                            "candidate_text": best_candidate.get("text", "")[:30],
                        }
                        logger.info(
                            "Self-healed via heuristic feature matching (score=%.2f): %s -> %s",
                            score,
                            target,
                            repaired_selector,
                        )
                        return loc, heal_info
        except Exception as exc:
            logger.debug("Heuristic feature matching inspection failed: %s", exc)

        # 若皆無法自癒，返回原本 locator（交由呼叫方進行常規錯誤處理與截圖）
        return page.locator(target).first, None

    def _extract_dom_candidates(self, page: Any, action: str) -> list[dict[str, Any]]:
        """從當前頁面提取可互動元素的關鍵屬性特徵"""
        script = """() => {
            const elements = Array.from(document.querySelectorAll('button, a, input, [role="button"], textarea, select'));
            return elements.slice(0, 80).map((el, idx) => {
                const rect = el.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).display !== 'none';
                return {
                    index: idx,
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || '',
                    text: (el.innerText || el.textContent || el.value || '').trim().substring(0, 80),
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    aria_label: el.getAttribute('aria-label') || '',
                    role: el.getAttribute('role') || '',
                    class_name: el.className || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    is_visible: isVisible
                };
            }).filter(e => e.is_visible);
        }"""
        return page.evaluate(script) or []

    def _match_best_candidate(
        self,
        candidates: list[dict[str, Any]],
        target: str,
        action: str,
        instruction: str | None,
    ) -> tuple[dict[str, Any] | None, float, str]:
        """評估特徵相似度得分並組裝修復選擇器"""
        target_lower = target.lower()
        inst_lower = (instruction or "").lower()

        best_cand = None
        highest_score = 0.0
        best_selector = ""

        # 提取 target 與 instruction 中的關鍵詞
        target_tokens = {t for t in re.findall(r"\w+", target_lower) if len(t) > 2 and t not in {"button", "input", "the", "click", "old", "btn"}}
        inst_tokens = {t for t in re.findall(r"\w+", inst_lower) if len(t) > 2 and t not in {"button", "input", "the", "click", "continue"}} if inst_lower else set()
        all_tokens = target_tokens.union(inst_tokens)

        for cand in candidates:
            score = 0.0
            tag = cand["tag"]
            cand_text = cand["text"].lower()
            cand_aria = cand["aria_label"].lower()
            cand_id = cand["id"].lower()
            cand_name = cand["name"].lower()
            cand_placeholder = cand["placeholder"].lower()

            # 1. 根據動作類型與標籤匹配加分 (0.2)
            if action == "click" and (tag in {"button", "a"} or cand.get("role") == "button"):
                score += 0.2
            elif action in {"fill", "press"} and tag in {"input", "textarea"}:
                score += 0.2

            # 2. Target 關鍵詞高權重直接命中 (最多 +0.4)
            cand_identifiers = f"{cand_id} {cand_name} {cand_aria}"
            if any(t in cand_identifiers for t in target_tokens):
                score += 0.4
            elif any(t in cand_text for t in target_tokens):
                score += 0.3

            # 3. Instruction 意圖詞命中 (最多 +0.2)
            cand_corpus = f"{cand_text} {cand_aria} {cand_id} {cand_name} {cand_placeholder}"
            if inst_tokens:
                inst_matches = sum(1 for t in inst_tokens if t in cand_corpus)
                score += 0.2 * (inst_matches / len(inst_tokens))

            # 4. 文字相似度比對 (最多 +0.2)
            if cand_text and all_tokens:
                sim = max((difflib.SequenceMatcher(None, t, cand_text).ratio() for t in all_tokens), default=0.0)
                score += 0.2 * sim


            if score > highest_score:
                highest_score = score
                best_cand = cand

                # 組裝具體的修復定位器
                if cand["id"]:
                    best_selector = f"#{cand['id']}"
                elif cand["name"]:
                    best_selector = f"{tag}[name='{cand['name']}']"
                elif cand["aria_label"]:
                    best_selector = f"{tag}[aria-label='{cand['aria_label']}']"
                elif cand["text"]:
                    best_selector = f"{tag}:has-text('{cand['text'][:20]}')"
                elif cand["placeholder"]:
                    best_selector = f"{tag}[placeholder='{cand['placeholder']}']"
                else:
                    best_selector = f"{tag}:nth-of-type({cand['index'] + 1})"

        return best_cand, min(highest_score, 1.0), best_selector


_self_healing_engine: HeuristicSelfHealingEngine | None = None

def get_self_healing_engine() -> HeuristicSelfHealingEngine:
    global _self_healing_engine
    if _self_healing_engine is None:
        _self_healing_engine = HeuristicSelfHealingEngine()
    return _self_healing_engine
