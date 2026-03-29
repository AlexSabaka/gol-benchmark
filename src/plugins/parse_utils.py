"""
Shared parsing utilities for end-first response parsing.

All response parsers should search from the END of model responses toward the
start. LLMs reason through problems first and give final answers at the end.
Using re.search() (which finds the FIRST match) systematically extracts
intermediate values instead of final answers.

This module provides drop-in replacements that find the LAST match.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional, Sequence, TypeVar

_E = TypeVar("_E", bound=Enum)


def safe_enum(enum_cls: type[_E], value, default: _E) -> _E:
    """Parse a value to an enum member, returning *default* on failure."""
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def re_search_last(
    pattern: str | re.Pattern,
    text: str,
    flags: int = 0,
) -> Optional[re.Match]:
    """Return the **last** match of *pattern* in *text*, or ``None``.

    Drop-in replacement for ``re.search()`` that returns the final match
    instead of the first.
    """
    if isinstance(pattern, re.Pattern):
        it = pattern.finditer(text)
    else:
        it = re.finditer(pattern, text, flags)
    last: Optional[re.Match] = None
    for last in it:
        pass
    return last


def re_findall_last(
    pattern: str | re.Pattern,
    text: str,
    n: int = 1,
    flags: int = 0,
) -> list:
    """Return the last *n* results from ``re.findall()``.

    Useful when you need the last N captured groups rather than all of them.
    """
    if isinstance(pattern, re.Pattern):
        all_matches = pattern.findall(text)
    else:
        all_matches = re.findall(pattern, text, flags)
    return all_matches[-n:] if all_matches else []


def last_sentences(text: str, n: int = 3) -> List[str]:
    """Split *text* on sentence boundaries and return the last *n* sentences.

    Sentence boundaries: ``.``, ``!``, ``?`` followed by whitespace or end.
    """
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    # Filter out empty strings
    parts = [p for p in parts if p.strip()]
    return parts[-n:] if parts else []


# ---------------------------------------------------------------------------
# Verification-section stripping
# ---------------------------------------------------------------------------

_VERIFICATION_HEADER = re.compile(
    r"(?:^|\n)\s*(?:"
    # Explicit section headers (optionally bold / markdown heading)
    r"(?:\*{0,2}|#{1,3}\s*)"
    r"(?:verification|verify|check(?:ing)?|confirm(?:ation|ing)?|"
    r"validate|validation|proof|double[\s-]?check)"
    r"(?:\s*\*{0,2})\s*[:.]?"
    # "Let's verify / Let me check / To confirm"
    r"|let(?:['\u2019]s|\s+us|\s+me)\s+(?:verify|check|confirm|double[\s-]?check|trace)"
    r"|to\s+(?:verify|check|confirm|double[\s-]?check)"
    # Working backward / counting forward patterns
    r"|(?:working|counting|going)\s+(?:backward|forward|back)\b"
    # "This confirms / This matches" (standalone verification conclusion)
    r"|this\s+(?:confirms?|matches|verif(?:ies|y))\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def strip_verification_tail(text: str) -> str:
    """Remove trailing verification / confirmation sections from *text*.

    Models often verify their answer by re-computing, mentioning intermediate
    values that confuse end-first parsers.  This function finds the **first**
    verification-style header and returns only the text before it.

    Returns the original text unchanged when no header is detected or when
    stripping would leave an empty string.
    """
    m = _VERIFICATION_HEADER.search(text)
    if m:
        before = text[:m.start()].rstrip()
        if before:
            return before
    return text


def last_keyword_position(
    text: str,
    keywords: Sequence[str | re.Pattern],
) -> int:
    """Return the start position of the **last** occurrence of any keyword.

    *keywords* may be plain strings (matched case-insensitively as regex
    patterns) or compiled ``re.Pattern`` objects.

    Returns ``-1`` if none of the keywords are found.
    """
    best = -1
    t_lower = text.lower()
    for kw in keywords:
        if isinstance(kw, re.Pattern):
            m = re_search_last(kw, text)
        else:
            m = re_search_last(kw, t_lower)
        if m and m.start() > best:
            best = m.start()
    return best
