"""Response parser for the fancy_unicode plugin.

Multi-strategy, end-first parsing with refusal detection.
Dispatches by task_mode (decode_only vs decode_and_act).

This plugin is EN-only.  Strategies:

  decode_only:
    runaway → refusal → boxed → labelled_answer → bold → content_block → last_line

  decode_and_act:
    runaway → refusal → single_word → normalized_first_line → boxed →
    labelled_answer → labelled_word → quoted_word → bold_word → last_word
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import normalize_unicode, re_search_last, strip_verification_tail
from .families import decode_to_ascii

# ---------------------------------------------------------------------------
# Sentinel values
# ---------------------------------------------------------------------------

REFUSAL_SENTINEL = "__REFUSAL__"
RUNAWAY_SENTINEL = "__RUNAWAY__"

# ---------------------------------------------------------------------------
# Refusal patterns (EN only — model must recognise fancy Unicode on its own,
# but may refuse to process text it perceives as suspicious/garbled)
# ---------------------------------------------------------------------------

_REFUSAL_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bI\s+cannot\b", re.IGNORECASE),
    re.compile(r"\bI\s+can'?t\b", re.IGNORECASE),
    re.compile(r"\bI'?m\s+sorry,?\s+I\s+(?:can'?t|cannot|won'?t)\b", re.IGNORECASE),
    re.compile(r"\bI\s+won'?t\s+(?:decode|process|read|help)\b", re.IGNORECASE),
    re.compile(r"\bnot\s+(?:able|going)\s+to\s+(?:decode|process|read|help)\b", re.IGNORECASE),
    re.compile(r"\brefuse\s+to\b", re.IGNORECASE),
    re.compile(r"\bunsafe\s+content\b", re.IGNORECASE),
    re.compile(r"\binappropriate\b", re.IGNORECASE),
    re.compile(r"\bas\s+an\s+AI.*?(?:cannot|can'?t)\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bappears?\s+to\s+be\s+(?:encoded|encrypted|garbled|unreadable)\b.*\bcannot\b",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"\bunreadable\s+(?:characters?|text|symbols?)\b.*\bcannot\b",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"\bcannot\s+(?:process|decode|read|interpret|understand)\b", re.IGNORECASE),
    re.compile(r"\bunable\s+to\s+(?:decode|process|read|interpret|understand)\b", re.IGNORECASE),
]


def _is_refusal(text: str) -> bool:
    return any(p.search(text) for p in _REFUSAL_PATTERNS)


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

def _try_boxed(text: str) -> Optional[str]:
    r"""Extract \boxed{answer} or a bare {word} on its own line (end-first)."""
    # LaTeX boxed: \boxed{...}
    m = re_search_last(r"\\boxed\{([^}]+)\}", text)
    if m:
        return m.group(1).strip()
    # Bare braces on their own line: {answer}
    m = re_search_last(r"^\{([^}]+)\}\s*$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _try_labelled_answer(text: str) -> Optional[str]:
    """Look for 'Decoded: X', 'Plaintext: X', 'Answer: X', etc. (end-first)."""
    patterns = [
        # "decoded: X" / "decoded text: X" / "decoded text is: X"
        r"decoded?\s*(?:(?:text|message)\s*)?(?:is\s*)?[:=]\s*(.+)",
        # "plaintext: X" / "plain text: X" / "the message is: X"
        r"(?:plaintext|plain\s+text|the\s+(?:message|text)\s+(?:says|reads|is))\s*[:=]?\s*(.+)",
        # "answer: X" / "result: X" / "output: X"
        r"(?:answer|result|output|response)\s*[:=]\s*(.+)",
        # Bold/heading label on its own line, value on next line
        r"(?:\*\*|#{1,3}\s*)(?:decoded?\s*(?:text|message)?|plaintext|plain\s+text|answer|output)\s*\*?\*?\s*\n+\s*(.+)",
    ]
    for pattern in patterns:
        m = re_search_last(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().strip('"\'`')
            if val:
                return val
    return None


def _try_bold(text: str) -> Optional[str]:
    """Extract content from **...** (end-first)."""
    m = re_search_last(r"\*\*(.+?)\*\*", text)
    if m:
        val = m.group(1).strip()
        if val:
            return val
    return None


# ---------------------------------------------------------------------------
# Explanation-line detection (shared by decode_only strategies)
# ---------------------------------------------------------------------------

# These patterns indicate a line is a meta/explanatory comment, not decoded content.
# Used by _try_last_line and _try_content_block to skip non-answer lines.
_EXPLANATION_LINE_PATTERNS: List[re.Pattern] = [
    # Full parenthetical: (The text uses subscript characters, ...)
    re.compile(r"^\s*\(.*\)\s*$"),
    # Bare markdown artifacts or near-empty: **, *, ##, etc.
    re.compile(r"^[\*#!\s]*$"),
    # Lines that name the encoding style/font (common in model explanations)
    re.compile(
        r"\b(?:font|encoding|character[s]?|style|unicode|fraktur|"
        r"subscript|superscript|diacritic[s]?|mathematical|alphanumeric|"
        r"italic|stylized|stylistic|decorative|block\s+letter[s]?|"
        r"fancy\s+letter[s]?|calligraph|script\s+font|special\s+font|"
        r"typewriter|monospace)\b",
        re.IGNORECASE,
    ),
    # Trailing commentary starters
    re.compile(
        r"^(?:note\s*:|the\s+text\s+(?:uses?|was|is)|"
        r"it(?:'s|\s+is)\s+written|written\s+in|"
        r"this\s+(?:text|sentence|passage|message)\s+(?:uses?|is|was)|"
        r"once\s+(?:deciphered|decoded|converted)|"
        r"clear\s+once|it\s+reads?[:\s])",
        re.IGNORECASE,
    ),
]


def _is_explanation_line(line: str) -> bool:
    """Return True if *line* looks like a meta/explanatory comment."""
    return any(p.search(line) for p in _EXPLANATION_LINE_PATTERNS)


def _clean_line(line: str) -> str:
    """Strip leading markdown markers and surrounding quotes from a line."""
    # Strip leading **, *, #, or mixed combinations (e.g. Grok's "** sentence")
    cleaned = re.sub(r"^[\*#\s]+", "", line)
    return cleaned.strip('"\'`').strip()


# ---------------------------------------------------------------------------
# decode_only specific
# ---------------------------------------------------------------------------

def _try_last_line(text: str) -> Optional[str]:
    """Walk lines from bottom; return the last non-explanation content line.

    Improvements over plain "last non-empty line":
    - Strips leading ** / # / * markdown artifacts (Grok pattern B, K)
    - Skips trailing parenthetical explanations (Haiku pattern G)
    - Skips font/style commentary lines (Gemma-3 pattern H)
    - Falls back to the raw last line if all lines are explanatory
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None

    # Walk from bottom, skip explanation lines
    for line in reversed(lines):
        cleaned = _clean_line(line)
        if not cleaned or len(cleaned) < 5:
            continue
        if _is_explanation_line(line):
            continue
        return cleaned

    # Fallback: last non-empty line, just clean markdown
    return _clean_line(lines[-1]) or None


def _try_content_block(text: str) -> Optional[str]:
    """Collect consecutive non-explanation lines into a single decoded block.

    Handles models that write each decoded sentence on its own line, then add
    an explanation (pattern I).  Returns lines 1–N joined with spaces, stopping
    at the first explanation line.  Only fires when ≥ 2 content lines exist.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    content_lines: List[str] = []

    for line in lines:
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if _is_explanation_line(line):
            # Stop collecting — everything after this is commentary
            if content_lines:
                break
            # If we haven't started yet, skip and keep looking
            continue
        content_lines.append(cleaned)

    if len(content_lines) >= 2:
        joined = " ".join(content_lines)
        if len(joined) > 20:  # sanity: must be a real sentence, not artifacts
            return joined
    return None


# ---------------------------------------------------------------------------
# decode_and_act specific
# ---------------------------------------------------------------------------

def _try_single_word(text: str) -> Optional[str]:
    """If the whole response is a single alphabetic word, return it.

    Also handles responses that are a single fancy-Unicode-encoded word
    (e.g. small_caps or Tier-3 emoji blocks) by normalising first.
    """
    stripped = text.strip().strip('"\'`').strip()
    if not stripped or " " in stripped or "\n" in stripped:
        return None
    if stripped.isalpha():
        return stripped.lower()
    # Try fancy Unicode decode — covers Tier-3 emoji blocks (isalpha() → False)
    # and single-char edge cases
    decoded = decode_to_ascii(stripped)
    if decoded and decoded.isalpha() and " " not in decoded:
        return decoded.lower()
    return None


def _try_normalized_first_line(text: str) -> Optional[str]:
    """Decode fancy Unicode in the first non-empty line; return it if a single word.

    Handles the common model pattern of echoing the encoded answer on the
    first line, then adding explanation (e.g. ``𝘱𝘢𝘭𝘢𝘯𝘲𝘶𝘪𝘯\\n\\n(As requested!)``).
    """
    decoded_full = decode_to_ascii(text)
    lines = [ln.strip() for ln in decoded_full.splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[0].strip(".,;:!?\"'`").strip()
    if first.isalpha() and 2 <= len(first) <= 40:
        return first.lower()
    return None


def _try_labelled_word(text: str) -> Optional[str]:
    """Look for 'Answer: word', 'The word is word' (end-first, single word)."""
    patterns = [
        r"(?:answer|result|the\s+word\s+is|response)\s*[:=]\s*[\"']?(\w+)[\"']?",
    ]
    for pattern in patterns:
        m = re_search_last(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val.isalpha():
                return val.lower()
    return None


def _try_quoted_word(text: str) -> Optional[str]:
    """Extract the last single-word quoted string."""
    m = re_search_last(r'["\']([a-zA-Z]+)["\']', text)
    if m:
        return m.group(1).lower()
    return None


def _try_bold_word(text: str) -> Optional[str]:
    """Extract the last **word** (single alpha token)."""
    m = re_search_last(r"\*\*([a-zA-Z]+)\*\*", text)
    if m:
        return m.group(1).lower()
    return None


_LAST_WORD_STOPWORDS: frozenset = frozenset({
    # Instruction-fragment words that appear at the end of templated instructions
    "else", "only", "that", "word", "more", "nothing", "above",
    # Common English function words likely from trailing commentary
    "the", "and", "but", "for", "not", "this", "with", "are", "was",
    "has", "had", "have", "been", "its", "our", "your", "their",
    # Meta-commentary words
    "note", "here", "just", "shown", "given", "below", "said", "tells",
})


def _try_last_word(text: str) -> Optional[str]:
    """Return the last alphabetic token (3+ chars) in the response.

    Skips common stop-words and instruction-fragment words to avoid
    capturing 'else', 'only', 'Note:' etc. from the end of a response
    that paraphrases the decode_and_act instruction (pattern J).
    """
    tokens = re.findall(r"\b([a-zA-Z]{2,})\b", text)
    for tok in reversed(tokens):
        lower = tok.lower()
        if len(lower) >= 3 and lower not in _LAST_WORD_STOPWORDS:
            return lower
    # Final fallback: any 2+ char token
    if tokens:
        return tokens[-1].lower()
    return None


# ---------------------------------------------------------------------------
# Parser class
# ---------------------------------------------------------------------------

class FancyUnicodeParser(ResponseParser):
    """Multi-strategy end-first parser for fancy_unicode responses.

    Dispatches by task_mode in task_params.
    decode_only  → extract the decoded plaintext
    decode_and_act → extract the single response word
    """

    def get_strategies(self) -> List[str]:
        return [
            "runaway_refusal", "refusal_detected",
            # decode_only
            "boxed", "labelled_answer", "bold", "content_block", "last_line",
            # decode_and_act
            "single_word", "normalized_first_line", "boxed", "labelled_answer",
            "labelled_word", "quoted_word", "bold_word", "last_word",
        ]

    def parse(self, response: str, task_params: Optional[Dict[str, Any]] = None) -> ParsedAnswer:
        task_params = task_params or {}

        # 0. Runaway — response hit max_tokens without a usable answer
        if task_params.get("hit_max_tokens"):
            return ParsedAnswer(
                value=RUNAWAY_SENTINEL, raw_response=response or "",
                parse_strategy="runaway_refusal", confidence=0.0,
            )

        if not response or not response.strip():
            return ParsedAnswer(
                value=None, raw_response=response or "",
                parse_strategy="empty", confidence=0.0,
                error="Empty response",
            )

        task_mode = task_params.get("task_mode", "decode_only")
        response = normalize_unicode(response)

        # 1. Refusal detection (before extraction)
        if _is_refusal(response):
            return ParsedAnswer(
                value=REFUSAL_SENTINEL, raw_response=response,
                parse_strategy="refusal_detected", confidence=0.90,
            )

        cleaned = strip_verification_tail(response)

        if task_mode == "decode_and_act":
            return self._parse_act(cleaned, response)
        else:
            return self._parse_decode(cleaned, response)

    # ------------------------------------------------------------------
    # decode_only
    # ------------------------------------------------------------------

    def _parse_decode(self, cleaned: str, raw: str) -> ParsedAnswer:
        strategies = [
            ("boxed",           0.90, _try_boxed),
            ("labelled_answer", 0.85, _try_labelled_answer),
            ("bold",            0.75, _try_bold),
            ("content_block",   0.70, _try_content_block),  # multi-line answers (I)
            ("last_line",       0.60, _try_last_line),       # filtered, markdown-stripped (G,H,K)
        ]
        for name, conf, fn in strategies:
            result = fn(cleaned)
            if result:
                return ParsedAnswer(
                    value=result, raw_response=raw,
                    parse_strategy=name, confidence=conf,
                )
        return ParsedAnswer(
            value=None, raw_response=raw,
            parse_strategy="fallback", confidence=0.0,
            error="Could not extract decoded plaintext",
        )

    # ------------------------------------------------------------------
    # decode_and_act
    # ------------------------------------------------------------------

    def _parse_act(self, cleaned: str, raw: str) -> ParsedAnswer:
        # Single-word strategy applied to the full (uncleaned) response first
        # — if the whole response is one word, trust it with high confidence.
        result = _try_single_word(raw)
        if result:
            return ParsedAnswer(
                value=result, raw_response=raw,
                parse_strategy="single_word", confidence=0.95,
            )

        # Normalised first-line: decode any fancy encoding, check if first
        # line is a single word (handles models that echo encoded answer + explain)
        result = _try_normalized_first_line(raw)
        if result:
            return ParsedAnswer(
                value=result, raw_response=raw,
                parse_strategy="normalized_first_line", confidence=0.90,
            )

        strategies = [
            ("boxed",           0.90, _try_boxed),
            ("labelled_answer", 0.85, _try_labelled_answer),
            ("labelled_word",   0.85, _try_labelled_word),
            ("quoted_word",     0.70, _try_quoted_word),
            ("bold_word",       0.70, _try_bold_word),
            ("last_word",       0.60, _try_last_word),
        ]
        for name, conf, fn in strategies:
            result = fn(cleaned)
            if result:
                return ParsedAnswer(
                    value=result, raw_response=raw,
                    parse_strategy=name, confidence=conf,
                )
        return ParsedAnswer(
            value=None, raw_response=raw,
            parse_strategy="fallback", confidence=0.0,
            error="Could not extract response word",
        )
