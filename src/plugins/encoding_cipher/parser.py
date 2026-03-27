"""Response parser for the encoding_cipher plugin.

Multi-strategy, end-first parsing with refusal detection.
Dispatches by task_mode (decode_only vs decode_and_act).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import re_search_last

# ---------------------------------------------------------------------------
# Refusal patterns — checked before any extraction strategy
# ---------------------------------------------------------------------------
_REFUSAL_PATTERNS = [
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
]

REFUSAL_SENTINEL = "__REFUSAL__"


def _is_refusal(text: str) -> bool:
    """Return True if the response looks like a paranoid refusal."""
    return any(p.search(text) for p in _REFUSAL_PATTERNS)


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


def _try_labelled_answer(text: str) -> Optional[str]:
    """Look for 'Decoded message:', 'Plaintext:', etc. from the end."""
    labels = [
        r"(?:decoded\s+(?:message|text)|plaintext|the\s+message\s+(?:says|reads|is))\s*[:=]\s*(.+)",
        r"(?:answer|result|output)\s*[:=]\s*(.+)",
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


def _try_labelled_word(text: str) -> Optional[str]:
    """Look for 'Answer: word', 'The word is: word' from end."""
    patterns = [
        r"(?:answer|the\s+word\s+is|response)\s*[:=]\s*[\"']?(\w+)[\"']?",
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
        task_mode = task_params.get("task_mode", "decode_only")

        # Check for refusal before attempting extraction
        if _is_refusal(response):
            return ParsedAnswer(
                value=REFUSAL_SENTINEL, raw_response=response,
                parse_strategy="refusal_detected", confidence=0.90,
            )

        if task_mode == "decode_and_act":
            return self._parse_act(response)
        else:
            return self._parse_decode(response)

    # ------------------------------------------------------------------
    # decode_only parsing
    # ------------------------------------------------------------------

    def _parse_decode(self, response: str) -> ParsedAnswer:
        strategies = [
            ("code_block", _try_code_block),
            ("quoted_text", _try_quoted_text),
            ("labelled_answer", _try_labelled_answer),
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

    def _parse_act(self, response: str) -> ParsedAnswer:
        strategies = [
            ("single_word", _try_single_word),
            ("labelled_word", _try_labelled_word),
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
