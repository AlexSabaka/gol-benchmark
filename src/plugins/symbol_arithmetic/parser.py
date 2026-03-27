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
from src.plugins.parse_utils import re_search_last


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
                parse_strategy="failed", error="Empty response",
            )

        symbols: List[str] = task_params.get("symbols", [])
        response = str(response).strip()

        # Strategy 1: undefined detection (checked first — special answer)
        result = self._strategy_undefined(response)
        if result is not None:
            return result

        # Strategies 2–6: extract a symbol from the set
        strategies = [
            ("boxed_symbol", self._strategy_boxed),
            ("labelled_answer", self._strategy_labelled),
            ("equals_pattern", self._strategy_equals),
            ("bold_symbol", self._strategy_bold),
            ("last_symbol", self._strategy_last_symbol),
        ]

        for name, fn in strategies:
            val = fn(response, symbols)
            if val is not None:
                return ParsedAnswer(
                    value=val, raw_response=response,
                    parse_strategy=name,
                )

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="failed",
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
    def _strategy_labelled(response: str, symbols: List[str]) -> Optional[str]:
        """Look for 'answer:', 'result:', 'final answer:', 'therefore' + symbol (end-first)."""
        sym_alt = "|".join(re.escape(s) for s in symbols)
        pattern = rf"(?:final\s+answer|answer|result|therefore)\s*[:=]?\s*({sym_alt})"
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
