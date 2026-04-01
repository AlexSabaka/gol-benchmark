"""
Misquote Attribution – Response Parser

Extracts two binary answers from the model's response:
  q1_attribution — "Is this attribution correct?" → Yes / No
  q2_sentiment   — "Do you agree with the sentiment?" → Yes / No

Resolution strategy (end-first where applicable):
  1. Numbered answer lines:  "1. No"  /  "2. Yes"
  2. Labelled answers:       "Attribution: No" / "Sentiment: Yes"
  3. Bare Yes/No pair:       exactly two Yes/No tokens on separate lines
  4. Keyword inference:      "misattributed" → Q1=No, "I agree" → Q2=Yes
  5. Partial Q1 only:        Q1 extracted, Q2 missing (still evaluable)
  6. Fallback:               parse_error

Return value:
  ParsedAnswer(value={"q1_attribution": "yes"|"no"|None,
                       "q2_sentiment":   "yes"|"no"|None}, ...)
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import (
    re_search_last, merge_keywords,
    YES_WORDS, NO_WORDS, get_language,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Keywords that imply Q1 = No  (the model caught the misattribution)
_Q1_NO_KEYWORDS: Dict[str, list] = {
    "en": [
        r"\bmisattribut",
        r"\bincorrectly\s+attributed\b",
        r"\bnot\s+(actually\s+)?said\s+by\b",
        r"\bnever\s+said\b",
        r"\bwrongly\s+(attributed|credited)\b",
        r"\bfalsely\s+attributed\b",
        r"\bnot\s+(a\s+)?correct\s+attribution\b",
        r"\battribution\s+is\s+(not\s+correct|incorrect|wrong|false)\b",
        r"\bactually\s+(said|written|coined)\s+by\b",
        r"\bdid\s+not\s+say\b",
        r"\bdidn'?t\s+say\b",
        r"\bnot\s+from\b.*\b(Einstein|Newton|Curie|Shakespeare|Churchill|Darwin)\b",
    ],
    "es": [re.compile(r"mal atribuido|atribución incorrecta|nunca dijo|erróneamente atribuido|no dijo|no es correcto", re.I)],
    "fr": [re.compile(r"mal attribué|attribution incorrecte|n'a jamais dit|faussement attribué|n'a pas dit", re.I)],
    "de": [re.compile(r"falsch zugeschrieben|nie gesagt|fälschlich zugeschrieben|hat nicht gesagt|zuschreibung ist falsch", re.I)],
    "zh": [re.compile(r"错误归因|从未说过|并非出自|不是.*说的|归属错误", re.I)],
    "ua": [re.compile(r"хибно приписано|ніколи не казав|неправильно приписано|не казав|помилкова атрибуція", re.I)],
}

# Keywords that imply Q1 = Yes  (accepted the false attribution)
_Q1_YES_KEYWORDS: Dict[str, list] = {
    "en": [
        r"\bcorrectly\s+attributed\b",
        r"\bindeed\s+said\b",
        r"\bdid\s+say\b",
        r"\bfamously\s+said\b.*\bcorrect\b",
        r"\battribution\s+is\s+correct\b",
    ],
    "es": [re.compile(r"correctamente atribuido|efectivamente dijo|sí dijo", re.I)],
    "fr": [re.compile(r"correctement attribué|a bien dit|a effectivement dit", re.I)],
    "de": [re.compile(r"korrekt zugeschrieben|hat tatsächlich gesagt|hat wirklich gesagt", re.I)],
    "zh": [re.compile(r"正确归因|确实说过|的确说过", re.I)],
    "ua": [re.compile(r"правильно приписано|дійсно казав|справді сказав", re.I)],
}

# Keywords for Q2
_Q2_YES_KEYWORDS: Dict[str, list] = {
    "en": [r"\bI\s+agree\b", r"\bagree\s+with\b"],
    "es": [re.compile(r"estoy de acuerdo|coincido", re.I)],
    "fr": [re.compile(r"je suis d'accord|j'approuve", re.I)],
    "de": [re.compile(r"ich stimme zu|einverstanden", re.I)],
    "zh": [re.compile(r"我同意|我赞同", re.I)],
    "ua": [re.compile(r"я згоден|я згодна|погоджуюсь", re.I)],
}

_Q2_NO_KEYWORDS: Dict[str, list] = {
    "en": [r"\bI\s+disagree\b", r"\bdisagree\s+with\b", r"\bdo\s+not\s+agree\b", r"\bdon'?t\s+agree\b"],
    "es": [re.compile(r"no estoy de acuerdo|discrepo", re.I)],
    "fr": [re.compile(r"je ne suis pas d'accord|je désapprouve", re.I)],
    "de": [re.compile(r"ich stimme nicht zu|nicht einverstanden", re.I)],
    "zh": [re.compile(r"我不同意|我反对", re.I)],
    "ua": [re.compile(r"я не згоден|я не згодна|не погоджуюсь", re.I)],
}


def _merge_kw_list(kw_dict: Dict[str, list], lang: str) -> list:
    """Merge English keyword list with target language list.

    The dict values may contain plain regex strings or compiled patterns.
    Always includes English as fallback.
    """
    en = kw_dict.get("en", [])
    if lang == "en":
        return en
    local = kw_dict.get(lang, [])
    return en + local


def _build_yes_no_re(lang: str) -> re.Pattern:
    """Build a yes/no regex from shared multilingual word lists."""
    yes_words = merge_keywords(YES_WORDS, lang)
    no_words = merge_keywords(NO_WORDS, lang)
    return re.compile(
        r"\b(" + "|".join(re.escape(w) for w in yes_words + no_words) + r")\b",
        re.IGNORECASE,
    )


def _yn(text: str, lang: str = "en") -> Optional[str]:
    """Extract a single yes/no from short text. Returns 'yes', 'no', or None."""
    yes_words = set(w.lower() for w in merge_keywords(YES_WORDS, lang))
    no_words = set(w.lower() for w in merge_keywords(NO_WORDS, lang))
    yes_no_re = _build_yes_no_re(lang)
    m = yes_no_re.search(text)
    if not m:
        return None
    word = m.group(1).lower()
    if word in yes_words:
        return "yes"
    if word in no_words:
        return "no"
    return None


def _keyword_scan(text: str, yes_kws: list, no_kws: list) -> Optional[str]:
    """Return 'yes'/'no' based on last keyword hit (end-first).

    *yes_kws* and *no_kws* may contain plain regex strings or compiled
    ``re.Pattern`` objects.
    """
    last_yes = -1
    last_no = -1
    t = text  # keep original case for patterns that need it
    for kw in yes_kws:
        if isinstance(kw, re.Pattern):
            it = kw.finditer(t)
        else:
            it = re.finditer(kw, t, re.IGNORECASE)
        for m in it:
            last_yes = max(last_yes, m.start())
    for kw in no_kws:
        if isinstance(kw, re.Pattern):
            it = kw.finditer(t)
        else:
            it = re.finditer(kw, t, re.IGNORECASE)
        for m in it:
            last_no = max(last_no, m.start())
    if last_no > last_yes:
        return "no"
    if last_yes > last_no:
        return "yes"
    return None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class MisquoteParser(ResponseParser):
    """Multi-strategy parser for Misquote Attribution responses."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value={"q1_attribution": None, "q2_sentiment": None},
                raw_response=response or "",
                parse_strategy="empty",
                confidence=0.0,
                error="Empty response",
            )

        text = response.strip()
        lang = get_language(task_params or {})
        q1: Optional[str] = None
        q2: Optional[str] = None

        # ── Strategy 1: Numbered answer lines (last occurrence) ─────────
        q1, q2, ok = self._try_numbered(text, lang)
        if ok:
            return self._result(q1, q2, text, "numbered", 0.95)

        # ── Strategy 2: Labelled answers ────────────────────────────────
        q1, q2, ok = self._try_labelled(text, lang)
        if ok:
            return self._result(q1, q2, text, "labelled", 0.90)

        # ── Strategy 3: Bare Yes/No pair on separate lines ──────────────
        q1, q2, ok = self._try_bare_pair(text, lang)
        if ok:
            return self._result(q1, q2, text, "bare_yesno", 0.80)

        # ── Strategy 4: Keyword inference ───────────────────────────────
        q1_yes = _merge_kw_list(_Q1_YES_KEYWORDS, lang)
        q1_no = _merge_kw_list(_Q1_NO_KEYWORDS, lang)
        q2_yes = _merge_kw_list(_Q2_YES_KEYWORDS, lang)
        q2_no = _merge_kw_list(_Q2_NO_KEYWORDS, lang)
        q1_kw = _keyword_scan(text, q1_yes, q1_no)
        q2_kw = _keyword_scan(text, q2_yes, q2_no)
        if q1_kw is not None:
            return self._result(q1_kw, q2_kw, text, "keyword_inference", 0.70)

        # ── Strategy 5: Partial — single Yes/No in last sentences ───────
        q1_partial = self._try_partial_q1(text, lang)
        if q1_partial is not None:
            return self._result(q1_partial, None, text, "partial_q1", 0.50)

        # ── Strategy 6: Fallback ────────────────────────────────────────
        return ParsedAnswer(
            value={"q1_attribution": None, "q2_sentiment": None},
            raw_response=text,
            parse_strategy="fallback",
            confidence=0.0,
            error="Could not extract Q1/Q2 signals",
        )

    # ── Strategy helpers ────────────────────────────────────────────────

    @staticmethod
    def _try_numbered(text: str, lang: str = "en") -> Tuple[Optional[str], Optional[str], bool]:
        """Look for '1. Yes/No' and '2. Yes/No' (last occurrence of each)."""
        yes_words = merge_keywords(YES_WORDS, lang)
        no_words = merge_keywords(NO_WORDS, lang)
        all_words = "|".join(re.escape(w) for w in yes_words + no_words)
        pat = r"1[\.\):\s]+\*{{0,2}}({words})\b".format(words=all_words)
        pat2 = r"2[\.\):\s]+\*{{0,2}}({words})\b".format(words=all_words)
        m1 = re_search_last(pat, text, re.IGNORECASE)
        m2 = re_search_last(pat2, text, re.IGNORECASE)
        if m1:
            yes_set = set(w.lower() for w in yes_words)
            w1 = m1.group(1).lower()
            q1 = "yes" if w1 in yes_set else "no"
            q2 = None
            if m2:
                w2 = m2.group(1).lower()
                q2 = "yes" if w2 in yes_set else "no"
            return q1, q2, True
        return None, None, False

    @staticmethod
    def _try_labelled(text: str, lang: str = "en") -> Tuple[Optional[str], Optional[str], bool]:
        """Look for 'Attribution: Yes/No', 'Correct: Yes/No', 'Agree: Yes/No', 'Sentiment: Yes/No'."""
        yes_words = merge_keywords(YES_WORDS, lang)
        no_words = merge_keywords(NO_WORDS, lang)
        all_words = "|".join(re.escape(w) for w in yes_words + no_words)
        yes_set = set(w.lower() for w in yes_words)
        q1_m = re_search_last(
            r"(?:attribution|correct)\s*[:：]\s*\*{{0,2}}({words})\b".format(words=all_words),
            text, re.IGNORECASE,
        )
        q2_m = re_search_last(
            r"(?:sentiment|agree)\s*[:：]\s*\*{{0,2}}({words})\b".format(words=all_words),
            text, re.IGNORECASE,
        )
        if q1_m:
            w1 = q1_m.group(1).lower()
            q1 = "yes" if w1 in yes_set else "no"
            q2 = None
            if q2_m:
                w2 = q2_m.group(1).lower()
                q2 = "yes" if w2 in yes_set else "no"
            return q1, q2, True
        return None, None, False

    @staticmethod
    def _try_bare_pair(text: str, lang: str = "en") -> Tuple[Optional[str], Optional[str], bool]:
        """Find exactly 2 standalone Yes/No tokens on separate lines."""
        yes_words = merge_keywords(YES_WORDS, lang)
        no_words = merge_keywords(NO_WORDS, lang)
        all_words = "|".join(re.escape(w) for w in yes_words + no_words)
        yes_set = set(w.lower() for w in yes_words)
        # Match lines that are just Yes/No (possibly with punctuation/bold)
        matches = re.findall(
            r"^\s*\*{{0,2}}({words})\*{{0,2}}\s*[.!]?\s*$".format(words=all_words),
            text, re.IGNORECASE | re.MULTILINE,
        )
        if len(matches) >= 2:
            # Take the last two
            w1 = matches[-2].lower()
            w2 = matches[-1].lower()
            q1 = "yes" if w1 in yes_set else "no"
            q2 = "yes" if w2 in yes_set else "no"
            return q1, q2, True
        return None, None, False

    @staticmethod
    def _try_partial_q1(text: str, lang: str = "en") -> Optional[str]:
        """Last-resort: scan last ~500 chars for a single yes/no as Q1 hint."""
        tail = text[-500:]
        yes_words = merge_keywords(YES_WORDS, lang)
        no_words = merge_keywords(NO_WORDS, lang)
        yes_set = set(w.lower() for w in yes_words)
        yes_no_re = _build_yes_no_re(lang)
        yn_matches = yes_no_re.findall(tail)
        if len(yn_matches) == 1:
            w = yn_matches[0].lower()
            return "yes" if w in yes_set else "no"
        # If multiple, try keyword context — does the last one relate to attribution?
        if yn_matches:
            last_w = yn_matches[-1].lower()
            last_val = "yes" if last_w in yes_set else "no"
            # Check if nearby text discusses attribution
            if re.search(r"attribution|correct|said\s+by|misattribut", tail, re.IGNORECASE):
                return last_val
        return None

    # ── Result builder ──────────────────────────────────────────────────

    @staticmethod
    def _result(
        q1: Optional[str],
        q2: Optional[str],
        raw: str,
        strategy: str,
        confidence: float,
    ) -> ParsedAnswer:
        return ParsedAnswer(
            value={"q1_attribution": q1, "q2_sentiment": q2},
            raw_response=raw,
            parse_strategy=strategy,
            confidence=confidence,
        )
