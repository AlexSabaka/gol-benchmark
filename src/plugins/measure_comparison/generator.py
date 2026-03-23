"""
Measure Comparison – Test Case Generator

Generates "Which is bigger/smaller: A or B?" test cases for quantity
comparison with measurement units.

Comparison types
  same_unit     — both quantities share a unit (pure number comparison)
  mixed_unit    — compatible units requiring conversion (e.g. cm vs inch)
  equal         — trick: different representation of the same quantity
  incomparable  — trick: different physical dimensions (no valid comparison)

Number formats
  integer   — whole numbers
  decimal   — floats, with optional adversarial digit-count traps
  fraction  — proper/improper fractions rendered as "3/4"
  mixed     — weighted blend (default)

Config keys (all optional, sensible defaults provided):
  number_format           str   "integer"|"decimal"|"fraction"|"mixed" (default "mixed")
  comparison_type         str   "same_unit"|"mixed_unit"|"equal"|"incomparable"|"all"
  type_weights            dict  weights when comparison_type="all"
  unit_categories         list  subset of length/mass/temperature/volume/speed/time
  question_direction      str   "bigger"|"smaller"|"mixed" (default "mixed")
  decimal_trap_ratio      float proportion of decimal Qs that are adversarial (default 0.3)
  close_value_ratio       float proportion of same-unit Qs with very close values (0.2)
  value_order             str   "random"|"bigger_first"|"smaller_first" (default "random")
  fraction_max_denominator int  (default 16)
  max_decimal_places      int   (default 3)
  language                str   prompt language code (default "en")
  count                   int   number of test cases
"""
from __future__ import annotations

import math
import random
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import TestCaseGenerator, TestCase

# =========================================================================
# Unit System
# =========================================================================

# Each unit: (symbol, to_base_factor)
# `to_base_factor` is a float multiplier to the category base unit.
# Temperature is special — handled via function pairs, factor is unused.

UNITS: Dict[str, Dict[str, Tuple[str, float]]] = {
    "length": {
        # base = metre
        "mm":   ("mm",   0.001),
        "cm":   ("cm",   0.01),
        "m":    ("m",    1.0),
        "km":   ("km",   1000.0),
        "inch": ("in",   0.0254),
        "foot": ("ft",   0.3048),
        "yard": ("yd",   0.9144),
        "mile": ("mi",   1609.344),
    },
    "mass": {
        # base = gram
        "mg":  ("mg", 0.001),
        "g":   ("g",  1.0),
        "kg":  ("kg", 1000.0),
        "oz":  ("oz", 28.3495),
        "lb":  ("lb", 453.592),
    },
    "temperature": {
        # base = Kelvin  (conversions handled by functions below)
        "C":  ("°C", 0.0),
        "F":  ("°F", 0.0),
        "K":  ("K",  0.0),
    },
    "volume": {
        # base = millilitre
        "mL":     ("mL",  1.0),
        "L":      ("L",   1000.0),
        "cup":    ("cup", 236.588),
        "fl_oz":  ("fl oz", 29.5735),
        "pint":   ("pt",  473.176),
        "gallon": ("gal", 3785.41),
    },
    "speed": {
        # base = m/s
        "m/s":  ("m/s",  1.0),
        "km/h": ("km/h", 1.0 / 3.6),
        "mph":  ("mph",  0.44704),
    },
    "time": {
        # base = second
        "s":   ("s",   1.0),
        "min": ("min", 60.0),
        "h":   ("h",   3600.0),
    },
}

# Display symbols  (unit_key → display string used in prompts)
UNIT_SYMBOLS: Dict[str, str] = {}
_UNIT_TO_BASE: Dict[str, float] = {}
_UNIT_CATEGORY: Dict[str, str] = {}

for _cat, _units in UNITS.items():
    for _ukey, (_sym, _factor) in _units.items():
        UNIT_SYMBOLS[_ukey] = _sym
        _UNIT_TO_BASE[_ukey] = _factor
        _UNIT_CATEGORY[_ukey] = _cat


# ---- Temperature helpers ------------------------------------------------

def _to_kelvin(value: float, unit_key: str) -> float:
    if unit_key == "K":
        return value
    if unit_key == "C":
        return value + 273.15
    if unit_key == "F":
        return (value - 32) * 5.0 / 9.0 + 273.15
    raise ValueError(f"Unknown temperature unit: {unit_key}")


def _from_kelvin(kelvin: float, unit_key: str) -> float:
    if unit_key == "K":
        return kelvin
    if unit_key == "C":
        return kelvin - 273.15
    if unit_key == "F":
        return (kelvin - 273.15) * 9.0 / 5.0 + 32
    raise ValueError(f"Unknown temperature unit: {unit_key}")


def to_base(value: float, unit_key: str) -> float:
    """Convert *value* in *unit_key* to the category's base unit."""
    if _UNIT_CATEGORY[unit_key] == "temperature":
        return _to_kelvin(value, unit_key)
    return value * _UNIT_TO_BASE[unit_key]


def from_base(base_value: float, unit_key: str) -> float:
    """Convert a base-unit value back to *unit_key*."""
    if _UNIT_CATEGORY[unit_key] == "temperature":
        return _from_kelvin(base_value, unit_key)
    return base_value / _UNIT_TO_BASE[unit_key]


# =========================================================================
# Known exact conversion pairs  (for "equal" trick questions)
# =========================================================================
# (unit_a, value_a, unit_b, value_b)  — guaranteed exact equivalence

EQUAL_PAIRS: List[Tuple[str, float, str, float]] = [
    # length
    ("km", 1,    "m",    1000),
    ("m",  1,    "cm",   100),
    ("cm", 1,    "mm",   10),
    ("foot", 1,  "inch", 12),
    ("yard", 1,  "foot", 3),
    ("mile", 1,  "yard", 1760),
    ("inch", 1,  "cm",   2.54),
    # mass
    ("kg", 1,    "g",    1000),
    ("g",  1,    "mg",   1000),
    ("lb", 1,    "oz",   16),
    # volume
    ("L",    1,  "mL",   1000),
    ("gallon", 1, "pint", 8),
    ("cup",  1,  "fl_oz", 8),
    # temperature
    ("C",  0,    "F",    32),
    ("C",  100,  "F",    212),
    ("C",  0,    "K",    273.15),
    # time
    ("h",  1,    "min",  60),
    ("min", 1,   "s",    60),
    ("h",  1,    "s",    3600),
    # speed
    ("km/h", 3.6, "m/s", 1),
]


# =========================================================================
# Multilingual prompts
# =========================================================================

# Comparison words per category × direction × language
# {lang: {cat: {bigger: ..., smaller: ...}}}

COMPARISON_WORDS: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "length":      {"bigger": "longer",  "smaller": "shorter"},
        "mass":        {"bigger": "heavier", "smaller": "lighter"},
        "temperature": {"bigger": "hotter",  "smaller": "colder"},
        "volume":      {"bigger": "more",    "smaller": "less"},
        "speed":       {"bigger": "faster",  "smaller": "slower"},
        "time":        {"bigger": "longer",  "smaller": "shorter"},
        "_generic":    {"bigger": "bigger",  "smaller": "smaller"},
    },
    "es": {
        "length":      {"bigger": "más largo",  "smaller": "más corto"},
        "mass":        {"bigger": "más pesado", "smaller": "más ligero"},
        "temperature": {"bigger": "más caliente", "smaller": "más frío"},
        "volume":      {"bigger": "más",        "smaller": "menos"},
        "speed":       {"bigger": "más rápido", "smaller": "más lento"},
        "time":        {"bigger": "más largo",  "smaller": "más corto"},
        "_generic":    {"bigger": "más grande", "smaller": "más pequeño"},
    },
    "fr": {
        "length":      {"bigger": "plus long",  "smaller": "plus court"},
        "mass":        {"bigger": "plus lourd", "smaller": "plus léger"},
        "temperature": {"bigger": "plus chaud", "smaller": "plus froid"},
        "volume":      {"bigger": "plus",       "smaller": "moins"},
        "speed":       {"bigger": "plus rapide","smaller": "plus lent"},
        "time":        {"bigger": "plus long",  "smaller": "plus court"},
        "_generic":    {"bigger": "plus grand", "smaller": "plus petit"},
    },
    "de": {
        "length":      {"bigger": "länger",    "smaller": "kürzer"},
        "mass":        {"bigger": "schwerer",  "smaller": "leichter"},
        "temperature": {"bigger": "heißer",    "smaller": "kälter"},
        "volume":      {"bigger": "mehr",      "smaller": "weniger"},
        "speed":       {"bigger": "schneller", "smaller": "langsamer"},
        "time":        {"bigger": "länger",    "smaller": "kürzer"},
        "_generic":    {"bigger": "größer",    "smaller": "kleiner"},
    },
    "zh": {
        "length":      {"bigger": "更长", "smaller": "更短"},
        "mass":        {"bigger": "更重", "smaller": "更轻"},
        "temperature": {"bigger": "更热", "smaller": "更冷"},
        "volume":      {"bigger": "更多", "smaller": "更少"},
        "speed":       {"bigger": "更快", "smaller": "更慢"},
        "time":        {"bigger": "更长", "smaller": "更短"},
        "_generic":    {"bigger": "更大", "smaller": "更小"},
    },
    "ua": {
        "length":      {"bigger": "довший",    "smaller": "коротший"},
        "mass":        {"bigger": "важчий",    "smaller": "легший"},
        "temperature": {"bigger": "гарячіший", "smaller": "холодніший"},
        "volume":      {"bigger": "більше",    "smaller": "менше"},
        "speed":       {"bigger": "швидший",   "smaller": "повільніший"},
        "time":        {"bigger": "довший",    "smaller": "коротший"},
        "_generic":    {"bigger": "більший",   "smaller": "менший"},
    },
}


# ---------------------------------------------------------------------------
# Question templates  {lang: [templates]}
# Placeholders: {comp_word}, {val1}, {unit1}, {val2}, {unit2}
# ---------------------------------------------------------------------------

QUESTION_TEMPLATES: Dict[str, List[str]] = {
    "en": [
        "Which is {comp_word}: {val1} {unit1} or {val2} {unit2}?",
        "What is {comp_word}, {val1} {unit1} or {val2} {unit2}?",
        "Is {val1} {unit1} or {val2} {unit2} {comp_word}?",
        "Between {val1} {unit1} and {val2} {unit2}, which is {comp_word}?",
        "{val1} {unit1} vs {val2} {unit2} — which is {comp_word}?",
    ],
    "es": [
        "¿Qué es {comp_word}: {val1} {unit1} o {val2} {unit2}?",
        "¿Cuál es {comp_word}, {val1} {unit1} o {val2} {unit2}?",
        "Entre {val1} {unit1} y {val2} {unit2}, ¿cuál es {comp_word}?",
        "{val1} {unit1} vs {val2} {unit2} — ¿cuál es {comp_word}?",
    ],
    "fr": [
        "Qu'est-ce qui est {comp_word} : {val1} {unit1} ou {val2} {unit2} ?",
        "Lequel est {comp_word}, {val1} {unit1} ou {val2} {unit2} ?",
        "Entre {val1} {unit1} et {val2} {unit2}, lequel est {comp_word} ?",
        "{val1} {unit1} vs {val2} {unit2} — lequel est {comp_word} ?",
    ],
    "de": [
        "Was ist {comp_word}: {val1} {unit1} oder {val2} {unit2}?",
        "Welches ist {comp_word}, {val1} {unit1} oder {val2} {unit2}?",
        "Zwischen {val1} {unit1} und {val2} {unit2}, was ist {comp_word}?",
        "{val1} {unit1} vs {val2} {unit2} — was ist {comp_word}?",
    ],
    "zh": [
        "{val1} {unit1} 和 {val2} {unit2}，哪个{comp_word}？",
        "哪个{comp_word}：{val1} {unit1} 还是 {val2} {unit2}？",
        "{val1} {unit1} vs {val2} {unit2}——哪个{comp_word}？",
    ],
    "ua": [
        "Що є {comp_word}: {val1} {unit1} чи {val2} {unit2}?",
        "Яке {comp_word}, {val1} {unit1} чи {val2} {unit2}?",
        "Між {val1} {unit1} та {val2} {unit2}, що є {comp_word}?",
        "{val1} {unit1} vs {val2} {unit2} — що є {comp_word}?",
    ],
}

# ---------------------------------------------------------------------------
# System prompts  {lang: {style: prompt}}
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS: Dict[str, Dict[str, str]] = {
    "en": {
        "analytical": (
            "You are a precise measurement comparison assistant. "
            "When asked to compare two quantities, carefully convert units "
            "if necessary and provide the correct answer. "
            "If the quantities are equal, say 'equal'. "
            "If they cannot be compared (different physical dimensions), "
            "say 'incomparable'."
        ),
        "casual": (
            "You're a helpful assistant. Compare the two measurements "
            "and tell me which one is bigger (or smaller). "
            "Just give the answer."
        ),
        "adversarial": (
            "Answer with just the winning measurement. "
            "No explanations, no working."
        ),
    },
    "es": {
        "analytical": (
            "Eres un asistente preciso de comparación de medidas. "
            "Cuando se te pida comparar dos cantidades, convierte las unidades "
            "cuidadosamente si es necesario y proporciona la respuesta correcta. "
            "Si las cantidades son iguales, di 'igual'. "
            "Si no se pueden comparar, di 'incomparable'."
        ),
        "casual": "Eres un asistente útil. Compara las dos medidas y dime cuál es mayor. Solo da la respuesta.",
        "adversarial": "Responde solo con la medida ganadora. Sin explicaciones.",
    },
    "fr": {
        "analytical": (
            "Vous êtes un assistant précis de comparaison de mesures. "
            "Lorsqu'on vous demande de comparer deux quantités, convertissez "
            "soigneusement les unités si nécessaire et fournissez la bonne réponse. "
            "Si les quantités sont égales, dites 'égal'. "
            "Si elles ne peuvent pas être comparées, dites 'incomparable'."
        ),
        "casual": "Vous êtes un assistant utile. Comparez les deux mesures et dites-moi laquelle est plus grande. Juste la réponse.",
        "adversarial": "Répondez uniquement avec la mesure gagnante. Pas d'explications.",
    },
    "de": {
        "analytical": (
            "Sie sind ein präziser Vergleichsassistent für Maßeinheiten. "
            "Wenn Sie gebeten werden, zwei Mengen zu vergleichen, konvertieren Sie "
            "die Einheiten sorgfältig, falls nötig, und geben Sie die richtige Antwort. "
            "Wenn die Mengen gleich sind, sagen Sie 'gleich'. "
            "Wenn sie nicht vergleichbar sind, sagen Sie 'nicht vergleichbar'."
        ),
        "casual": "Du bist ein hilfreicher Assistent. Vergleiche die beiden Messungen und sag mir, welche größer ist. Nur die Antwort.",
        "adversarial": "Antworte nur mit der größeren Messung. Keine Erklärungen.",
    },
    "zh": {
        "analytical": (
            "你是一个精确的测量比较助手。"
            "当被要求比较两个数量时，如有必要请仔细换算单位，并提供正确答案。"
            "如果数量相等，请说'相等'。"
            "如果无法比较（不同物理量纲），请说'无法比较'。"
        ),
        "casual": "你是一个helpful助手。比较两个测量值，告诉我哪个更大。只给答案。",
        "adversarial": "只回答更大的那个测量值。不要解释。",
    },
    "ua": {
        "analytical": (
            "Ви — точний помічник для порівняння вимірювань. "
            "Коли вас просять порівняти дві величини, уважно перетворіть одиниці "
            "за потреби та надайте правильну відповідь. "
            "Якщо величини рівні, скажіть 'рівні'. "
            "Якщо їх неможливо порівняти, скажіть 'непорівнянні'."
        ),
        "casual": "Ви — корисний помічник. Порівняйте два вимірювання і скажіть, яке більше. Тільки відповідь.",
        "adversarial": "Відповідайте лише більшим вимірюванням. Без пояснень.",
    },
}

# ---------------------------------------------------------------------------
# User prompt templates  {lang: {style: template}}
# Placeholder: {question}
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "minimal": "{question}\n\nAnswer:",
        "casual": "Hey, quick question — {question}",
        "linguistic": (
            "I have a measurement comparison question for you.\n\n"
            "{question}\n\n"
            "Please provide just the winning measurement "
            "(or 'equal' / 'incomparable' if applicable)."
        ),
    },
    "es": {
        "minimal": "{question}\n\nRespuesta:",
        "casual": "Oye, pregunta rápida — {question}",
        "linguistic": (
            "Tengo una pregunta sobre comparación de medidas.\n\n"
            "{question}\n\n"
            "Por favor, proporciona solo la medida ganadora."
        ),
    },
    "fr": {
        "minimal": "{question}\n\nRéponse :",
        "casual": "Salut, petite question — {question}",
        "linguistic": (
            "J'ai une question de comparaison de mesures.\n\n"
            "{question}\n\n"
            "Veuillez fournir uniquement la mesure gagnante."
        ),
    },
    "de": {
        "minimal": "{question}\n\nAntwort:",
        "casual": "Hey, kurze Frage — {question}",
        "linguistic": (
            "Ich habe eine Frage zum Vergleich von Maßeinheiten.\n\n"
            "{question}\n\n"
            "Bitte geben Sie nur die größere Messung an."
        ),
    },
    "zh": {
        "minimal": "{question}\n\n答案：",
        "casual": "嘿，快问一下——{question}",
        "linguistic": (
            "我有一个关于测量比较的问题。\n\n"
            "{question}\n\n"
            "请只提供较大的测量值。"
        ),
    },
    "ua": {
        "minimal": "{question}\n\nВідповідь:",
        "casual": "Привіт, швидке питання — {question}",
        "linguistic": (
            "У мене є питання про порівняння вимірювань.\n\n"
            "{question}\n\n"
            "Будь ласка, надайте лише більше вимірювання."
        ),
    },
}


# =========================================================================
# Generator
# =========================================================================

class MeasureComparisonGenerator(TestCaseGenerator):
    """Generates measurement-comparison test cases."""

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, Any],
        count: int,
        seed: int | None = None,
    ) -> List[TestCase]:
        rng = random.Random(seed)

        # ---- Config ----
        number_format = config.get("number_format", "mixed")
        comparison_type = config.get("comparison_type", "all")
        type_weights = config.get("type_weights", {
            "same_unit": 0.40,
            "mixed_unit": 0.30,
            "equal": 0.15,
            "incomparable": 0.15,
        })
        unit_categories = config.get("unit_categories", list(UNITS.keys()))
        question_direction = config.get("question_direction", "mixed")
        decimal_trap_ratio = config.get("decimal_trap_ratio", 0.3)
        close_value_ratio = config.get("close_value_ratio", 0.2)
        value_order = config.get("value_order", "random")
        frac_max_denom = config.get("fraction_max_denominator", 16)
        max_dp = config.get("max_decimal_places", 3)
        language = config.get("language", "en")

        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get(
            "name", f"measure_comparison_{user_style}_{system_style}"
        )

        test_cases: List[TestCase] = []
        for idx in range(count):
            # Pick comparison type
            ctype = self._pick_comparison_type(comparison_type, type_weights, rng)

            # Pick number format for this case
            nfmt = self._pick_number_format(number_format, rng)

            # Pick direction
            direction = self._pick_direction(question_direction, rng)

            # Generate the case
            case = self._generate_case(
                ctype=ctype,
                nfmt=nfmt,
                direction=direction,
                unit_categories=unit_categories,
                decimal_trap_ratio=decimal_trap_ratio,
                close_value_ratio=close_value_ratio,
                value_order=value_order,
                frac_max_denom=frac_max_denom,
                max_dp=max_dp,
                rng=rng,
            )

            # Build prompts
            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                language=language,
                direction=direction,
                case=case,
                rng=rng,
            )
            test_cases.append(tc)

        return test_cases

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_comparison_type(
        comparison_type: str,
        type_weights: Dict[str, float],
        rng: random.Random,
    ) -> str:
        if comparison_type != "all":
            return comparison_type
        modes = list(type_weights.keys())
        weights = [type_weights[m] for m in modes]
        return rng.choices(modes, weights=weights, k=1)[0]

    @staticmethod
    def _pick_number_format(number_format: str, rng: random.Random) -> str:
        if number_format != "mixed":
            return number_format
        return rng.choice(["integer", "decimal", "fraction"])

    @staticmethod
    def _pick_direction(question_direction: str, rng: random.Random) -> str:
        if question_direction != "mixed":
            return question_direction
        return rng.choice(["bigger", "smaller"])

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def _generate_case(
        self,
        *,
        ctype: str,
        nfmt: str,
        direction: str,
        unit_categories: List[str],
        decimal_trap_ratio: float,
        close_value_ratio: float,
        value_order: str,
        frac_max_denom: int,
        max_dp: int,
        rng: random.Random,
    ) -> Dict[str, Any]:
        """Return a dict describing one comparison problem.

        Keys: val1_str, unit1_key, val2_str, unit2_key,
              val1_base, val2_base, category, comparison_type,
              number_format, is_decimal_trap, correct_position,
              expected_answer
        """
        if ctype == "incomparable":
            return self._gen_incomparable(nfmt, unit_categories, frac_max_denom, max_dp, rng)
        if ctype == "equal":
            return self._gen_equal(nfmt, unit_categories, frac_max_denom, max_dp, rng)
        if ctype == "mixed_unit":
            return self._gen_mixed_unit(
                nfmt, direction, unit_categories, decimal_trap_ratio,
                close_value_ratio, value_order, frac_max_denom, max_dp, rng,
            )
        # same_unit
        return self._gen_same_unit(
            nfmt, direction, unit_categories, decimal_trap_ratio,
            close_value_ratio, value_order, frac_max_denom, max_dp, rng,
        )

    # ---- same_unit ---------------------------------------------------

    def _gen_same_unit(
        self, nfmt, direction, cats, trap_ratio, close_ratio, order, frac_denom, max_dp, rng,
    ) -> Dict[str, Any]:
        cat = rng.choice(cats)
        unit_key = rng.choice(list(UNITS[cat].keys()))

        is_trap = nfmt == "decimal" and rng.random() < trap_ratio
        is_close = rng.random() < close_ratio

        if is_trap:
            a_val, b_val, a_str, b_str = self._make_decimal_trap(rng, max_dp)
        elif nfmt == "fraction":
            a_val, a_str = self._make_fraction(rng, frac_denom)
            b_val, b_str = self._make_fraction(rng, frac_denom)
            while a_val == b_val:
                b_val, b_str = self._make_fraction(rng, frac_denom)
        elif nfmt == "decimal":
            if is_close:
                a_val, b_val, a_str, b_str = self._make_close_decimals(rng, max_dp)
            else:
                a_val, a_str = self._make_decimal(rng, max_dp)
                b_val, b_str = self._make_decimal(rng, max_dp)
                while a_val == b_val:
                    b_val, b_str = self._make_decimal(rng, max_dp)
        else:  # integer
            if is_close:
                a_val = rng.randint(1, 10000)
                b_val = a_val + rng.choice([-1, 1])
                if b_val <= 0:
                    b_val = a_val + 1
            else:
                a_val = rng.randint(1, 10000)
                b_val = rng.randint(1, 10000)
                while b_val == a_val:
                    b_val = rng.randint(1, 10000)
            a_str, b_str = str(a_val), str(b_val)

        a_base = to_base(a_val, unit_key)
        b_base = to_base(b_val, unit_key)

        return self._finalize(
            a_str, unit_key, b_str, unit_key,
            a_base, b_base, a_val, b_val,
            cat, "same_unit", nfmt, is_trap, direction, order, rng,
        )

    # ---- mixed_unit --------------------------------------------------

    def _gen_mixed_unit(
        self, nfmt, direction, cats, trap_ratio, close_ratio, order, frac_denom, max_dp, rng,
    ) -> Dict[str, Any]:
        cat = rng.choice(cats)
        units_in_cat = list(UNITS[cat].keys())
        if len(units_in_cat) < 2:
            # fallback to same-unit if only one unit in category
            return self._gen_same_unit(
                nfmt, direction, cats, trap_ratio, close_ratio, order, frac_denom, max_dp, rng,
            )
        u1, u2 = rng.sample(units_in_cat, 2)

        is_trap = nfmt == "decimal" and rng.random() < trap_ratio

        if is_trap:
            a_val, b_raw, a_str, _ = self._make_decimal_trap(rng, max_dp)
            # Convert b to unit2 scale
            a_base = to_base(a_val, u1)
            b_base = a_base * rng.uniform(0.5, 2.0)  # different from a
            b_val = from_base(b_base, u2)
            b_str = self._format_value(b_val, nfmt, rng, max_dp, frac_denom)
        elif nfmt == "fraction":
            a_val, a_str = self._make_fraction(rng, frac_denom)
            b_val, b_str = self._make_fraction(rng, frac_denom)
        elif nfmt == "decimal":
            a_val, a_str = self._make_decimal(rng, max_dp)
            b_val, b_str = self._make_decimal(rng, max_dp)
        else:
            a_val = rng.randint(1, 1000)
            b_val = rng.randint(1, 1000)
            a_str, b_str = str(a_val), str(b_val)

        a_base = to_base(float(a_val), u1)
        b_base = to_base(float(b_val), u2)

        return self._finalize(
            a_str, u1, b_str, u2,
            a_base, b_base, float(a_val), float(b_val),
            cat, "mixed_unit", nfmt, is_trap, direction, order, rng,
        )

    # ---- equal -------------------------------------------------------

    def _gen_equal(self, nfmt, cats, frac_denom, max_dp, rng) -> Dict[str, Any]:
        # Filter EQUAL_PAIRS to those whose category is in cats
        valid = [
            p for p in EQUAL_PAIRS
            if _UNIT_CATEGORY[p[0]] in cats
        ]
        if not valid:
            valid = EQUAL_PAIRS

        u1, v1, u2, v2 = rng.choice(valid)
        # Optionally scale both by the same factor.
        # Skip scaling for temperature: conversion is affine, not
        # proportional, so multiplying both sides breaks equality.
        if _UNIT_CATEGORY[u1] != "temperature":
            scale = rng.choice([1, 2, 5, 10, 0.5, 0.1])
            v1 *= scale
            v2 *= scale

        cat = _UNIT_CATEGORY[u1]
        a_str = self._format_value(v1, nfmt, rng, max_dp, frac_denom)
        b_str = self._format_value(v2, nfmt, rng, max_dp, frac_denom)
        a_base = to_base(v1, u1)
        b_base = to_base(v2, u2)

        # Randomly swap display order
        if rng.random() < 0.5:
            a_str, b_str = b_str, a_str
            u1, u2 = u2, u1
            v1, v2 = v2, v1
            a_base, b_base = b_base, a_base

        return {
            "val1_str": a_str,
            "unit1_key": u1,
            "val2_str": b_str,
            "unit2_key": u2,
            "val1_base": a_base,
            "val2_base": b_base,
            "val1_numeric": v1,
            "val2_numeric": v2,
            "category": cat,
            "comparison_type": "equal",
            "number_format": nfmt,
            "is_decimal_trap": False,
            "correct_position": "equal",
            "expected_answer": "equal",
        }

    # ---- incomparable ------------------------------------------------

    def _gen_incomparable(self, nfmt, cats, frac_denom, max_dp, rng) -> Dict[str, Any]:
        if len(cats) < 2:
            # Need at least 2 categories — force an extra one
            all_cats = list(UNITS.keys())
            cats = list(set(cats + [rng.choice(all_cats)]))

        cat1, cat2 = rng.sample(cats, 2)
        u1 = rng.choice(list(UNITS[cat1].keys()))
        u2 = rng.choice(list(UNITS[cat2].keys()))

        a_val, a_str = self._make_value(nfmt, rng, max_dp, frac_denom)
        b_val, b_str = self._make_value(nfmt, rng, max_dp, frac_denom)

        return {
            "val1_str": a_str,
            "unit1_key": u1,
            "val2_str": b_str,
            "unit2_key": u2,
            "val1_base": to_base(a_val, u1),
            "val2_base": to_base(b_val, u2),
            "val1_numeric": a_val,
            "val2_numeric": b_val,
            "category": f"{cat1}+{cat2}",
            "comparison_type": "incomparable",
            "number_format": nfmt,
            "is_decimal_trap": False,
            "correct_position": "incomparable",
            "expected_answer": "incomparable",
        }

    # ------------------------------------------------------------------
    # Value generators
    # ------------------------------------------------------------------

    def _make_value(self, nfmt: str, rng, max_dp, frac_denom) -> Tuple[float, str]:
        """Generate a single value as (float, display_str)."""
        if nfmt == "fraction":
            return self._make_fraction(rng, frac_denom)
        elif nfmt == "decimal":
            return self._make_decimal(rng, max_dp)
        else:
            v = rng.randint(1, 10000)
            return float(v), str(v)

    @staticmethod
    def _make_decimal(rng: random.Random, max_dp: int) -> Tuple[float, str]:
        dp = rng.randint(1, max_dp)
        val = round(rng.uniform(0.01, 1000.0), dp)
        return val, f"{val:.{dp}f}"

    @staticmethod
    def _make_close_decimals(rng: random.Random, max_dp: int) -> Tuple[float, float, str, str]:
        """Two decimal values very close to each other."""
        dp = rng.randint(1, max_dp)
        base = round(rng.uniform(1.0, 100.0), dp)
        nudge = 10 ** (-dp)
        other = base + nudge * rng.choice([-1, 1])
        if other <= 0:
            other = base + nudge
        other = round(other, dp)
        if other == base:
            other = base + nudge
            other = round(other, dp)
        return base, other, f"{base:.{dp}f}", f"{other:.{dp}f}"

    @staticmethod
    def _make_decimal_trap(rng: random.Random, max_dp: int) -> Tuple[float, float, str, str]:
        """Adversarial pair: more digits ≠ bigger number.

        E.g. 0.11 (2 digits) vs 0.9 (1 digit) — the shorter one is bigger.
        """
        # The "big" value has fewer decimal places
        big_dp = rng.randint(1, max(1, max_dp - 1))
        big_val = round(rng.uniform(0.5, 10.0), big_dp)

        # The "small" value has more decimal places but is numerically smaller
        small_dp = big_dp + rng.randint(1, max(1, max_dp - big_dp))
        small_dp = min(small_dp, max_dp)
        small_val = round(rng.uniform(0.001, big_val * 0.8), small_dp)

        # Ensure they are actually different and the trap holds
        if small_val >= big_val:
            small_val = round(big_val * 0.5, small_dp)

        return big_val, small_val, f"{big_val:.{big_dp}f}", f"{small_val:.{small_dp}f}"

    @staticmethod
    def _make_fraction(rng: random.Random, max_denom: int) -> Tuple[float, str]:
        denom = rng.randint(2, max_denom)
        numer = rng.randint(1, denom * 4)  # allows improper fractions
        f = Fraction(numer, denom)
        return float(f), f"{f.numerator}/{f.denominator}"

    @staticmethod
    def _format_value(val: float, nfmt: str, rng, max_dp: int, frac_denom: int) -> str:
        """Format a numeric value according to the chosen number format."""
        if nfmt == "fraction":
            f = Fraction(val).limit_denominator(frac_denom)
            return f"{f.numerator}/{f.denominator}"
        elif nfmt == "decimal":
            dp = rng.randint(1, max_dp)
            return f"{val:.{dp}f}"
        else:
            if val == int(val):
                return str(int(val))
            return f"{val:g}"

    # ---- finalize / ordering -----------------------------------------

    def _finalize(
        self,
        a_str, u1, b_str, u2,
        a_base, b_base, a_numeric, b_numeric,
        cat, ctype, nfmt, is_trap, direction, order, rng,
    ) -> Dict[str, Any]:
        """Determine winner, apply ordering, return case dict."""
        # Determine which is actually bigger
        if a_base > b_base:
            bigger_idx = 0  # first
        elif b_base > a_base:
            bigger_idx = 1  # second
        else:
            # exactly equal — shouldn't happen in same/mixed but handle gracefully
            bigger_idx = 0

        # Apply value ordering
        if order == "bigger_first" and bigger_idx == 1:
            a_str, b_str = b_str, a_str
            u1, u2 = u2, u1
            a_base, b_base = b_base, a_base
            a_numeric, b_numeric = b_numeric, a_numeric
            bigger_idx = 0
        elif order == "smaller_first" and bigger_idx == 0:
            a_str, b_str = b_str, a_str
            u1, u2 = u2, u1
            a_base, b_base = b_base, a_base
            a_numeric, b_numeric = b_numeric, a_numeric
            bigger_idx = 1
        elif order == "random" and rng.random() < 0.5:
            a_str, b_str = b_str, a_str
            u1, u2 = u2, u1
            a_base, b_base = b_base, a_base
            a_numeric, b_numeric = b_numeric, a_numeric
            bigger_idx = 1 - bigger_idx

        # Determine correct position and expected answer based on direction
        if direction == "bigger":
            if bigger_idx == 0:
                correct_position = "first"
                expected = f"{a_str} {UNIT_SYMBOLS[u1]}"
            else:
                correct_position = "second"
                expected = f"{b_str} {UNIT_SYMBOLS[u2]}"
        else:  # smaller
            if bigger_idx == 0:
                correct_position = "second"
                expected = f"{b_str} {UNIT_SYMBOLS[u2]}"
            else:
                correct_position = "first"
                expected = f"{a_str} {UNIT_SYMBOLS[u1]}"

        return {
            "val1_str": a_str,
            "unit1_key": u1,
            "val2_str": b_str,
            "unit2_key": u2,
            "val1_base": a_base,
            "val2_base": b_base,
            "val1_numeric": a_numeric,
            "val2_numeric": b_numeric,
            "category": cat,
            "comparison_type": ctype,
            "number_format": nfmt,
            "is_decimal_trap": is_trap,
            "correct_position": correct_position,
            "expected_answer": expected,
        }

    # ------------------------------------------------------------------
    # Build TestCase
    # ------------------------------------------------------------------

    def _build_test_case(
        self,
        *,
        idx: int,
        seed: int | None,
        config_name: str,
        user_style: str,
        system_style: str,
        language: str,
        direction: str,
        case: Dict[str, Any],
        rng: random.Random,
    ) -> TestCase:
        cat = case["category"].split("+")[0]  # use first cat for word lookup
        comp_word = self._get_comp_word(language, cat, direction)

        u1_sym = UNIT_SYMBOLS[case["unit1_key"]]
        u2_sym = UNIT_SYMBOLS[case["unit2_key"]]

        templates = QUESTION_TEMPLATES.get(language, QUESTION_TEMPLATES["en"])
        template = rng.choice(templates)
        question = template.format(
            comp_word=comp_word,
            val1=case["val1_str"],
            unit1=u1_sym,
            val2=case["val2_str"],
            unit2=u2_sym,
        )

        user_templates = USER_PROMPT_TEMPLATES.get(language, USER_PROMPT_TEMPLATES["en"])
        user_template = user_templates.get(user_style, user_templates["casual"])
        user_prompt = user_template.format(question=question).strip()

        sys_prompts = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["en"])
        system_prompt = sys_prompts.get(system_style, sys_prompts["analytical"])

        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

        seed_label = seed if seed is not None else 0

        return TestCase(
            test_id=f"measure_comparison_{seed_label}_{idx:04d}",
            task_type="measure_comparison",
            config_name=config_name,
            prompts={
                "system": system_prompt,
                "user": user_prompt,
                "full": full_prompt,
            },
            task_params={
                "expected_answer": case["expected_answer"],
                "value1": case["val1_str"],
                "unit1": case["unit1_key"],
                "unit1_symbol": u1_sym,
                "value2": case["val2_str"],
                "unit2": case["unit2_key"],
                "unit2_symbol": u2_sym,
                "value1_base": case["val1_base"],
                "value2_base": case["val2_base"],
                "category": case["category"],
                "comparison_type": case["comparison_type"],
                "number_format": case["number_format"],
                "question_direction": direction,
                "correct_position": case["correct_position"],
                "is_decimal_trap": case["is_decimal_trap"],
            },
            prompt_metadata={
                "user_style": user_style,
                "system_style": system_style,
                "language": language,
            },
            generation_metadata={
                "seed": seed,
                "index": idx,
                "comparison_type": case["comparison_type"],
            },
        )

    @staticmethod
    def _get_comp_word(language: str, category: str, direction: str) -> str:
        lang_words = COMPARISON_WORDS.get(language, COMPARISON_WORDS["en"])
        cat_words = lang_words.get(category, lang_words["_generic"])
        return cat_words.get(direction, cat_words["bigger"])
