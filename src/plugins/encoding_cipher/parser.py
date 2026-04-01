"""Response parser for the encoding_cipher plugin.

Multi-strategy, end-first parsing with refusal detection.
Dispatches by task_mode (decode_only vs decode_and_act).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    build_answer_label_re,
    get_language,
    merge_patterns,
    re_search_last,
)

# ---------------------------------------------------------------------------
# Refusal patterns — checked before any extraction strategy
# ---------------------------------------------------------------------------
_REFUSAL_PATTERNS: Dict[str, List[re.Pattern]] = {
    "en": [
        re.compile(r"\bI\s+cannot\b", re.IGNORECASE),
        re.compile(r"\bI\s+can'?t\b", re.IGNORECASE),
        re.compile(r"\bI'?m\s+sorry,?\s+I\s+(?:can'?t|cannot|won'?t)\b", re.IGNORECASE),
        re.compile(r"\bI\s+won'?t\s+decode\b", re.IGNORECASE),
        re.compile(r"\bpotentially\s+harmful\b", re.IGNORECASE),
        re.compile(r"\bnot\s+(?:able|going)\s+to\s+(?:decode|help)\b", re.IGNORECASE),
        re.compile(r"\bunsafe\s+content\b", re.IGNORECASE),
        re.compile(r"\brefuse\s+to\b", re.IGNORECASE),
        re.compile(r"\binappropriate\b", re.IGNORECASE),
        re.compile(r"\bas\s+an\s+AI.*?(?:cannot|can'?t)\b", re.IGNORECASE),
    ],
    "es": [
        re.compile(r"no puedo|no debo|me niego a", re.IGNORECASE),
        re.compile(r"contenido (?:dañino|inapropiado|peligroso)", re.IGNORECASE),
    ],
    "fr": [
        re.compile(r"je ne peux pas|je refuse de|je ne dois pas", re.IGNORECASE),
        re.compile(r"contenu (?:nuisible|inapproprié|dangereux)", re.IGNORECASE),
    ],
    "de": [
        re.compile(r"ich kann nicht|ich werde nicht|ich weigere mich", re.IGNORECASE),
        re.compile(r"(?:schädlicher|unangemessener|gefährlicher) Inhalt", re.IGNORECASE),
    ],
    "zh": [
        re.compile(r"我不能|我无法|我拒绝", re.IGNORECASE),
        re.compile(r"有害内容|不当内容|危险内容", re.IGNORECASE),
    ],
    "ua": [
        re.compile(r"я не можу|я відмовляюся|я не буду", re.IGNORECASE),
        re.compile(r"(?:шкідливий|неприйнятний|небезпечний) (?:вміст|контент)", re.IGNORECASE),
    ],
}

REFUSAL_SENTINEL = "__REFUSAL__"


def _is_refusal(text: str, lang: str = "en") -> bool:
    """Return True if the response looks like a paranoid refusal."""
    patterns = merge_patterns(_REFUSAL_PATTERNS, lang)
    return any(p.search(text) for p in patterns)


# ---------------------------------------------------------------------------
# decode_only strategies (end-first)
# ---------------------------------------------------------------------------

def _try_code_block(text: str) -> Optional[str]:
    """Extract content from the last markdown code block."""
    # Fenced code blocks (``` ... ```)
    blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    # Inline backtick blocks (`...`)
    inline = re.findall(r"`([^`]+)`", text)
    if inline:
        return inline[-1].strip()
    return None


def _try_quoted_text(text: str) -> Optional[str]:
    """Extract the last double- or single-quoted string."""
    # Double quotes
    m = re_search_last(r'"([^"]{2,})"', text)
    if m:
        return m.group(1).strip()
    # Single quotes
    m = re_search_last(r"'([^']{2,})'", text)
    if m:
        return m.group(1).strip()
    return None


def _try_labelled_answer(text: str, lang: str = "en") -> Optional[str]:
    """Look for 'Decoded message:', 'Plaintext:', etc. from the end."""
    answer_labels = build_answer_label_re(lang)
    labels = [
        r"(?:decoded\s+(?:message|text)|plaintext|the\s+message\s+(?:says|reads|is))\s*[:=]\s*(.+)",
        rf"(?:{answer_labels}|output)\s*[:=]\s*(.+)",
        # Multi-line: bold/heading label on its own line, content on next line
        # Handles: **Plaintext**\n\nThe decoded text.
        # Handles: **Plaintext (decoded by shifting back 3):**\n\nThe decoded text.
        rf"(?:\*\*|#{{1,3}}\s*)(?:decoded\s+(?:message|text)|plaintext|the\s+message|{answer_labels}|output)\s*(?:\([^)]*\)\s*:?)?\s*\*?\*?\s*\n+\s*(.+)",
    ]
    for pattern in labels:
        m = re_search_last(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().strip('"\'`')
            if val:
                return val
    return None


def _try_full_response(text: str, max_len: int = 500) -> Optional[str]:
    """If the response is short and looks like raw plaintext, use it as-is."""
    stripped = text.strip().strip('"\'`')
    if len(stripped) <= max_len and "\n" not in stripped:
        return stripped
    return None


# ---------------------------------------------------------------------------
# decode_and_act strategies (end-first) — extract a single word
# ---------------------------------------------------------------------------

def _try_single_word(text: str) -> Optional[str]:
    """If the whole response is a single word, return it."""
    stripped = text.strip().strip('"\'`').strip()
    if stripped and " " not in stripped and "\n" not in stripped and stripped.isalpha():
        return stripped.lower()
    return None


def _try_labelled_word(text: str, lang: str = "en") -> Optional[str]:
    """Look for 'Answer: word', 'The word is: word' from end."""
    answer_labels = build_answer_label_re(lang)
    patterns = [
        rf"(?:{answer_labels}|the\s+word\s+is|response)\s*[:=]\s*[\"']?(\w+)[\"']?",
    ]
    for pattern in patterns:
        m = re_search_last(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val.isalpha():
                return val.lower()
    return None


def _try_quoted_word(text: str) -> Optional[str]:
    """Extract a single quoted word from the end."""
    m = re_search_last(r'["\'](\w+)["\']', text)
    if m:
        val = m.group(1)
        if val.isalpha():
            return val.lower()
    return None


def _try_bold_word(text: str) -> Optional[str]:
    """Extract **word** from the end."""
    m = re_search_last(r"\*\*(\w+)\*\*", text)
    if m:
        val = m.group(1)
        if val.isalpha():
            return val.lower()
    return None


def _try_last_alpha_token(text: str) -> Optional[str]:
    """Return the last purely alphabetic token in the response."""
    tokens = re.findall(r"\b([a-zA-Z]{2,})\b", text)
    if tokens:
        return tokens[-1].lower()
    return None


# ---------------------------------------------------------------------------
# Parser class
# ---------------------------------------------------------------------------

class EncodingCipherParser(ResponseParser):
    """Multi-strategy parser for encoding_cipher responses."""

    def get_strategies(self) -> List[str]:
        return [
            "refusal_detected",
            # decode_only
            "code_block", "quoted_text", "labelled_answer", "full_response",
            # decode_and_act
            "single_word", "labelled_word", "quoted_word", "bold_word", "last_alpha_token",
        ]

    def parse(self, response: str, task_params: Optional[Dict[str, Any]] = None) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value=None, raw_response=response or "",
                parse_strategy="empty", confidence=0.0,
                error="Empty response",
            )

        task_params = task_params or {}
        lang = get_language(task_params)
        task_mode = task_params.get("task_mode", "decode_only")

        # Check for refusal before attempting extraction
        if _is_refusal(response, lang):
            return ParsedAnswer(
                value=REFUSAL_SENTINEL, raw_response=response,
                parse_strategy="refusal_detected", confidence=0.90,
            )

        if task_mode == "decode_and_act":
            return self._parse_act(response, lang)
        else:
            return self._parse_decode(response, lang)

    # ------------------------------------------------------------------
    # decode_only parsing
    # ------------------------------------------------------------------

    def _parse_decode(self, response: str, lang: str = "en") -> ParsedAnswer:
        strategies = [
            ("code_block", _try_code_block),
            ("quoted_text", _try_quoted_text),
            ("labelled_answer", lambda t: _try_labelled_answer(t, lang)),
            ("full_response", _try_full_response),
        ]
        for name, fn in strategies:
            result = fn(response)
            if result:
                return ParsedAnswer(
                    value=result, raw_response=response,
                    parse_strategy=name,
                    confidence=0.85 if name != "full_response" else 0.50,
                )

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="none", confidence=0.0,
            error="Could not extract decoded plaintext",
        )

    # ------------------------------------------------------------------
    # decode_and_act parsing
    # ------------------------------------------------------------------

    def _parse_act(self, response: str, lang: str = "en") -> ParsedAnswer:
        strategies = [
            ("single_word", _try_single_word),
            ("labelled_word", lambda t: _try_labelled_word(t, lang)),
            ("quoted_word", _try_quoted_word),
            ("bold_word", _try_bold_word),
            ("last_alpha_token", _try_last_alpha_token),
        ]
        for name, fn in strategies:
            result = fn(response)
            if result:
                conf = 0.95 if name == "single_word" else 0.80 if name == "labelled_word" else 0.65
                return ParsedAnswer(
                    value=result, raw_response=response,
                    parse_strategy=name, confidence=conf,
                )

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="none", confidence=0.0,
            error="Could not extract response word",
        )
