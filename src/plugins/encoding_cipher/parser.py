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
    strip_verification_tail,
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

def _try_context_anchored_bold(text: str) -> Optional[str]:
    """Context-anchored extraction of **bold plaintext** spans.

    Covers Groups B/D (decodes to: **...**) and E (plaintext is: **...**)
    from annotation data — combined 100% and 80-90% capture exact rates.
    """
    # Group E: "plaintext is: **...**" — 100% exact capture
    m = re.search(r"(?i)plaintext\s+is:\s*\*\*([^*\n]+?)\*\*", text)
    if m:
        return m.group(1).strip()

    # Groups B+D: "decodes to: **...**" — 80-90% exact; allow newlines between anchor and bold
    m = re.search(r"(?i)decodes?\s+to:\s*\n*\s*\*\*([^*\n]+?)\*\*", text)
    if m:
        return m.group(1).strip()

    # Variant: "decoded plaintext is: **...**"
    m = re.search(r"(?i)(?:decoded\s+)?plaintext\s+(?:is|was):\s*\*\*([^*\n]+?)\*\*", text)
    if m:
        return m.group(1).strip()

    # Variant: "reveals: **...**"
    m = re.search(r"(?i)reveals?\s*:\s*\*\*([^*\n]+?)\*\*", text)
    if m:
        return m.group(1).strip()

    return None


def _try_blockquote_after_label(text: str) -> Optional[str]:
    """Extract plaintext from a > blockquote following a 'decoded plaintext' label.

    Covers Group A (29 cases): **Decoded plaintext (ROT13):**\\n\\n> text
    and the middle+plain long-tail (3 cases).
    """
    # Pattern 1: "**Decoded plaintext (ROT13):**\n\n> Full sentence."
    # [^*]* handles "(ROT13)", "(rot-13)", "(Caesar 3)", etc.
    m = re.search(
        r"(?i)\*\*decoded\s+plaintext[^*]*\*\*\s*:?\s*\n+\s*>+\s*([^\n]+)",
        text,
    )
    if m:
        candidate = re.sub(r"^>+\s*", "", m.group(1)).strip()
        if len(candidate) >= 10:
            return candidate

    # Pattern 2: inline — label and blockquote on the same line
    m = re.search(
        r"(?i)\*\*decoded\s+plaintext[^*]*\*\*\s*:?\s*>+\s*([^\n]+)",
        text,
    )
    if m:
        candidate = m.group(1).strip()
        if len(candidate) >= 10:
            return candidate

    # Pattern 3: non-bold label variant "Decoded text:\n\n> sentence."
    m = re.search(
        r"(?i)decoded\s+(?:plaintext|text|message)\s*:?\s*\n+\s*>+\s*([^\n]+)",
        text,
    )
    if m:
        candidate = re.sub(r"^>+\s*", "", m.group(1)).strip()
        if len(candidate) >= 10:
            return candidate

    return None


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
    """Extract quoted plaintext, preferring anchored 'we get: \"...\"' patterns (Group C)."""
    # Anchored: "we get:\n\n\"Full sentence.\"" — Group C
    m = re.search(r'(?i)we\s+get:\s*\n*\s*"([^"]{10,})"', text)
    if m:
        return m.group(1).strip()

    # Anchored variant: "combining ... we get: \"...\""
    m = re.search(r'(?i)combining[^.]*we\s+get:\s*\n*\s*"([^"]{10,})"', text)
    if m:
        return m.group(1).strip()

    # Bare fallback — last double-quoted span; raised minimum length, no newlines
    m = re_search_last(r'"([^"\n]{15,})"', text)
    if m:
        return m.group(1).strip()

    # Single-quote fallback (tightened)
    m = re_search_last(r"'([^'\n]{15,})'", text)
    if m:
        return m.group(1).strip()

    return None


def _try_labelled_answer(text: str, lang: str = "en") -> Optional[str]:
    """Look for 'Decoded message:', 'Plaintext:', etc.

    Uses re_search_last for single-line patterns (end-first).
    Uses re.search (first match) for the multi-line bold variant because the
    decoded-plaintext label appears once; re_search_last would find later
    section headers (validation, notes) instead.
    """
    answer_labels = build_answer_label_re(lang)
    # Single-line patterns — end-first
    single_line = [
        r"(?:decoded\s+(?:message|text)|plaintext|the\s+message\s+(?:says|reads|is))\s*[:=]\s*(.+)",
        # Removed "|output" — fires on intermediate step outputs in analytical responses
        rf"(?:{answer_labels})\s*[:=]\s*(.+)",
    ]
    for pattern in single_line:
        m = re_search_last(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().strip('"\'`')
            if val:
                return val

    # Multi-line: bold/heading label on its own line, content on next line
    # Uses re.search (FIRST match) — the decoded-plaintext label appears once.
    # Strips optional > blockquote prefix from the captured content.
    multiline_pattern = (
        rf"(?:\*\*|#{{1,3}}\s*)"
        rf"(?:decoded\s+(?:message|text)|plaintext|the\s+message|{answer_labels})"
        rf"\s*(?:\([^)]*\)\s*:?)?\s*\*?\*?\s*\n+\s*>?\s*(.+)"
    )
    m = re.search(multiline_pattern, text, re.IGNORECASE)
    if m:
        val = m.group(1).strip().strip('"\'`')
        if val:
            return val

    return None


# ---------------------------------------------------------------------------
# Bold / italic fallback strategies (decode_only)
# ---------------------------------------------------------------------------

_BOLD_HEADER_RE = re.compile(
    r"^(?:step\s+\d|note[:\s]|important[:\s]|warning[:\s]|"
    r"final\s+answer[:\s]|decoded\s+plaintext)",
    re.IGNORECASE,
)


def _try_italic_phrase(text: str) -> Optional[str]:
    """Extract *italic plaintext phrase* following a decoded label (long-tail format)."""
    # Anchored: decoded label followed by italic phrase on next line
    m = re.search(
        r"(?i)decod(?:ed|es?)\s+(?:plaintext|text|message)[^:]*:?\s*\n+\s*\*(?!\*)([^*\n]{10,}?)\*(?!\*)",
        text,
    )
    if m:
        return m.group(1).strip()

    # Unanchored: only fire if no substantial bold spans exist (avoids shadowing bold strategies)
    if not re.search(r"\*\*[^*\n]{10,}\*\*", text):
        m = re_search_last(r"(?<!\*)\*(?!\*)([^*\n]{15,}?)\*(?!\*)", text)
        if m:
            return m.group(1).strip()

    return None


def _try_bold_plaintext(text: str) -> Optional[str]:
    """Broad fallback: last substantial **bold phrase** that isn't a section header."""
    candidates = re.findall(r"\*\*([^*\n]{10,}?)\*\*", text)
    if not candidates:
        return None
    viable = [c for c in candidates if not _BOLD_HEADER_RE.match(c.strip())]
    if not viable:
        return None
    return viable[-1].strip()


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
            "context_anchored_bold", "blockquote_after_label",
            "code_block", "quoted_text", "labelled_answer",
            "italic_phrase", "bold_plaintext", "full_response",
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
        # Strip trailing validation/verification sections before any extraction.
        # Analytical responses often append "Step N: Validation" that confuses
        # quote and label strategies.
        text = strip_verification_tail(response)

        _CONFIDENCE = {
            "context_anchored_bold":  0.92,
            "blockquote_after_label": 0.85,
            "code_block":             0.85,
            "quoted_text":            0.85,
            "labelled_answer":        0.80,
            "italic_phrase":          0.75,
            "bold_plaintext":         0.70,
            "full_response":          0.50,
        }
        strategies = [
            ("context_anchored_bold",  _try_context_anchored_bold),
            ("blockquote_after_label", _try_blockquote_after_label),
            ("code_block",             _try_code_block),
            ("quoted_text",            _try_quoted_text),
            ("labelled_answer",        lambda t: _try_labelled_answer(t, lang)),
            ("italic_phrase",          _try_italic_phrase),
            ("bold_plaintext",         _try_bold_plaintext),
            ("full_response",          _try_full_response),
        ]
        for name, fn in strategies:
            result = fn(text)
            if result:
                return ParsedAnswer(
                    value=result, raw_response=response,
                    parse_strategy=name,
                    confidence=_CONFIDENCE.get(name, 0.75),
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
