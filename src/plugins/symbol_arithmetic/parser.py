"""
Symbol Arithmetic Response Parser

Multi-strategy, end-first parser for extracting symbol answers (or
"UNDEFINED") from model responses.  All strategies filter candidates against
the known symbol set passed via ``task_params['symbols']``.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    build_answer_label_re,
    get_language,
    merge_keywords,
    normalize_unicode,
    re_search_last,
    strip_verification_tail,
)


# Symbol-arithmetic-specific label terms — `therefore` is the characteristic
# intro for a concluding symbol in a derivation ("…therefore the answer is ⊕").
_EXTRA_LABELS: Dict[str, List[str]] = {
    "en": ["therefore"],
    "es": ["por lo tanto"],
    "fr": ["donc"],
    "de": ["daher", "also"],
    "zh": ["因此", "所以"],
    "ua": ["отже", "тому"],
}


def _build_label_alt(lang: str) -> str:
    base = build_answer_label_re(lang)
    extra = merge_keywords(_EXTRA_LABELS, lang)
    extra_alt = "|".join(re.escape(e) for e in extra) if extra else ""
    if base and extra_alt:
        return f"{base}|{extra_alt}"
    return base or extra_alt


_UNDEFINED_KEYWORDS = [
    "undefined", "not defined", "no entry", "missing",
    "cannot be determined", "does not exist", "incomplete table",
    "not in the table", "no result", "is not defined",
]


class SymbolArithmeticParser(ResponseParser):
    """6-strategy end-first parser for symbol arithmetic responses."""

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        if not response:
            return ParsedAnswer(
                value=None, raw_response=response or "",
                parse_strategy="empty", error="Empty response",
            )

        symbols: List[str] = task_params.get("symbols", [])
        response = normalize_unicode(str(response).strip())
        lang = get_language(task_params)

        # Strategy 1: undefined detection (checked first — special answer).
        # Run against a verification-stripped copy so "Let me verify: the
        # table shows no result for this pair" doesn't re-trigger "no result"
        # after a genuine answer.
        response_clean = strip_verification_tail(response)
        result = self._strategy_undefined(response_clean)
        if result is not None:
            return result

        # Strategies 2–6: extract a symbol from the set.
        # Boxed / bold / labelled keep the raw response because those
        # formats carry high signal regardless of the verification section;
        # equals_pattern and last_symbol scan freely for a symbol token, so
        # they benefit from stripping the verification re-computation tail.
        # The `_strategy_labelled` takes a lang arg so it can build the
        # multilingual answer-label alternation once per call.
        strategies = [
            ("boxed_symbol", lambda t, s: self._strategy_boxed(t, s), response),
            ("labelled_answer", lambda t, s: self._strategy_labelled(t, s, lang), response),
            ("equals_pattern", lambda t, s: self._strategy_equals(t, s), response_clean),
            ("bold_symbol", lambda t, s: self._strategy_bold(t, s), response),
            ("last_symbol", lambda t, s: self._strategy_last_symbol(t, s), response_clean),
        ]

        for name, fn, strategy_text in strategies:
            val = fn(strategy_text, symbols)
            if val is not None:
                return ParsedAnswer(
                    value=val, raw_response=response,
                    parse_strategy=name,
                )

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="fallback",
            error="All parsing strategies failed",
        )

    def get_strategies(self) -> List[str]:
        return [
            "undefined_detection",
            "boxed_symbol",
            "labelled_answer",
            "equals_pattern",
            "bold_symbol",
            "last_symbol",
        ]

    # ── strategy implementations ────────────────────────────────────

    @staticmethod
    def _strategy_undefined(response: str) -> Optional[ParsedAnswer]:
        """Detect if the model flagged the result as undefined / missing."""
        lower = response.lower()
        for kw in _UNDEFINED_KEYWORDS:
            if kw in lower:
                return ParsedAnswer(
                    value="UNDEFINED", raw_response=response,
                    parse_strategy="undefined_detection",
                )
        return None

    @staticmethod
    def _strategy_boxed(response: str, symbols: List[str]) -> Optional[str]:
        r"""Extract from ``\boxed{X}`` (end-first)."""
        pattern = r"\\boxed\{([^}]+)\}"
        m = re_search_last(pattern, response)
        if m:
            candidate = m.group(1).strip()
            if candidate in symbols:
                return candidate
        return None

    @staticmethod
    def _strategy_labelled(response: str, symbols: List[str], lang: str = "en") -> Optional[str]:
        """Look for '<label>: <symbol>' (end-first) — multilingual labels."""
        sym_alt = "|".join(re.escape(s) for s in symbols)
        label_alt = _build_label_alt(lang)
        pattern = rf"(?:{label_alt})\s*[:=]?\s*({sym_alt})"
        m = re_search_last(pattern, response, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _strategy_equals(response: str, symbols: List[str]) -> Optional[str]:
        """Match ``= X`` where X is a valid symbol (end-first)."""
        sym_alt = "|".join(re.escape(s) for s in symbols)
        pattern = rf"=\s*({sym_alt})(?:\s|$|[.,;)!?])"
        m = re_search_last(pattern, response)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _strategy_bold(response: str, symbols: List[str]) -> Optional[str]:
        """Match ``**X**`` markdown bold (end-first)."""
        sym_alt = "|".join(re.escape(s) for s in symbols)
        pattern = rf"\*\*({sym_alt})\*\*"
        m = re_search_last(pattern, response)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _strategy_last_symbol(response: str, symbols: List[str]) -> Optional[str]:
        """Return the last occurrence of any symbol-set member."""
        # Sort symbols longest-first so multi-char tokens match greedily
        sorted_syms = sorted(symbols, key=len, reverse=True)
        sym_alt = "|".join(re.escape(s) for s in sorted_syms)
        pattern = rf"({sym_alt})"
        m = re_search_last(pattern, response)
        if m:
            return m.group(1)
        return None
