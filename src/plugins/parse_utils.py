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
from typing import Any, Dict, List, Optional, Sequence, TypeVar, Union

_E = TypeVar("_E", bound=Enum)

Number = Union[int, float]


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
# Parser-offset resolver (Phase 2)
# ---------------------------------------------------------------------------


def resolve_parser_offsets(
    raw_response: str, value: Any
) -> Optional[tuple[int, int]]:
    """Locate the substring in ``raw_response`` that produced ``value``.

    Phase 2 universal fallback — called at result-file write time for
    parsers that don't emit ``char_start`` / ``char_end`` natively. The
    frontend uses the returned offsets to paint the amber parser-highlight
    region reliably (substring-search client-side can lock onto the wrong
    occurrence or fail entirely on non-string values).

    Type contract:

    - ``str`` → searched directly.
    - ``int`` / ``float`` / ``bool`` → stringified and searched. ``True`` /
      ``False`` normalise to lower-case ``"true"`` / ``"false"`` to match
      how models typically write them.
    - ``list`` / ``dict`` / any non-scalar → returns ``None``. These are
      constructed / computed values (grids, ranked lists) with no single
      contiguous substring in the response.
    - ``None`` / empty → returns ``None``.

    Search order:

    1. **Last** exact occurrence (end-first parser convention, CLAUDE.md §6).
    2. Last case-insensitive occurrence (models often capitalise differently
       than the normalised canonical form).

    Returns ``(start, end)`` inclusive-exclusive, or ``None``.
    """
    if not raw_response or value is None:
        return None

    needle: Optional[str]
    if isinstance(value, str):
        needle = value.strip()
    elif isinstance(value, bool):
        # bool MUST be checked before int because bool is a subclass of int.
        needle = "true" if value else "false"
    elif isinstance(value, (int, float)):
        needle = str(value)
    else:
        # Dict, list, tuple, custom types — no meaningful single region.
        return None

    if not needle:
        return None

    # Exact last match first.
    idx = raw_response.rfind(needle)
    if idx >= 0:
        return (idx, idx + len(needle))

    # Case-insensitive last match.
    lower_haystack = raw_response.lower()
    lower_needle = needle.lower()
    if lower_needle != needle:
        idx = lower_haystack.rfind(lower_needle)
        if idx >= 0:
            return (idx, idx + len(lower_needle))
    else:
        # Needle is already lowercase; search the lowered haystack to catch
        # capitalised occurrences (e.g. value="drive", response has "Drive").
        idx = lower_haystack.rfind(lower_needle)
        if idx >= 0:
            return (idx, idx + len(lower_needle))

    return None


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

    For languages not in *keyword_dict*, falls back to the ``LanguageSpec``
    registry (``src.plugins.languages``) so new languages registered there
    work automatically without editing this file.
    """
    en = keyword_dict.get("en", [])
    if language == "en":
        return en
    local = keyword_dict.get(language)
    if local is None:
        from src.plugins import languages as _langs  # late import avoids circular
        spec = _langs.get(language)
        if spec is not None:
            # Map known dicts to their LanguageSpec attribute
            if keyword_dict is ANSWER_LABELS:
                local = spec.answer_labels
            elif keyword_dict is YES_WORDS:
                local = spec.yes_words
            elif keyword_dict is NO_WORDS:
                local = spec.no_words
            else:
                local = []
        else:
            local = []
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
    from src.plugins import languages as _langs  # late import avoids circular
    merged = dict(WORD_TO_INT["en"])
    if language == "en":
        return merged
    lang_data = WORD_TO_INT.get(language)
    if lang_data is None:
        spec = _langs.get(language)
        lang_data = spec.word_to_int if spec else {}
    merged.update(lang_data)
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


# ---------------------------------------------------------------------------
# Unicode normalization
# ---------------------------------------------------------------------------

def normalize_unicode(text: str) -> str:
    """Normalize curly / smart quotes and apostrophes to ASCII equivalents.

    Models frequently emit U+2018 / U+2019 (curly single quotes) and
    U+201C / U+201D (curly double quotes), which do not match ASCII ``'``
    or ``"`` in hand-written regex patterns.  Also folds U+2032 (prime)
    and U+2033 (double prime), commonly emitted in measurement notation
    (5' / 5"), so unit parsing doesn't have to special-case them.
    Normalizing once at parse entry lets every downstream regex use plain
    ASCII.
    """
    return (
        text
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201C", '"')
        .replace("\u201D", '"')
        .replace("\u2032", "'")
        .replace("\u2033", '"')
    )


# ---------------------------------------------------------------------------
# LaTeX / math-wrapper normalization for label-based extraction
# ---------------------------------------------------------------------------

_LATEX_WRAP_RE = re.compile(
    r"\\(?:text|mathbf|mathrm|mathit|mathsf|mathtt|textbf|textit)\s*\{([^{}]*)\}"
)
# \quad / \qquad / \, / \; / \: / \!  — explicit LaTeX spacing macros.
_LATEX_SPACING_RE = re.compile(r"\\(?:qquad|quad|[,;:!])")


def normalize_for_label_matching(text: str) -> str:
    """Strip LaTeX math-mode wrappers so token-adjacent patterns can match.

    * ``\\text{X}`` → ``X`` (same for ``\\mathbf`` / ``\\mathrm`` / …)
    * ``\\quad`` / ``\\,`` / ``\\;`` etc. → single space
    * ``$$`` / ``$`` delimiters → single space

    Callers that rely on sentinel detection (``cannot determine``,
    ``no solution``) should run sentinel checks on the *raw* text; only
    label-extraction strategies should see the normalized form.
    """
    # Run the wrapper strip until stable so nested wrappers
    # (``\mathbf{\text{X}}``) get fully unwrapped.  Bounded to 3 iterations.
    for _ in range(3):
        prev = text
        text = _LATEX_WRAP_RE.sub(r"\1", text)
        if text == prev:
            break
    text = _LATEX_SPACING_RE.sub(" ", text)
    text = text.replace("$$", " ").replace("$", " ")
    return text


# ---------------------------------------------------------------------------
# Numeric parsing with float-vs-int discipline
# ---------------------------------------------------------------------------

def try_parse_number(
    text: str,
    word_map: Optional[Dict[str, int]] = None,
) -> Optional[Number]:
    """Parse *text* as an ``int`` or ``float``, stripping punctuation/markdown noise.

    Returns an ``int`` for integer literals and a ``float`` for decimals.
    Keeping the two types distinct lets evaluators flag ``non_integer_prediction``
    without silently truncating (``int("22.2")`` coerces to ``22``, which
    would score as correct against an expected value of ``22``).

    Word-number fallback via *word_map* always returns an ``int``.
    Supports negative word forms prefixed with ``-``, ``negative``, ``minus``,
    or the Unicode minus sign ``−`` (U+2212).
    """
    s = text.strip().strip("*_`").rstrip(".,;:!?)}]")
    if re.fullmatch(r"-?\d+", s):
        try:
            return int(s)
        except ValueError:
            return None
    if re.fullmatch(r"-?\d+\.\d+", s):
        try:
            return float(s)
        except ValueError:
            return None
    if word_map is None:
        return None
    low = s.lower()
    if low in word_map:
        return word_map[low]
    stripped = re.sub(r"^(?:-|negative|minus|\u2212)\s+", "", low)
    if stripped != low and stripped in word_map:
        return -word_map[stripped]
    return None


# ---------------------------------------------------------------------------
# Sentinel-keyword detection (first-N / last-M sentences)
# ---------------------------------------------------------------------------

def detect_sentinel_keyword(
    text: str,
    keyword_dict: Dict[str, List[str]],
    lang: str,
    scan_first: int = 2,
    scan_last: int = 3,
    normalize_apostrophes: bool = True,
) -> bool:
    """Return True if any sentinel keyword from *keyword_dict* appears in the
    opening *scan_first* sentences or the closing *scan_last* sentences of *text*.

    Designed for plugin-level "refusal" / "no-solution" / "cannot-determine"
    style sentinels.  The keyword dict is merged across English and *lang*
    via :func:`merge_keywords` so the same call works for every language.

    Set *normalize_apostrophes* to False if callers have already normalized
    U+2019 to U+0027 in both the text and the keyword dict.
    """
    keywords = merge_keywords(keyword_dict, lang)
    if not keywords:
        return False

    def _norm(s: str) -> str:
        s = s.lower()
        if normalize_apostrophes:
            s = s.replace("\u2019", "'")
        return s

    keywords = [_norm(k) for k in keywords]

    # Split the FULL text so we can slice the true opening and the true
    # closing.  ``last_sentences`` would truncate from the end and miss the
    # real opening for long responses.
    parts = re.split(r"(?<=[.!?。！？])\s+", text.strip())
    parts = [p for p in parts if p.strip()]
    if not parts:
        return False
    opening = _norm(" ".join(parts[:scan_first]))
    closing = _norm(" ".join(parts[-scan_last:]))
    for kw in keywords:
        if kw in opening or kw in closing:
            return True
    return False


# ---------------------------------------------------------------------------
# Contextual-marker detection around a match position
# ---------------------------------------------------------------------------

def has_contextual_marker(
    text: str,
    position: int,
    pattern_dicts: Sequence[Dict[str, re.Pattern]],
    lang: str,
    pre_window: int = 120,
    post_window: int = 80,
    positional: bool = False,
) -> bool:
    """Return True if any pattern from *pattern_dicts* matches near *position*.

    Used for conditional / dismissive / option-listing context detection
    around a keyword hit (e.g. "walk" in carwash, where "only walk if..."
    should NOT count as a walk recommendation).

    *pattern_dicts* is a sequence of ``{lang_code: compiled_regex}`` dicts;
    English patterns are always checked, and the target language's patterns
    are additionally checked when ``lang != "en"``.

    When *positional* is False (default), any match anywhere in the window
    counts.  When True, the match span must contain *position* itself —
    this is the stricter check used for option-listing / comparison
    patterns, so a genuine recommendation that merely sits within 120 chars
    of an earlier "X or Y" listing is not filtered.
    """
    window_start = max(0, position - pre_window)
    window_end = min(len(text), position + post_window)
    window = text[window_start:window_end]
    offset = position - window_start
    codes = ["en"] if lang == "en" else ["en", lang]

    for code in codes:
        for pattern_dict in pattern_dicts:
            pat = pattern_dict.get(code)
            if pat is None:
                continue
            if positional:
                for m in pat.finditer(window):
                    if m.start() <= offset < m.end():
                        return True
            else:
                if pat.search(window):
                    return True
    return False
