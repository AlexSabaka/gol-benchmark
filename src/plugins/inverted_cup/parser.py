"""
Inverted Cup – Response Parser

Extracts the model's recommended action from a free-form response.

The correct action is to flip / turn the cup over.
Wrong answers include: drilling a hole, cutting, returning, leaving it,
using it as-is (impossible), etc.

Resolution strategy (all prefer the LAST match — end-first principle):
 1. Boxed answer  \\boxed{...}
 2. Bold / header formatting  **...**
 3. Labelled answer line  (Answer: / Action: / Solution: ...)
 4. Strong recommendation phrasing
 5. Full-text keyword scan
 6. Last-sentences scan
 7. Fallback → "wrong"
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import re_search_last, last_sentences

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------

FLIP_PATTERNS = [
    r"\bflip\b",
    r"\bflip\s+(?:it|the\s+cup)\b",
    r"\bturn\s+(?:it|the\s+cup)\s+(?:over|upside.?down|around|right.?side.?up)\b",
    r"\binvert\s+(?:it|the\s+cup)?\b",
    r"\brotate\s+(?:it|the\s+cup)\s+180\b",
    r"\bupend\b",
    r"\bupright\b.*\bplace\b",
    r"\bplace\s+it\s+(?:the\s+)?right\s+(?:side\s+)?up\b",
    r"\bright.?side.?up\b",
    r"\bthe\s+(?:correct|right|proper)\s+way\s+(?:is|to)\s+(?:to\s+)?(?:flip|turn|invert)\b",
    r"\bjust\s+(?:flip|turn|invert)\b",
    r"\bsimply\s+(?:flip|turn|invert)\b",
    r"\bthe\s+opening\s+(?:should|needs? to)\s+(?:face|be\s+on)\s+(?:up|the\s+top)\b",
    r"\bturn\s+(?:it\s+)?back\s+(?:the\s+right\s+way|to\s+normal)\b",
    r"\breorient\b",
    r"\brotate\b.*\bup(?:ward|right)\b",
    r"\btilt\s+(?:it|the\s+cup)\b",
    r"\btip\s+(?:it|the\s+cup)\b",
    r"\bmouth\b.*\bfacing\s+up\b",
    r"\brim\b.*\b(?:facing\s+up|on\s+top)\b",
    r"\bopen(?:ing)?\s+(?:end|side)\s+(?:facing\s+)?up\b",
]

WRONG_PATTERNS = [
    r"\bdrill\b",
    r"\bcut\b.*\bhole\b",
    r"\bhole\b.*\bcut\b",
    r"\bpower\s+tool\b",
    r"\bsaw\b",
    r"\bpoke\b.*\bhole\b",
    r"\breturn\b.*\bshop\b|\bshop\b.*\breturn\b",
    r"\bthrow\s+(?:it\s+)?away\b",
    r"\bdiscard\b",
    r"\buseless\b.*\bcannot\b",
    r"\bcannot\s+be\s+used\b",
    r"\bimpossible\s+to\s+use\b",
]


def _last_pos(patterns: list[str], text: str) -> int:
    """Return the position of the **last** occurrence of any pattern, or -1."""
    best = -1
    for p in patterns:
        for m in re.finditer(p, text):
            if m.start() > best:
                best = m.start()
    return best


def _has_flip(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in FLIP_PATTERNS)


def _has_wrong(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in WRONG_PATTERNS)


def _classify(text: str) -> Optional[str]:
    """Classify text as 'flip', 'wrong', or None.

    If flip is mentioned at all, the model demonstrates the key insight
    (the correct answer IS to flip). "Wrong" patterns like "drill a hole"
    may appear alongside flip as creative alternatives but don't negate
    the correct understanding. So flip takes priority when both are present.
    """
    has_f = _has_flip(text)
    has_w = _has_wrong(text)

    if has_f:
        return "flip"
    if has_w:
        return "wrong"
    return None


class InvertedCupParser(ResponseParser):
    """Multi-strategy parser for Inverted Cup responses."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value="wrong",
                raw_response=response or "",
                parse_strategy="empty",
                confidence=0.0,
                error="Empty response",
            )

        text = response.strip()

        # --- Strategy 1: LaTeX boxed (last match) ---
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text, re.IGNORECASE)
        if boxed:
            result = _classify(boxed.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # --- Strategy 2: Bold (last match) ---
        bold = re_search_last(r"\*\*([^*]{1,80})\*\*", text)
        if bold:
            result = _classify(bold.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="bold", confidence=0.9)

        # --- Strategy 3: Labelled answer line (last match) ---
        label_match = re_search_last(
            r"(?:answer|action|solution|recommendation|suggestion|step\s+1|first(?:ly)?)\s*[:：]\s*([^\n.]{1,150})",
            text,
            re.IGNORECASE,
        )
        if label_match:
            result = _classify(label_match.group(1))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="label_line", confidence=0.88)

        # --- Strategy 4: Strong recommendation sentence (last match) ---
        strong = re_search_last(
            r"(?:you\s+(?:should|need\s+to|just\s+need\s+to|can)|simply|just|all\s+you\s+(?:need\s+to\s+do|have\s+to\s+do)(?:\s+is)?|the\s+(?:solution|answer|fix)\s+is\s+to)\s+([^\n.]{1,100})",
            text,
            re.IGNORECASE,
        )
        if strong:
            result = _classify(strong.group(0))
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="strong_recommendation", confidence=0.85)

        # --- Strategy 5: Full text ---
        result = _classify(text)
        if result:
            return ParsedAnswer(value=result, raw_response=text, parse_strategy="full_text", confidence=0.7)

        # --- Strategy 6: Last sentences (end-first) ---
        for sent in reversed(last_sentences(text, n=5)):
            result = _classify(sent)
            if result:
                return ParsedAnswer(value=result, raw_response=text, parse_strategy="last_sentences", confidence=0.6)

        # --- Fallback ---
        return ParsedAnswer(
            value="wrong",
            raw_response=text,
            parse_strategy="fallback",
            confidence=0.1,
            error="Could not extract flip/wrong signal",
        )
