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
from typing import Any, Dict, List, Optional, Sequence, TypeVar

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


# ---------------------------------------------------------------------------
# Multilingual keyword utilities
# ---------------------------------------------------------------------------

def merge_keywords(keyword_dict: Dict[str, List[str]], language: str) -> List[str]:
    """Merge English keywords with target language keywords.

    Always includes English as fallback since models often respond
    in English even when prompted in another language.
    """
    en = keyword_dict.get("en", [])
    if language == "en":
        return en
    local = keyword_dict.get(language, [])
    return list(dict.fromkeys(en + local))  # dedupe preserving order


def merge_patterns(
    pattern_dict: Dict[str, List[re.Pattern]],
    language: str,
) -> List[re.Pattern]:
    """Like merge_keywords but for compiled regex patterns."""
    en = pattern_dict.get("en", [])
    if language == "en":
        return en
    local = pattern_dict.get(language, [])
    return en + local


def get_language(task_params: Dict[str, Any]) -> str:
    """Extract language code from task_params, defaulting to 'en'."""
    return task_params.get("language", "en")


# ---------------------------------------------------------------------------
# Shared multilingual number-word map
# ---------------------------------------------------------------------------

WORD_TO_INT: Dict[str, Dict[str, int]] = {
    "en": {
        "zero": 0, "no": 0, "none": 0,
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    },
    "es": {
        "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
        "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
        "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
        "veinte": 20,
    },
    "fr": {
        "zéro": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4,
        "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
        "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
        "seize": 16, "dix-sept": 17, "dix-huit": 18, "dix-neuf": 19,
        "vingt": 20,
    },
    "de": {
        "null": 0, "eins": 1, "ein": 1, "eine": 1, "zwei": 2, "drei": 3,
        "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8,
        "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13,
        "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17,
        "achtzehn": 18, "neunzehn": 19, "zwanzig": 20,
    },
    "zh": {
        "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    },
    "ua": {
        "нуль": 0, "один": 1, "одна": 1, "два": 2, "дві": 2, "три": 3,
        "чотири": 4, "п'ять": 5, "шість": 6, "сім": 7, "вісім": 8,
        "дев'ять": 9, "десять": 10, "одинадцять": 11, "дванадцять": 12,
        "тринадцять": 13, "чотирнадцять": 14, "п'ятнадцять": 15,
        "шістнадцять": 16, "сімнадцять": 17, "вісімнадцять": 18,
        "дев'ятнадцять": 19, "двадцять": 20,
    },
}


def build_word_to_int(language: str) -> Dict[str, int]:
    """Merge English + target language number word maps."""
    merged = dict(WORD_TO_INT["en"])
    if language != "en" and language in WORD_TO_INT:
        merged.update(WORD_TO_INT[language])
    return merged


# ---------------------------------------------------------------------------
# Shared multilingual answer labels
# ---------------------------------------------------------------------------

ANSWER_LABELS: Dict[str, List[str]] = {
    "en": ["answer", "result", "final answer", "solution", "response"],
    "es": ["respuesta", "resultado", "respuesta final", "solución"],
    "fr": ["réponse", "résultat", "réponse finale", "solution"],
    "de": ["antwort", "ergebnis", "endgültige antwort", "lösung"],
    "zh": ["答案", "结果", "最终答案", "解答"],
    "ua": ["відповідь", "результат", "остаточна відповідь", "рішення"],
}


def build_answer_label_re(language: str) -> str:
    """Build a regex alternation of answer labels for the given language.

    Returns a pattern like ``answer|result|final answer|respuesta|resultado``
    that can be embedded in a larger regex.
    """
    labels = merge_keywords(ANSWER_LABELS, language)
    return "|".join(re.escape(l) for l in labels)


# ---------------------------------------------------------------------------
# Shared yes/no words
# ---------------------------------------------------------------------------

YES_WORDS: Dict[str, List[str]] = {
    "en": ["yes", "true", "correct", "right"],
    "es": ["sí", "si", "verdadero", "correcto"],
    "fr": ["oui", "vrai", "correct", "exacte"],
    "de": ["ja", "richtig", "korrekt", "wahr"],
    "zh": ["是", "对", "正确", "是的"],
    "ua": ["так", "правда", "правильно", "вірно"],
}

NO_WORDS: Dict[str, List[str]] = {
    "en": ["no", "false", "incorrect", "wrong"],
    "es": ["no", "falso", "incorrecto"],
    "fr": ["non", "faux", "incorrect"],
    "de": ["nein", "falsch", "inkorrekt", "unwahr"],
    "zh": ["不", "否", "错", "不是", "错误"],
    "ua": ["ні", "неправда", "невірно", "неправильно"],
}
