"""
Measure Comparison – Response Parser

Extracts the model's chosen measurement from a free-form response.

Four answer categories:
  1. Normal     — a value+unit that matches one of the two options
  2. Equal      — keywords like "equal", "same", "equivalent"
  3. Incomparable — keywords like "cannot compare", "incomparable"
  4. Position   — "first"/"second" fallback

Strategy pipeline (tried in order, highest confidence first):
  1. boxed              \\boxed{...}                          0.95
  2. bold               **...**                               0.90
  3. keyword_equal      detects "equal"/"same" etc.           0.90
  4. keyword_incomparable  detects "cannot compare" etc.      0.90
  5. label_line         "Answer: ..."                         0.88
  6. value_unit_match   extract value+unit, match to options  0.85
  7. position_match     "first"/"second"                      0.75
  8. last_value_unit    last value+unit found                 0.65
  9. fallback           parse error                           0.10
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import re_search_last

# ---------------------------------------------------------------------------
# Unit symbol aliases (normalised form → set of of display variants)
# ---------------------------------------------------------------------------

_SYMBOL_ALIASES: Dict[str, List[str]] = {
    "mm": ["mm", "millimeter", "millimeters", "millimetre", "millimetres"],
    "cm": ["cm", "centimeter", "centimeters", "centimetre", "centimetres"],
    "m":  ["m", "meter", "meters", "metre", "metres"],
    "km": ["km", "kilometer", "kilometers", "kilometre", "kilometres"],
    "in": ["in", "inch", "inches", '"'],
    "ft": ["ft", "foot", "feet", "'"],
    "yd": ["yd", "yard", "yards"],
    "mi": ["mi", "mile", "miles"],
    "mg": ["mg", "milligram", "milligrams"],
    "g":  ["g", "gram", "grams"],
    "kg": ["kg", "kilogram", "kilograms"],
    "oz": ["oz", "ounce", "ounces"],
    "lb": ["lb", "lbs", "pound", "pounds"],
    "°C": ["°c", "°C", "celsius", "c", "degrees celsius", "deg c"],
    "°F": ["°f", "°F", "fahrenheit", "f", "degrees fahrenheit", "deg f"],
    "K":  ["k", "kelvin"],
    "mL": ["ml", "mL", "milliliter", "milliliters", "millilitre", "millilitres"],
    "L":  ["l", "L", "liter", "liters", "litre", "litres"],
    "cup": ["cup", "cups"],
    "fl oz": ["fl oz", "fluid ounce", "fluid ounces", "fl. oz", "fl.oz"],
    "pt": ["pt", "pint", "pints"],
    "gal": ["gal", "gallon", "gallons"],
    "m/s": ["m/s", "meters per second", "metres per second"],
    "km/h": ["km/h", "kmh", "kph", "kilometers per hour", "kilometres per hour"],
    "mph": ["mph", "miles per hour"],
    "s":  ["s", "sec", "second", "seconds"],
    "min": ["min", "minute", "minutes"],
    "h":  ["h", "hr", "hour", "hours"],
}

# Build reverse lookup: any alias → canonical symbol
_ALIAS_TO_CANON: Dict[str, str] = {}
for _canon, _aliases in _SYMBOL_ALIASES.items():
    for _a in _aliases:
        _ALIAS_TO_CANON[_a.lower()] = _canon

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Value pattern: integer, decimal, or fraction
_VALUE_RE = r"(?:-?\d+(?:\.\d+)?(?:/\d+)?)"

# Value + optional space + unit (capture groups: value, unit-text)
_VALUE_UNIT_RE = re.compile(
    r"(" + _VALUE_RE + r")"     # group 1: numeric value
    r"\s*"
    r"(°?[A-Za-z/][A-Za-z/.\s]{0,20})",  # group 2: unit text
    re.IGNORECASE,
)

# Equal keywords
_EQUAL_KEYWORDS = re.compile(
    r"(?:\b(?:equal|same|equivalent|identical|both.{0,15}(?:equal|same)|no\s+difference|"
    r"igual|iguales|même|mêmes|gleich|рівні|однакові|égal|égales|égaux)\b"
    r"|相等|相同)",
    re.IGNORECASE,
)

# Incomparable keywords
_INCOMPARABLE_KEYWORDS = re.compile(
    r"(?:cannot\s+(?:be\s+)?compare|can'?t\s+(?:be\s+)?compare|incomparable|"
    r"not\s+comparable|different\s+(?:physical\s+)?(?:dimensions?|categories|units?|quantities)|"
    r"impossible\s+to\s+compare|apples?\s+and\s+oranges?|"
    r"no\s+(?:se\s+)?puede[n]?\s+comparar|incomparable|"
    r"ne\s+(?:peut|peuvent)\s+pas\s+être\s+comparé|incomparable|"
    r"nicht\s+vergleichbar|"
    r"无法比较|不能比较|不可比较|"
    r"непорівнянні|неможливо\s+порівняти|"
    r"incomparables?)",
    re.IGNORECASE,
)

# Position keywords
_POSITION_RE = re.compile(
    r"\b(first|second|1st|2nd|option\s*[12ab]|choice\s*[12ab]|"
    r"primer[ao]|segund[ao]|premier|deuxième|erst[eé]|zweit[eé]|"
    r"第一|第二|перш[аеий]|друг[аеий])\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _normalise_unit(text: str) -> Optional[str]:
    """Return the canonical unit symbol for *text*, or None."""
    text = text.strip().rstrip(".,;:!?)")
    low = text.lower()
    if low in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[low]
    # Try progressively shorter prefixes (min 2 chars to avoid
    # single-letter false positives like "k"→kelvin for "kilometer")
    for length in range(len(low), 1, -1):
        prefix = low[:length]
        if prefix in _ALIAS_TO_CANON:
            return _ALIAS_TO_CANON[prefix]
    return None


def _parse_value_str(text: str) -> Optional[float]:
    """Parse a numeric string (int, float, or fraction) to float."""
    text = text.strip().rstrip(".,;:!?)")
    if "/" in text:
        parts = text.split("/")
        if len(parts) == 2:
            try:
                return float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                return None
    try:
        return float(text)
    except ValueError:
        return None


def _extract_value_units(text: str) -> List[Tuple[str, str, float, str]]:
    """Extract all (value_str, unit_canon, value_float, raw_match) tuples."""
    results = []
    for m in _VALUE_UNIT_RE.finditer(text):
        val_str = m.group(1)
        unit_text = m.group(2).strip()
        val_f = _parse_value_str(val_str)
        unit_canon = _normalise_unit(unit_text)
        if val_f is not None and unit_canon is not None:
            raw = m.group(0).strip()
            results.append((val_str, unit_canon, val_f, raw))
    return results


def _build_option_key(val_str: str, unit_symbol: str) -> str:
    """Canonical key for an option: strip spaces, lowercase."""
    return f"{val_str} {unit_symbol}".strip().lower()


def _match_to_option(
    extracted_val: str,
    extracted_unit: str,
    task_params: Dict[str, Any],
) -> Optional[str]:
    """Check if an extracted value+unit matches option 1 or 2.

    Returns "first", "second", or None.
    """
    opt1_sym = task_params.get("unit1_symbol", "")
    opt2_sym = task_params.get("unit2_symbol", "")
    v1 = task_params.get("value1", "")
    v2 = task_params.get("value2", "")

    # Normalise the extracted unit
    ext_unit_norm = extracted_unit  # already canonical from _normalise_unit

    # Compare against option 1
    if ext_unit_norm == opt1_sym or ext_unit_norm == _normalise_unit(opt1_sym):
        if _values_match(extracted_val, v1):
            return "first"

    # Compare against option 2
    if ext_unit_norm == opt2_sym or ext_unit_norm == _normalise_unit(opt2_sym):
        if _values_match(extracted_val, v2):
            return "second"

    return None


def _values_match(a: str, b: str) -> bool:
    """Check if two value strings represent the same number."""
    fa = _parse_value_str(a)
    fb = _parse_value_str(b)
    if fa is not None and fb is not None:
        return abs(fa - fb) < 1e-9
    return a.strip() == b.strip()


def _position_to_answer(pos: str, task_params: Dict[str, Any]) -> str:
    """Convert a position label to the expected answer string."""
    if pos == "first":
        sym = task_params.get("unit1_symbol", "")
        return f"{task_params.get('value1', '')} {sym}".strip()
    elif pos == "second":
        sym = task_params.get("unit2_symbol", "")
        return f"{task_params.get('value2', '')} {sym}".strip()
    return pos  # "equal" / "incomparable"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class MeasureComparisonParser(ResponseParser):
    """Multi-strategy parser for measurement comparison responses."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy="empty",
                confidence=0.0,
                error="Empty response",
            )

        text = response.strip()
        tp = task_params or {}

        # Route decimal comparison type to a specialised parser (bare numbers)
        if tp.get("comparison_type") == "decimal":
            return self._parse_decimal(text, tp)

        # --- Strategy 1: LaTeX boxed (last match) ---
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            inner = boxed.group(1).strip()
            result = self._try_resolve(inner, tp)
            if result is not None:
                return ParsedAnswer(
                    value=result, raw_response=text,
                    parse_strategy="boxed", confidence=0.95,
                )

        # --- Strategy 2: Bold (last match) ---
        bold = re_search_last(r"\*\*([^*]{1,40})\*\*", text)
        if bold:
            inner = bold.group(1).strip()
            result = self._try_resolve(inner, tp)
            if result is not None:
                return ParsedAnswer(
                    value=result, raw_response=text,
                    parse_strategy="bold", confidence=0.90,
                )

        # --- Strategy 3: Equal keywords ---
        if _EQUAL_KEYWORDS.search(text):
            # Only count as "equal" if the model seems conclusive
            # (avoid matching "they are not equal" / "they are definitely not equal")
            negated = re.search(r"\b(?:not|no|n't|aren'?t|isn'?t)\b.{0,30}" + _EQUAL_KEYWORDS.pattern, text, re.IGNORECASE)
            if not negated:
                return ParsedAnswer(
                    value="equal", raw_response=text,
                    parse_strategy="keyword_equal", confidence=0.90,
                )

        # --- Strategy 4: Incomparable keywords ---
        if _INCOMPARABLE_KEYWORDS.search(text):
            negated = re.search(r"\b(?:not|no|n't)\b.{0,30}" + _INCOMPARABLE_KEYWORDS.pattern, text, re.IGNORECASE)
            if not negated:
                return ParsedAnswer(
                    value="incomparable", raw_response=text,
                    parse_strategy="keyword_incomparable", confidence=0.90,
                )

        # --- Strategy 5: Label line (last match) ---
        label = re_search_last(
            r"(?:answer|result|the\s+(?:answer|result)\s+is)\s*[:：]?\s*(.+?)(?:\.|$)",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if label:
            inner = label.group(1).strip()
            result = self._try_resolve(inner, tp)
            if result is not None:
                return ParsedAnswer(
                    value=result, raw_response=text,
                    parse_strategy="label_line", confidence=0.88,
                )

        # --- Strategy 6: Value+unit match against known options ---
        # NOTE: Do NOT reverse here. Both options are typically mentioned in
        # the response (e.g. "876 mg is heavier than 211 mg"). The first
        # match that corresponds to a known option is the answer being stated.
        vus = _extract_value_units(text)
        for val_str, unit_canon, val_f, raw_match in vus:
            pos = _match_to_option(val_str, unit_canon, tp)
            if pos is not None:
                answer = _position_to_answer(pos, tp)
                return ParsedAnswer(
                    value=answer, raw_response=text,
                    parse_strategy="value_unit_match", confidence=0.85,
                )

        # --- Strategy 7: Position keywords (last match) ---
        pos_m = re_search_last(_POSITION_RE, text)
        if pos_m:
            pos_word = pos_m.group(1).lower()
            pos = self._resolve_position(pos_word)
            if pos is not None:
                answer = _position_to_answer(pos, tp)
                return ParsedAnswer(
                    value=answer, raw_response=text,
                    parse_strategy="position_match", confidence=0.75,
                )

        # --- Strategy 8: Last value+unit found ---
        if vus:
            last_val, last_unit, _, raw = vus[-1]
            answer = f"{last_val} {last_unit}"
            return ParsedAnswer(
                value=answer, raw_response=text,
                parse_strategy="last_value_unit", confidence=0.65,
            )

        # --- Fallback ---
        return ParsedAnswer(
            value=None, raw_response=text,
            parse_strategy="fallback", confidence=0.10,
            error="Could not extract a measurement answer from response",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_resolve(self, inner: str, tp: Dict[str, Any]) -> Optional[str]:
        """Try to resolve a short string as an answer.

        Returns: answer string ("equal", "incomparable", "V unit", position answer)
                 or None if unresolvable.
        """
        low = inner.lower().strip()

        # Check equal / incomparable keywords
        if _EQUAL_KEYWORDS.search(inner):
            return "equal"
        if _INCOMPARABLE_KEYWORDS.search(inner):
            return "incomparable"

        # Check value+unit
        vus = _extract_value_units(inner)
        for val_str, unit_canon, val_f, raw in vus:
            pos = _match_to_option(val_str, unit_canon, tp)
            if pos is not None:
                return _position_to_answer(pos, tp)

        # Check position words
        pos = self._resolve_position(low)
        if pos is not None:
            return _position_to_answer(pos, tp)

        # Direct string match against expected options
        opt1 = _build_option_key(tp.get("value1", ""), tp.get("unit1_symbol", ""))
        opt2 = _build_option_key(tp.get("value2", ""), tp.get("unit2_symbol", ""))
        if low == opt1 or low.replace(" ", "") == opt1.replace(" ", ""):
            return _position_to_answer("first", tp)
        if low == opt2 or low.replace(" ", "") == opt2.replace(" ", ""):
            return _position_to_answer("second", tp)

        return None

    @staticmethod
    def _resolve_position(word: str) -> Optional[str]:
        """Map a position keyword to 'first' or 'second'."""
        first_words = {
            "first", "1st", "option 1", "option a", "choice 1", "choice a",
            "primero", "primera", "premier", "première", "erste", "erster",
            "第一", "перший", "перша", "першій", "першая",
        }
        second_words = {
            "second", "2nd", "option 2", "option b", "choice 2", "choice b",
            "segundo", "segunda", "deuxième", "zweite", "zweiter",
            "第二", "другий", "друга", "другій",
        }
        low = word.strip().lower()
        if low in first_words:
            return "first"
        if low in second_words:
            return "second"
        return None

    # ------------------------------------------------------------------
    # Decimal-framing parser (bare numbers, no units)
    # ------------------------------------------------------------------

    def _parse_decimal(self, text: str, tp: Dict[str, Any]) -> ParsedAnswer:
        """Parse a decimal-framing response.  Expected answer is a bare number."""
        v1 = tp.get("value1", "")
        v2 = tp.get("value2", "")

        # Strategy 1: LaTeX boxed (last match)
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            inner = boxed.group(1).strip()
            match = self._match_decimal_value(inner, v1, v2)
            if match:
                return ParsedAnswer(
                    value=match, raw_response=text,
                    parse_strategy="decimal_boxed", confidence=0.95,
                )

        # Strategy 2: Bold (last match)
        bold = re_search_last(r"\*\*([^*]{1,40})\*\*", text)
        if bold:
            inner = bold.group(1).strip()
            match = self._match_decimal_value(inner, v1, v2)
            if match:
                return ParsedAnswer(
                    value=match, raw_response=text,
                    parse_strategy="decimal_bold", confidence=0.90,
                )

        # Strategy 3: Label line (last match)
        label = re_search_last(
            r"(?:answer|result|the\s+(?:answer|result)\s+is)\s*[:：]?\s*(.+?)(?:\.|$)",
            text, re.IGNORECASE | re.MULTILINE,
        )
        if label:
            inner = label.group(1).strip()
            match = self._match_decimal_value(inner, v1, v2)
            if match:
                return ParsedAnswer(
                    value=match, raw_response=text,
                    parse_strategy="decimal_label", confidence=0.88,
                )

        # Strategy 4: Scan for bare numbers matching v1 or v2 (end-first)
        # Build a pattern that matches either value as a standalone number
        v1_esc = re.escape(v1)
        v2_esc = re.escape(v2)
        pattern = re.compile(
            r"(?<!\d)(?<!\.)(" + v1_esc + r"|" + v2_esc + r")(?!\d)(?!\.)",
        )
        matches = list(pattern.finditer(text))
        if matches:
            last_match = matches[-1].group(1)
            match = self._match_decimal_value(last_match, v1, v2)
            if match:
                return ParsedAnswer(
                    value=match, raw_response=text,
                    parse_strategy="decimal_value_match", confidence=0.85,
                )

        # Strategy 5: Position keywords (last match)
        pos_m = re_search_last(_POSITION_RE, text)
        if pos_m:
            pos_word = pos_m.group(1).lower()
            pos = self._resolve_position(pos_word)
            if pos == "first":
                return ParsedAnswer(
                    value=v1, raw_response=text,
                    parse_strategy="decimal_position", confidence=0.75,
                )
            elif pos == "second":
                return ParsedAnswer(
                    value=v2, raw_response=text,
                    parse_strategy="decimal_position", confidence=0.75,
                )

        # Fallback
        return ParsedAnswer(
            value=None, raw_response=text,
            parse_strategy="decimal_fallback", confidence=0.10,
            error="Could not extract a decimal answer from response",
        )

    @staticmethod
    def _match_decimal_value(
        candidate: str, v1: str, v2: str,
    ) -> Optional[str]:
        """Check if candidate matches v1 or v2 (as bare number strings)."""
        c = candidate.strip()
        # Direct string match
        if c == v1:
            return v1
        if c == v2:
            return v2
        # Try float comparison for robustness (e.g. "9.90" vs "9.9")
        try:
            cf = float(c)
            if abs(cf - float(v1)) < 1e-9:
                return v1
            if abs(cf - float(v2)) < 1e-9:
                return v2
        except ValueError:
            pass
        return None
