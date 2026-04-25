"""
Measure Comparison – Response Parser

Extracts the model's chosen measurement from a free-form response.

Four answer categories:
  1. Normal     — a value+unit that matches one of the two options
  2. Equal      — keywords like "equal", "same", "equivalent"
  3. Incomparable — keywords like "cannot compare", "incomparable"
  4. Position   — "first"/"second" fallback

Strategy pipeline (tried in order, highest confidence first):
  1. boxed                \\boxed{...}                         0.95
  2. label_line           "Answer: ..."                        0.88
  3. bold                 **...** (two-pass: keywords, values) 0.90
  4. value_unit_comparative  "{val} {unit} is {comp}" + reverse  0.87
  5. keyword_incomparable detects "cannot compare" etc.        0.86
  6. value_unit_match     extract value+unit, match to options 0.85
  7. keyword_equal        detects "equal"/"same" etc.          0.82
  8. position_match       "first"/"second"                     0.75
  9. last_value_unit      last value+unit found                0.65
  10. bare_value_match    bare number match (no unit)          0.60
  11. fallback            parse error                          0.10
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import (
    re_search_last,
    build_answer_label_re,
    get_language,
    strip_verification_tail,
    normalize_unicode,
)

# ---------------------------------------------------------------------------
# Unit symbol aliases (normalised form → set of of display variants)
# ---------------------------------------------------------------------------

_SYMBOL_ALIASES: Dict[str, List[str]] = {
    # --- Length ---
    "mm": ["mm", "millimeter", "millimeters", "millimetre", "millimetres",
            "milímetro", "milímetros",                        # ES
            "millimètre", "millimètres",                      # FR
            "Millimeter",                                     # DE
            "міліметр", "міліметри",                          # UA
            "毫米"],                                           # ZH
    "cm": ["cm", "centimeter", "centimeters", "centimetre", "centimetres",
            "centímetro", "centímetros",                      # ES
            "centimètre", "centimètres",                      # FR
            "Zentimeter",                                     # DE
            "сантиметр", "сантиметри",                        # UA
            "厘米"],                                           # ZH
    "m":  ["m", "meter", "meters", "metre", "metres",
            "metro", "metros",                                # ES
            "mètre", "mètres",                                # FR
            "Meter",                                          # DE
            "метр", "метри",                                  # UA
            "米"],                                             # ZH
    "km": ["km", "kilometer", "kilometers", "kilometre", "kilometres",
            "kilómetro", "kilómetros",                        # ES
            "kilomètre", "kilomètres",                        # FR
            "Kilometer",                                      # DE
            "кілометр", "кілометри",                          # UA
            "公里"],                                           # ZH
    "in": ["in", "inch", "inches", '"',
            "pulgada", "pulgadas",                            # ES
            "pouce", "pouces",                                # FR
            "Zoll",                                           # DE
            "дюйм", "дюйми",                                 # UA
            "英寸"],                                           # ZH
    "ft": ["ft", "foot", "feet", "'",
            "pie", "pies",                                    # ES
            "pied", "pieds",                                  # FR
            "Fuß",                                            # DE
            "фут", "фути",                                    # UA
            "英尺"],                                           # ZH
    "yd": ["yd", "yard", "yards",
            "yarda", "yardas",                                # ES
            "ярд", "ярди"],                                   # UA
    "mi": ["mi", "mile", "miles",
            "milla", "millas",                                # ES
            "миля", "милі"],                                  # UA
    # --- Weight / Mass ---
    "mg": ["mg", "milligram", "milligrams",
            "miligramo", "miligramos",                        # ES
            "milligramme", "milligrammes",                    # FR
            "Milligramm",                                     # DE
            "міліграм", "міліграми",                          # UA
            "毫克"],                                           # ZH
    "g":  ["g", "gram", "grams",
            "gramo", "gramos",                                # ES
            "gramme", "grammes",                              # FR
            "Gramm",                                          # DE
            "грам", "грами",                                  # UA
            "克"],                                             # ZH
    "kg": ["kg", "kilogram", "kilograms",
            "kilogramo", "kilogramos",                         # ES
            "kilogramme", "kilogrammes",                       # FR
            "Kilogramm",                                       # DE
            "кілограм", "кілограми",                           # UA
            "千克", "公斤"],                                    # ZH
    "oz": ["oz", "ounce", "ounces",
            "onza", "onzas",                                  # ES
            "унція", "унції"],                                # UA
    "lb": ["lb", "lbs", "pound", "pounds",
            "libra", "libras",                                # ES
            "livre", "livres",                                # FR
            "Pfund",                                          # DE
            "фунт", "фунти",                                  # UA
            "磅"],                                             # ZH
    # --- Temperature ---
    "°C": ["°c", "°C", "celsius", "c", "degrees celsius", "deg c",
            "grado celsius", "grados celsius",                # ES
            "degré celsius", "degrés celsius",                # FR
            "Grad Celsius",                                   # DE
            "градус Цельсія", "градуси Цельсія",              # UA
            "摄氏度"],                                         # ZH
    "°F": ["°f", "°F", "fahrenheit", "f", "degrees fahrenheit", "deg f",
            "grado fahrenheit", "grados fahrenheit",          # ES
            "degré fahrenheit", "degrés fahrenheit",          # FR
            "Grad Fahrenheit",                                # DE
            "градус Фаренгейта", "градуси Фаренгейта",       # UA
            "华氏度"],                                         # ZH
    "K":  ["k", "kelvin",
            "кельвін"],                                       # UA
    # --- Volume ---
    "mL": ["ml", "mL", "milliliter", "milliliters", "millilitre", "millilitres",
            "mililitro", "mililitros",                        # ES
            "millilitre", "millilitres",                      # FR (same as EN-GB)
            "Milliliter",                                     # DE
            "мілілітр", "мілілітри",                          # UA
            "毫升"],                                           # ZH
    "L":  ["l", "L", "liter", "liters", "litre", "litres",
            "litro", "litros",                                # ES
            "Liter",                                          # DE
            "літр", "літри",                                  # UA
            "升"],                                             # ZH
    "cup": ["cup", "cups",
            "taza", "tazas",                                  # ES
            "tasse", "tasses",                                # FR
            "Tasse", "Tassen",                                # DE
            "чашка", "чашки"],                                # UA
    "fl oz": ["fl oz", "fluid ounce", "fluid ounces", "fl. oz", "fl.oz"],
    "pt": ["pt", "pint", "pints",
            "pinta", "pintas"],                               # ES
    "gal": ["gal", "gallon", "gallons",
            "galón", "galones",                               # ES
            "галон", "галони"],                               # UA
    # --- Speed ---
    "m/s": ["m/s", "meters per second", "metres per second",
            "metros por segundo",                             # ES
            "mètres par seconde",                             # FR
            "Meter pro Sekunde",                              # DE
            "метрів на секунду",                              # UA
            "米每秒"],                                         # ZH
    "km/h": ["km/h", "kmh", "kph", "kilometers per hour", "kilometres per hour",
            "kilómetros por hora",                            # ES
            "kilomètres par heure",                           # FR
            "Kilometer pro Stunde",                           # DE
            "кілометрів на годину",                           # UA
            "公里每小时"],                                     # ZH
    "mph": ["mph", "miles per hour",
            "millas por hora",                                # ES
            "miles par heure",                                # FR
            "Meilen pro Stunde",                              # DE
            "миль на годину"],                                # UA
    # --- Time ---
    "s":  ["s", "sec", "second", "seconds",
            "segundo", "segundos",                            # ES
            "seconde", "secondes",                            # FR
            "Sekunde", "Sekunden",                            # DE
            "секунда", "секунди",                             # UA
            "秒"],                                             # ZH
    "min": ["min", "minute", "minutes",
            "minuto", "minutos",                              # ES
            "Minute", "Minuten",                              # DE
            "хвилина", "хвилини",                             # UA
            "分钟"],                                           # ZH
    "h":  ["h", "hr", "hour", "hours",
            "hora", "horas",                                  # ES
            "heure", "heures",                                # FR
            "Stunde", "Stunden",                              # DE
            "година", "години",                               # UA
            "小时"],                                           # ZH
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
    r"(?:\b(?:equal|equivalent|identical|no\s+difference)\b"
    r"|\bboth.{0,15}(?:equal|same)\b"
    r"|\b(?:are|is|they'?re|that'?s)\s+(?:exactly\s+)?(?:the\s+)?same\b"
    r"|\bsame\s+(?:value|amount|quantity|measurement|weight|length|distance|volume|speed|temperature|size)\b"
    r"|\bneither\s+is\s+(?:shorter|longer|heavier|lighter|hotter|colder|warmer|cooler|faster|slower|bigger|smaller|greater|more|less)\b"
    r"|\bigual\b|\biguales\b|\bmême\b|\bmêmes\b|\bégal\b|\bégales\b|\bégaux\b"
    r"|\bgleich\b|\bidentisch\b|\bkein\s+Unterschied\b"
    r"|\bрівні\b|\bоднакові\b|\bідентичні\b|\bнемає\s+різниці\b"
    r"|相等|相同|一样|没有区别)",
    re.IGNORECASE,
)

# Incomparable keywords
_INCOMPARABLE_KEYWORDS = re.compile(
    r"(?:cannot\s+(?:be\s+)?compare|can'?t\s+(?:be\s+)?compare|aren'?t\s+comparable|incomparable|"
    r"not\s+comparable|not\s+(?:a\s+)?meaningful|"
    r"different\s+(?:physical\s+)?(?:dimensions?|categories|units?|quantities"
    r"|kinds?\s+of\s+(?:units?|measurements?|quantities)"
    r"|types?\s+of\s+(?:units?|measurements?|quantities)"
    r"|things)|"
    r"measure\s+different\s+things|"
    r"impossible\s+to\s+compare|apples?\s+and\s+oranges?|"
    r"no\s+(?:se\s+)?puede[n]?\s+comparar|incomparables?|"
    r"ne\s+(?:peut|peuvent)\s+pas\s+(?:être\s+)?comparée?s?|"
    r"pas\s+comparables?|"
    r"nicht\s+vergleichbar|lassen\s+sich\s+nicht\s+vergleichen|"
    r"nicht\s+miteinander\s+vergleichbar|"
    r"无法比较|不能比较|不可比较|无法对比|"
    r"непорівнянні|неможливо\s+порівняти|не\s+можна\s+порівняти|"
    r"не\s+піддаються\s+порівнянню)",
    re.IGNORECASE,
)

# Position keywords
_POSITION_RE = re.compile(
    r"\b(first|second|1st|2nd|option\s*[12ab]|choice\s*[12ab]|"
    r"primer[ao]|segund[ao]|premier|première|deuxième|erst[eér]|zweit[eér]|"
    r"第一|第二|перш[аеийіь]|друг[аеийі])\b",
    re.IGNORECASE,
)

# Comparative adjectives per language
_COMPARATIVE_ADJECTIVES: Dict[str, str] = {
    "en": (r"shorter|longer|heavier|lighter|hotter|colder|warmer|cooler|"
           r"faster|slower|bigger|smaller|greater|less|more|fewer|"
           r"larger|higher|lower|taller|wider"),
    "es": (r"más corto|más largo|más pesado|más ligero|más caliente|más frío|"
           r"más rápido|más lento|más grande|más pequeño|mayor|menor"),
    "fr": (r"plus court|plus long|plus lourd|plus léger|plus chaud|plus froid|"
           r"plus rapide|plus lent|plus grand|plus petit"),
    "de": (r"kürzer|länger|schwerer|leichter|heißer|kälter|"
           r"schneller|langsamer|größer|kleiner|höher|niedriger"),
    "zh": r"更短|更长|更重|更轻|更热|更冷|更快|更慢|更大|更小",
    "ua": (r"коротший|довший|важчий|легший|гарячіший|холодніший|"
           r"швидший|повільніший|більший|менший"),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _normalise_unit(text: str) -> Optional[str]:
    """Return the canonical unit symbol for *text*, or None."""
    text = text.strip().rstrip(".,;:!?)")
    low = text.lower()
    if low in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[low]
    # Try progressively shorter prefixes.
    # Allow single-char matches only when the next char is non-alpha
    # (avoids "k"→kelvin for "kilometer" while allowing "h" from "h is shorter")
    for length in range(len(low), 0, -1):
        prefix = low[:length].rstrip()
        if prefix in _ALIAS_TO_CANON:
            if len(prefix) == 1 and len(low) > 1 and low[1:2].isalpha():
                continue
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

        text = normalize_unicode(response.strip())
        tp = task_params or {}
        lang = get_language(tp)

        # Route decimal comparison type to a specialised parser (bare numbers)
        if tp.get("comparison_type") == "decimal":
            return self._parse_decimal(text, tp, lang)

        # Keyword strategies use a tail-stripped copy to avoid "same unit" /
        # "equal in magnitude" phrases in verification sections firing as
        # false-positive equal/incomparable answers.
        text_for_keywords = strip_verification_tail(text)

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

        # --- Strategy 2: Label line (last match) ---
        # Runs before bold so that an explicit "Answer:" label takes priority
        # over bold values scattered in the reasoning text.  The word-boundary
        # in build_answer_label_re() matches "answer" inside "**Answer:**"
        # because "**" is non-word and does not break \b.
        answer_labels = build_answer_label_re(lang)
        label = re_search_last(
            r"(?:" + answer_labels + r"|the\s+(?:answer|result)\s+is)\s*[:：]?\s*(.+?)(?:\.|$)",
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

        # --- Strategy 3: Bold (two-pass: keywords first, then values) ---
        # Pass 1: any bold with equal/incomparable keywords takes priority.
        # Pass 2: last-resolvable bold for value+unit extraction.
        bold_matches = list(re.finditer(r"\*\*([^*]{1,40})\*\*", text))
        for bold in bold_matches:
            inner = bold.group(1).strip()
            if _EQUAL_KEYWORDS.search(inner) or _INCOMPARABLE_KEYWORDS.search(inner):
                result = self._try_resolve(inner, tp)
                if result is not None:
                    return ParsedAnswer(
                        value=result, raw_response=text,
                        parse_strategy="bold", confidence=0.90,
                    )
        for bold in reversed(bold_matches):
            inner = bold.group(1).strip()
            # Skip bolds ending with ':' — they are headers, not answers
            if inner.endswith(':'):
                continue
            result = self._try_resolve(inner, tp)
            if result is not None:
                return ParsedAnswer(
                    value=result, raw_response=text,
                    parse_strategy="bold", confidence=0.90,
                )

        # --- Strategy 4: "{value} {unit} is {comparative}" pattern ---
        # Handles responses like "18.68 h is shorter." where the answer is
        # stated plainly without labels, bold, or boxed formatting.
        # Build language-aware comparatives: always include EN + target language
        _comp_en = _COMPARATIVE_ADJECTIVES["en"]
        _comp_local = _COMPARATIVE_ADJECTIVES.get(lang, "")
        _COMPARATIVES = _comp_en + ("|" + _comp_local if _comp_local and lang != "en" else "")

        # EN-style: "{value} {unit} is [adv ...] {comparative}"
        # Allow up to 2 intermediate words (e.g. "is indeed heavier",
        # "is clearly longer") without losing the option-matching guard below.
        fwd_m = re_search_last(
            r"(" + _VALUE_RE + r")\s+(°?[A-Za-z/][A-Za-z/.]*)\s+(?:is|es|est|ist|є)"
            r"\s+(?:\w+\s+){0,2}"
            r"(?:" + _COMPARATIVES + r")",
            text,
            re.IGNORECASE,
        )
        # Reverse pattern: "the {comparative} [adv ...] one is {value} {unit}"
        rev_m = re_search_last(
            r"(?:" + _COMPARATIVES + r")\s+(?:\w+\s+){0,2}"
            r"(?:one\s+)?(?:is|es|est|ist|є)\s+"
            r"(" + _VALUE_RE + r")\s+(°?[A-Za-z/][A-Za-z/.]*)",
            text,
            re.IGNORECASE,
        )
        # When both fire, take the one whose span ends LATER in the text —
        # end-first principle.  The forward pattern can grab an early
        # comparison statement ("609 kg is much heavier") while a later
        # reverse match ("the lighter one is 758 oz") is the true answer.
        if fwd_m and rev_m:
            comp_m = fwd_m if fwd_m.end() >= rev_m.end() else rev_m
        else:
            comp_m = fwd_m or rev_m
        if comp_m:
            val_str = comp_m.group(1)
            unit_text = comp_m.group(2).strip()
            unit_canon = _normalise_unit(unit_text)
            if unit_canon:
                pos = _match_to_option(val_str, unit_canon, tp)
                if pos:
                    answer = _position_to_answer(pos, tp)
                    return ParsedAnswer(
                        value=answer, raw_response=text,
                        parse_strategy="value_unit_comparative", confidence=0.87,
                    )

        # --- Strategy 5: Incomparable keywords ---
        # Checked BEFORE value_unit_match: incomparable responses always
        # restate both values in explanation, so value extraction would
        # incorrectly pick one up.
        if _INCOMPARABLE_KEYWORDS.search(text_for_keywords):
            negated = re.search(r"\b(?:not|no|n't)\b.{0,30}" + _INCOMPARABLE_KEYWORDS.pattern, text_for_keywords, re.IGNORECASE)
            if not negated:
                return ParsedAnswer(
                    value="incomparable", raw_response=text,
                    parse_strategy="keyword_incomparable", confidence=0.86,
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

        # --- Strategy 7: Equal keywords ---
        # Checked AFTER value_unit_match and incomparable: "same" can appear
        # in explanatory context (e.g. "the same unit").
        if _EQUAL_KEYWORDS.search(text_for_keywords):
            negated = re.search(r"\b(?:not|no|n't|aren'?t|isn'?t)\b.{0,30}" + _EQUAL_KEYWORDS.pattern, text_for_keywords, re.IGNORECASE)
            if not negated:
                return ParsedAnswer(
                    value="equal", raw_response=text,
                    parse_strategy="keyword_equal", confidence=0.82,
                )

        # --- Strategy 8: Position keywords (last match) ---
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

        # --- Strategy 9: Last value+unit found ---
        if vus:
            last_val, last_unit, _, raw = vus[-1]
            answer = f"{last_val} {last_unit}"
            return ParsedAnswer(
                value=answer, raw_response=text,
                parse_strategy="last_value_unit", confidence=0.65,
            )

        # --- Strategy 10: Bare value match (no unit) ---
        # Some models omit units entirely. Match bare numbers against
        # option values (end-first).
        v1 = tp.get("value1", "")
        v2 = tp.get("value2", "")
        if v1 or v2:
            bare_nums = re.findall(r"(?<!\d)(?<!\.)(" + _VALUE_RE + r")(?!\d)(?!\.)", text)
            for num_str in reversed(bare_nums):
                if v1 and _values_match(num_str, v1):
                    answer = _position_to_answer("first", tp)
                    return ParsedAnswer(
                        value=answer, raw_response=text,
                        parse_strategy="bare_value_match", confidence=0.60,
                    )
                if v2 and _values_match(num_str, v2):
                    answer = _position_to_answer("second", tp)
                    return ParsedAnswer(
                        value=answer, raw_response=text,
                        parse_strategy="bare_value_match", confidence=0.60,
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
            "primero", "primera",                              # ES
            "premier", "première",                             # FR
            "erste", "erster", "erstes",                       # DE
            "第一",                                             # ZH
            "перший", "перша", "перше",                        # UA
        }
        second_words = {
            "second", "2nd", "option 2", "option b", "choice 2", "choice b",
            "segundo", "segunda",                              # ES
            "deuxième", "second", "seconde",                   # FR
            "zweite", "zweiter", "zweites",                    # DE
            "第二",                                             # ZH
            "другий", "друга", "друге",                        # UA
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

    def _parse_decimal(self, text: str, tp: Dict[str, Any], lang: str = "en") -> ParsedAnswer:
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
        dec_answer_labels = build_answer_label_re(lang)
        label = re_search_last(
            r"(?:" + dec_answer_labels + r"|the\s+(?:answer|result)\s+is)\s*[:：]?\s*(.+?)(?:\.|$)",
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
