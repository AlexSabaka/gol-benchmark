"""
Measure Comparison Plugin – Comprehensive pytest test suite.

Covers: generator, parser, evaluator, plugin registration, and round-trip
integration.  Each comparison type, number format, unit category, and
edge case gets dedicated tests.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List

import pytest

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from src.plugins.measure_comparison.generator import (
    EQUAL_PAIRS,
    UNITS,
    UNIT_SYMBOLS,
    MeasureComparisonGenerator,
    _UNIT_CATEGORY,
    _to_kelvin,
    _from_kelvin,
    to_base,
    from_base,
)
from src.plugins.measure_comparison.parser import MeasureComparisonParser
from src.plugins.measure_comparison.evaluator import MeasureComparisonEvaluator
from src.plugins.base import TestCase, ParsedAnswer, EvaluationResult


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def gen():
    return MeasureComparisonGenerator()


@pytest.fixture
def parser():
    return MeasureComparisonParser()


@pytest.fixture
def evaluator():
    return MeasureComparisonEvaluator()


def _default_config(**overrides) -> Dict:
    cfg = {
        "number_format": "mixed",
        "comparison_type": "all",
        "unit_categories": list(UNITS.keys()),
        "language": "en",
    }
    cfg.update(overrides)
    return cfg


def _default_prompt_config(**overrides) -> Dict:
    cfg = {"user_style": "casual", "system_style": "analytical", "name": "test"}
    cfg.update(overrides)
    return cfg


# ===========================================================================
# Unit conversion helpers
# ===========================================================================

class TestTemperatureConversions:
    """Verify the temperature helper functions with known values."""

    @pytest.mark.parametrize("c,k", [
        (0, 273.15),
        (100, 373.15),
        (-40, 233.15),
        (37, 310.15),
    ])
    def test_c_to_kelvin(self, c, k):
        assert math.isclose(_to_kelvin(c, "C"), k, rel_tol=1e-9)

    @pytest.mark.parametrize("f,k", [
        (32, 273.15),
        (212, 373.15),
        (-40, 233.15),
    ])
    def test_f_to_kelvin(self, f, k):
        assert math.isclose(_to_kelvin(f, "F"), k, rel_tol=1e-6)

    def test_k_to_kelvin_identity(self):
        assert _to_kelvin(300.0, "K") == 300.0

    @pytest.mark.parametrize("k,unit,expected", [
        (273.15, "C", 0.0),
        (373.15, "C", 100.0),
        (273.15, "F", 32.0),
        (300.0, "K", 300.0),
    ])
    def test_from_kelvin(self, k, unit, expected):
        assert math.isclose(_from_kelvin(k, unit), expected, rel_tol=1e-6)

    def test_c_roundtrip(self):
        for c in [-40, 0, 37, 100]:
            assert math.isclose(_from_kelvin(_to_kelvin(c, "C"), "C"), c, rel_tol=1e-9)

    def test_f_roundtrip(self):
        for f in [-40, 32, 98.6, 212]:
            assert math.isclose(_from_kelvin(_to_kelvin(f, "F"), "F"), f, rel_tol=1e-9)


class TestLinearConversions:
    """Verify to_base / from_base for non-temperature units."""

    @pytest.mark.parametrize("value,unit,expected_base", [
        (1.0, "km", 1000.0),
        (1.0, "cm", 0.01),
        (1.0, "inch", 0.0254),
        (1.0, "kg", 1000.0),
        (1.0, "L", 1000.0),
        (1.0, "h", 3600.0),
        (60.0, "min", 3600.0),
    ])
    def test_to_base(self, value, unit, expected_base):
        assert math.isclose(to_base(value, unit), expected_base, rel_tol=1e-6)

    def test_roundtrip_all_linear_units(self):
        """to_base then from_base should yield the original value."""
        for cat, units in UNITS.items():
            if cat == "temperature":
                continue
            for ukey in units:
                val = 42.5
                assert math.isclose(from_base(to_base(val, ukey), ukey), val, rel_tol=1e-9)


class TestEqualPairsValidity:
    """Every EQUAL_PAIRS entry must have exactly matching base values."""

    def test_all_equal_pairs(self):
        for u1, v1, u2, v2 in EQUAL_PAIRS:
            b1 = to_base(v1, u1)
            b2 = to_base(v2, u2)
            assert math.isclose(b1, b2, rel_tol=1e-6), (
                f"EQUAL_PAIR ({u1},{v1},{u2},{v2}): base {b1} != {b2}"
            )


# ===========================================================================
# Generator tests
# ===========================================================================

class TestGeneratorBatch:
    """Test generate_batch with various configs."""

    def test_deterministic_with_seed(self, gen):
        # Exclude decimal type — it produces multiple cases per pair (approximate count)
        weights = {"same_unit": 0.4, "mixed_unit": 0.3, "equal": 0.15, "incomparable": 0.15}
        cfg = _default_config(count=10, type_weights=weights)
        pc = _default_prompt_config()
        a = gen.generate_batch(cfg, pc, count=10, seed=42)
        b = gen.generate_batch(cfg, pc, count=10, seed=42)
        assert len(a) == len(b) == 10
        for ta, tb in zip(a, b):
            assert ta.test_id == tb.test_id
            assert ta.task_params["expected_answer"] == tb.task_params["expected_answer"]

    def test_different_seeds_differ(self, gen):
        cfg = _default_config(count=20)
        pc = _default_prompt_config()
        a = gen.generate_batch(cfg, pc, count=20, seed=1)
        b = gen.generate_batch(cfg, pc, count=20, seed=2)
        answers_a = [tc.task_params["expected_answer"] for tc in a]
        answers_b = [tc.task_params["expected_answer"] for tc in b]
        assert answers_a != answers_b

    def test_batch_size_respected(self, gen):
        # Exclude decimal type — it produces multiple cases per pair (approximate count)
        weights = {"same_unit": 0.4, "mixed_unit": 0.3, "equal": 0.15, "incomparable": 0.15}
        for n in [1, 5, 50]:
            cfg = _default_config(type_weights=weights)
            pc = _default_prompt_config()
            cases = gen.generate_batch(cfg, pc, count=n, seed=99)
            assert len(cases) == n

    def test_all_cases_are_testcase_objects(self, gen):
        cases = gen.generate_batch(_default_config(), _default_prompt_config(), count=10, seed=7)
        for tc in cases:
            assert isinstance(tc, TestCase)
            assert tc.task_type == "measure_comparison"
            assert "expected_answer" in tc.task_params

    def test_test_ids_unique(self, gen):
        cases = gen.generate_batch(_default_config(), _default_prompt_config(), count=100, seed=0)
        ids = [tc.test_id for tc in cases]
        assert len(ids) == len(set(ids))


class TestGeneratorComparisonTypes:
    """Test each comparison type specifically."""

    def test_same_unit_only(self, gen):
        cfg = _default_config(comparison_type="same_unit")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["comparison_type"] == "same_unit"
            assert tc.task_params["unit1"] == tc.task_params["unit2"]

    def test_mixed_unit_only(self, gen):
        cfg = _default_config(comparison_type="mixed_unit")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["comparison_type"] == "mixed_unit"
            # Mixed means different units in the same category (usually)
            # They share a category
            cat = tc.task_params["category"]
            assert cat in UNITS

    def test_equal_only(self, gen):
        cfg = _default_config(comparison_type="equal")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["comparison_type"] == "equal"
            assert tc.task_params["expected_answer"] == "equal"
            assert tc.task_params["correct_position"] == "equal"

    def test_equal_base_values_match(self, gen):
        """Equal cases must have matching base values."""
        cfg = _default_config(comparison_type="equal")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=50, seed=42)
        for tc in cases:
            b1 = tc.task_params["value1_base"]
            b2 = tc.task_params["value2_base"]
            assert math.isclose(b1, b2, rel_tol=1e-6), (
                f"{tc.test_id}: base values {b1} vs {b2} should be equal"
            )

    def test_incomparable_only(self, gen):
        cfg = _default_config(comparison_type="incomparable")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["comparison_type"] == "incomparable"
            assert tc.task_params["expected_answer"] == "incomparable"
            assert tc.task_params["correct_position"] == "incomparable"
            # Units should be from different categories
            cat = tc.task_params["category"]
            assert "+" in cat  # incomparable uses "cat1+cat2" notation

    def test_all_type_distribution(self, gen):
        """Type 'all' should produce a mix of comparison types."""
        cfg = _default_config(comparison_type="all")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=200, seed=42)
        types_seen = {tc.task_params["comparison_type"] for tc in cases}
        assert "same_unit" in types_seen
        assert "mixed_unit" in types_seen
        assert "equal" in types_seen
        assert "incomparable" in types_seen


class TestGeneratorNumberFormats:
    """Verify number format selection."""

    def test_integer_format(self, gen):
        cfg = _default_config(comparison_type="same_unit", number_format="integer")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["number_format"] == "integer"

    def test_decimal_format(self, gen):
        cfg = _default_config(comparison_type="same_unit", number_format="decimal")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["number_format"] == "decimal"

    def test_fraction_format(self, gen):
        cfg = _default_config(comparison_type="same_unit", number_format="fraction")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["number_format"] == "fraction"
            # The value strings should contain '/'
            assert "/" in tc.task_params["value1"]
            assert "/" in tc.task_params["value2"]

    def test_mixed_format_produces_variety(self, gen):
        cfg = _default_config(comparison_type="same_unit", number_format="mixed")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=100, seed=42)
        formats = {tc.task_params["number_format"] for tc in cases}
        assert len(formats) >= 2  # at least 2 different formats


class TestGeneratorUnitCategories:
    """Verify unit category filtering."""

    def test_single_category(self, gen):
        cfg = _default_config(comparison_type="same_unit", unit_categories=["length"])
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["category"] == "length"

    def test_two_categories(self, gen):
        cfg = _default_config(comparison_type="same_unit", unit_categories=["mass", "time"])
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert tc.task_params["category"] in {"mass", "time"}

    def test_all_categories_appear(self, gen):
        cfg = _default_config(comparison_type="same_unit", unit_categories=list(UNITS.keys()))
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=300, seed=42)
        cats = {tc.task_params["category"] for tc in cases}
        assert cats == set(UNITS.keys())


class TestGeneratorCorrectness:
    """Verify generated correct answers are actually correct."""

    def test_same_unit_correct_answers(self, gen):
        """For same-unit, the bigger/smaller base value should match the answer."""
        cfg = _default_config(comparison_type="same_unit", question_direction="bigger")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=50, seed=42)
        for tc in cases:
            b1 = tc.task_params["value1_base"]
            b2 = tc.task_params["value2_base"]
            pos = tc.task_params["correct_position"]
            if b1 > b2:
                assert pos == "first"
            elif b2 > b1:
                assert pos == "second"

    def test_smaller_direction(self, gen):
        """With question_direction='smaller', correct = the smaller value."""
        cfg = _default_config(comparison_type="same_unit", question_direction="smaller")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=50, seed=42)
        for tc in cases:
            b1 = tc.task_params["value1_base"]
            b2 = tc.task_params["value2_base"]
            pos = tc.task_params["correct_position"]
            if b1 < b2:
                assert pos == "first"
            elif b2 < b1:
                assert pos == "second"

    def test_mixed_unit_base_conversion_consistent(self, gen):
        """For mixed_unit, base values should be consistent with value+unit."""
        cfg = _default_config(comparison_type="mixed_unit", number_format="integer")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=50, seed=42)
        for tc in cases:
            # Re-derive base from value and unit
            v1 = float(tc.task_params["value1"])
            u1 = tc.task_params["unit1"]
            expected_b1 = to_base(v1, u1)
            assert math.isclose(tc.task_params["value1_base"], expected_b1, rel_tol=1e-6)


class TestGeneratorDecimalTraps:
    """Decimal traps: 0.9 vs 0.85 where digit-count misleads."""

    def test_decimal_traps_produced(self, gen):
        cfg = _default_config(
            comparison_type="same_unit",
            number_format="decimal",
            decimal_trap_ratio=1.0,  # force all to be traps
        )
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=20, seed=42)
        trap_count = sum(1 for tc in cases if tc.task_params["is_decimal_trap"])
        assert trap_count > 0

    def test_no_traps_when_ratio_zero(self, gen):
        cfg = _default_config(
            comparison_type="same_unit",
            number_format="decimal",
            decimal_trap_ratio=0.0,
        )
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=30, seed=42)
        for tc in cases:
            assert not tc.task_params["is_decimal_trap"]


class TestGeneratorTemperatureEqualPairs:
    """Temperature equal pairs must not be broken by scaling."""

    def test_temperature_equal_no_scaling(self, gen):
        """Equal-type temperature cases should still have matching base values."""
        cfg = _default_config(
            comparison_type="equal",
            unit_categories=["temperature"],
        )
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=50, seed=42)
        for tc in cases:
            b1 = tc.task_params["value1_base"]
            b2 = tc.task_params["value2_base"]
            assert math.isclose(b1, b2, rel_tol=1e-6), (
                f"{tc.test_id}: temperature equal base {b1} vs {b2}"
            )


# ===========================================================================
# Prompt / language tests
# ===========================================================================

class TestLanguageSupport:
    """Ensure prompts are generated for all supported languages."""

    @pytest.mark.parametrize("lang", ["en", "es", "fr", "de", "zh", "ua"])
    def test_language_prompt_generated(self, gen, lang):
        cfg = _default_config(language=lang, comparison_type="same_unit")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=3, seed=42)
        for tc in cases:
            assert tc.prompts["user"], f"Empty user prompt for {lang}"
            assert tc.prompts["system"], f"Empty system prompt for {lang}"
            assert len(tc.prompts["user"]) > 10

    @pytest.mark.parametrize("user_style", ["minimal", "casual", "linguistic"])
    def test_user_styles(self, gen, user_style):
        cfg = _default_config(comparison_type="same_unit")
        pc = _default_prompt_config(user_style=user_style)
        cases = gen.generate_batch(cfg, pc, count=3, seed=42)
        for tc in cases:
            assert tc.prompts["user"]
            assert tc.prompt_metadata["user_style"] == user_style

    @pytest.mark.parametrize("sys_style", ["analytical", "casual", "adversarial"])
    def test_system_styles(self, gen, sys_style):
        cfg = _default_config(comparison_type="same_unit")
        pc = _default_prompt_config(system_style=sys_style)
        cases = gen.generate_batch(cfg, pc, count=3, seed=42)
        for tc in cases:
            assert tc.prompts["system"]
            assert tc.prompt_metadata["system_style"] == sys_style


# ===========================================================================
# Parser tests
# ===========================================================================

def _make_task_params(**overrides) -> Dict:
    """Make a typical normal-comparison task_params dict."""
    tp = {
        "value1": "10",
        "unit1_symbol": "cm",
        "value2": "5",
        "unit2_symbol": "cm",
        "comparison_type": "same_unit",
        "correct_position": "first",
        "expected_answer": "10 cm",
    }
    tp.update(overrides)
    return tp


class TestParserBoxed:
    """Strategy 1: \\boxed{...}"""

    def test_boxed_value_unit(self, parser):
        tp = _make_task_params()
        pa = parser.parse("The answer is \\boxed{10 cm}.", tp)
        assert pa.value == "10 cm"
        assert pa.parse_strategy == "boxed"
        assert pa.confidence == 0.95

    def test_boxed_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("\\boxed{equal}", tp)
        assert pa.value == "equal"
        assert pa.parse_strategy == "boxed"

    def test_boxed_incomparable(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse("\\boxed{cannot compare}", tp)
        assert pa.value == "incomparable"


class TestParserBold:
    """Strategy 2: **...**"""

    def test_bold_value_unit(self, parser):
        tp = _make_task_params()
        pa = parser.parse("The answer is **10 cm**.", tp)
        assert pa.value == "10 cm"
        assert pa.parse_strategy == "bold"
        assert pa.confidence == 0.90

    def test_bold_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("They are **equal**.", tp)
        assert pa.value == "equal"


class TestParserEqualKeywords:
    """Strategy 3: equal/same/equivalent keywords."""

    @pytest.mark.parametrize("text", [
        "They are equal.",
        "Both values are the same.",
        "These are equivalent amounts.",
        "There's no difference between them.",
    ])
    def test_en_equal_detected(self, parser, text):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse(text, tp)
        assert pa.value == "equal"
        assert pa.parse_strategy == "keyword_equal"

    def test_negated_equal_not_matched(self, parser):
        """'not equal' should NOT trigger keyword_equal."""
        tp = _make_task_params()
        pa = parser.parse("They are not equal. The answer is 10 cm.", tp)
        # Should use a later strategy, not keyword_equal
        assert pa.value != "equal" or pa.parse_strategy != "keyword_equal"


class TestParserIncomparableKeywords:
    """Strategy 4: incomparable keywords."""

    @pytest.mark.parametrize("text", [
        "These cannot be compared — different dimensions.",
        "You can't compare kilograms to meters!",
        "Incomparable units.",
        "It's impossible to compare temperature and mass.",
    ])
    def test_en_incomparable_detected(self, parser, text):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse(text, tp)
        assert pa.value == "incomparable"
        assert pa.parse_strategy == "keyword_incomparable"


class TestParserLabelLine:
    """Strategy 5: Answer: ..."""

    def test_answer_label(self, parser):
        tp = _make_task_params()
        pa = parser.parse("After analysis, Answer: 10 cm.", tp)
        assert pa.value == "10 cm"
        assert pa.parse_strategy == "label_line"

    def test_the_answer_is(self, parser):
        tp = _make_task_params()
        pa = parser.parse("Let me think... The answer is 10 cm.", tp)
        assert pa.value == "10 cm"
        assert pa.parse_strategy == "label_line"


class TestParserValueUnitMatch:
    """Strategy 6: value+unit extraction matching an option."""

    def test_match_first_option(self, parser):
        tp = _make_task_params()
        pa = parser.parse("I think 10 cm is bigger.", tp)
        assert pa.value == "10 cm"
        assert pa.parse_strategy in ("value_unit_match", "value_unit_comparative")

    def test_match_second_option(self, parser):
        tp = _make_task_params()
        pa = parser.parse("5 cm is smaller, but wait, 5 cm is the answer.", tp)
        assert pa.value == "5 cm"
        assert pa.parse_strategy in ("value_unit_match", "value_unit_comparative")

    def test_fraction_value(self, parser):
        tp = _make_task_params(
            value1="3/4", unit1_symbol="cup",
            value2="1/2", unit2_symbol="cup",
            expected_answer="3/4 cup",
        )
        pa = parser.parse("I think 3/4 cup is more.", tp)
        assert pa.value == "3/4 cup"

    def test_mph_unit(self, parser):
        tp = _make_task_params(
            value1="60", unit1_symbol="mph",
            value2="100", unit2_symbol="mph",
            expected_answer="100 mph",
        )
        pa = parser.parse("The second option, 100 mph.", tp)
        assert pa.value == "100 mph"


class TestParserPositionMatch:
    """Strategy 7: first/second keywords."""

    def test_first_keyword(self, parser):
        tp = _make_task_params()
        pa = parser.parse("The first one.", tp)
        assert pa.value == "10 cm"
        assert pa.parse_strategy == "position_match"

    def test_second_keyword(self, parser):
        tp = _make_task_params()
        pa = parser.parse("The second one.", tp)
        assert pa.value == "5 cm"
        assert pa.parse_strategy == "position_match"


class TestParserEmptyAndFallback:
    """Edge cases: empty response, unparseable."""

    def test_empty_response(self, parser):
        pa = parser.parse("", _make_task_params())
        assert pa.value is None
        assert pa.parse_strategy == "empty"
        assert pa.error

    def test_whitespace_only(self, parser):
        pa = parser.parse("   \n  ", _make_task_params())
        assert pa.value is None

    def test_completely_unparseable(self, parser):
        pa = parser.parse("I don't know.", _make_task_params())
        # Should reach fallback
        assert pa.confidence <= 0.65  # last_value_unit or fallback


class TestParserMultilingual:
    """Keywords in non-English languages."""

    def test_spanish_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("Los valores son iguales.", tp)
        assert pa.value == "equal"

    def test_french_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("Ce sont les mêmes valeurs.", tp)
        assert pa.value == "equal"

    def test_german_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("Die Werte sind gleich.", tp)
        assert pa.value == "equal"

    def test_chinese_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("这两个值相等。", tp)
        assert pa.value == "equal"

    def test_ukrainian_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("Ці значення однакові.", tp)
        assert pa.value == "equal"

    def test_spanish_incomparable(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse("No se pueden comparar estas cantidades.", tp)
        assert pa.value == "incomparable"

    def test_german_incomparable(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse("Diese Werte sind nicht vergleichbar.", tp)
        assert pa.value == "incomparable"

    def test_chinese_incomparable(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse("无法比较这两个量。", tp)
        assert pa.value == "incomparable"


# ===========================================================================
# False-negative regression tests (v2.10.5)
# ===========================================================================

class TestParserSmartQuotes:
    """Fix 1: Smart/curly quotes must not break keyword detection."""

    def test_incomparable_curly_apostrophe(self, parser):
        tp = _make_task_params(
            value1="755.8", unit1_symbol="lb",
            value2="152.8", unit2_symbol="min",
            comparison_type="incomparable",
        )
        pa = parser.parse(
            "They can\u2019t be compared \u2013 one is a weight (lb) "
            "and the other a time (min).",
            tp,
        )
        assert pa.value == "incomparable"

    def test_incomparable_curly_cant_be_directly(self, parser):
        tp = _make_task_params(
            value1="580.44", unit1_symbol="mL",
            value2="358.82", unit2_symbol="km/h",
            comparison_type="incomparable",
        )
        pa = parser.parse(
            "They\u2019re different kinds of units, so you can\u2019t "
            "directly compare them.",
            tp,
        )
        assert pa.value == "incomparable"

    def test_arent_comparable_curly(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse("These aren\u2019t comparable.", tp)
        assert pa.value == "incomparable"


class TestParserEqualKeywordContext:
    """Fix 2: 'same' in explanatory context must NOT trigger 'equal'."""

    def test_same_unit_explanatory(self, parser):
        """'the same unit' in explanation, value in conclusion."""
        tp = _make_task_params(
            value1="87.761", unit1_symbol="ft",
            value2="87.760", unit2_symbol="ft",
            expected_answer="87.761 ft",
        )
        pa = parser.parse(
            "Since both numbers share the same whole number part, "
            "87.761 feet is longer. **Answer:** 87.761 ft.",
            tp,
        )
        assert pa.value == "87.761 ft"
        assert pa.value != "equal"

    def test_convert_to_same_unit(self, parser):
        """'convert to the same unit' should not trigger equal."""
        tp = _make_task_params(
            value1="332", unit1_symbol="mg",
            value2="614", unit2_symbol="lb",
            expected_answer="332 mg",
        )
        pa = parser.parse(
            "Let's convert both quantities to the same unit. "
            "332 mg = 0.332 g, 614 lb = 278950 g. "
            "Clearly, 0.332 g is lighter. Answer: 332 mg",
            tp,
        )
        assert pa.value == "332 mg"

    def test_genuine_equal_still_works(self, parser):
        """Genuine 'equal' answers must still parse correctly."""
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("They are the same.", tp)
        assert pa.value == "equal"

    def test_genuine_both_equal(self, parser):
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse("Both values are the same.", tp)
        assert pa.value == "equal"

    def test_neither_is_shorter(self, parser):
        """'Neither is shorter' pattern for equal values."""
        tp = _make_task_params(comparison_type="equal")
        pa = parser.parse(
            "Neither is shorter — they are exactly equal.",
            tp,
        )
        assert pa.value == "equal"


class TestParserBoldIteration:
    """Fix 3: Bold iteration should find answer keyword, not last value."""

    def test_bold_equal_then_value(self, parser):
        """Equal keyword in earlier bold, value in later bold."""
        tp = _make_task_params(
            value1="880/1", unit1_symbol="yd",
            value2="1/2", unit2_symbol="mi",
            comparison_type="equal",
        )
        pa = parser.parse(
            "They are **exactly the same distance**.\n\n"
            "1 mile = 1,760 yards.\nTherefore, 1/2 mile = **880 yards**.",
            tp,
        )
        assert pa.value == "equal"

    def test_bold_equal_then_conversion(self, parser):
        tp = _make_task_params(
            value1="500/1", unit1_symbol="mL",
            value2="1/2", unit2_symbol="L",
            comparison_type="equal",
        )
        pa = parser.parse(
            "They are **equal**.\n\n0.5 Liters = **500 mL**.",
            tp,
        )
        assert pa.value == "equal"

    def test_bold_temp_equal(self, parser):
        tp = _make_task_params(
            value1="0.00", unit1_symbol="°C",
            value2="32.00", unit2_symbol="°F",
            comparison_type="equal",
        )
        pa = parser.parse(
            "Let's convert both temperatures to the same unit "
            "(Celsius) to compare them.\n\n"
            "*   **32.00 °F to °C:**  °C = (°F - 32) * 5/9\n"
            "    °C = (32 - 32) * 5/9 = 0 * 5/9 = 0 °C\n\n"
            "Now we can compare:\n\n"
            "*   0.00 °C vs 0.00 °C\n\n"
            "They are equal.\n\nAnswer: equal",
            tp,
        )
        assert pa.value == "equal"


class TestParserExpandedIncomparable:
    """Fix 4: Expanded incomparable patterns."""

    def test_different_kinds_of_units(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse(
            "These are different kinds of units — one is volume, "
            "the other is speed.",
            tp,
        )
        assert pa.value == "incomparable"

    def test_measure_different_things(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse("They measure different things entirely.", tp)
        assert pa.value == "incomparable"

    def test_different_types_of_measurements(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse(
            "You're comparing different types of measurements.", tp)
        assert pa.value == "incomparable"

    def test_not_meaningful_comparison(self, parser):
        tp = _make_task_params(comparison_type="incomparable")
        pa = parser.parse(
            "This is not a meaningful comparison.", tp)
        assert pa.value == "incomparable"

    def test_incomparable_with_value_mentions(self, parser):
        """Incomparable even when values are mentioned in explanation."""
        tp = _make_task_params(
            value1="9782", unit1_symbol="s",
            value2="1305", unit2_symbol="mph",
            comparison_type="incomparable",
        )
        pa = parser.parse(
            "These are different kinds of units:\n"
            "- 9782 s = time\n"
            "- 1305 mph = speed\n\n"
            "So asking which is 'longer' doesn't make sense.",
            tp,
        )
        assert pa.value == "incomparable"


class TestParserReverseComparative:
    """Fix 5: 'the lighter one is X' reverse comparative pattern."""

    def test_lighter_one_is(self, parser):
        tp = _make_task_params(
            value1="758.337", unit1_symbol="oz",
            value2="609.413", unit2_symbol="kg",
            expected_answer="758.337 oz",
        )
        pa = parser.parse(
            "609.413 kg is much heavier.\n\n"
            "Quick conversion: 758.337 oz ≈ 21.5 kg.\n\n"
            "Therefore, the lighter one is 758.337 oz.",
            tp,
        )
        assert pa.value == "758.337 oz"


class TestParserBareValue:
    """Fix 6: Bare value match when model omits the unit."""

    def test_bare_number_answer(self, parser):
        tp = _make_task_params(
            value1="2.73", unit1_symbol="s",
            value2="0.699", unit2_symbol="s",
            expected_answer="0.699 s",
        )
        pa = parser.parse(
            "0.699 is shorter than 2.73.\n\n**Answer: 0.699**\n",
            tp,
        )
        assert pa.value == "0.699 s"


# ===========================================================================
# Evaluator tests
# ===========================================================================

class TestEvaluatorNormal:
    """Normal comparison: correct / wrong."""

    def test_correct_exact(self, evaluator):
        pa = ParsedAnswer(value="10 cm", raw_response="10 cm", parse_strategy="boxed", confidence=0.95)
        tp = _make_task_params()
        result = evaluator.evaluate(pa, "10 cm", tp)
        assert result.correct is True
        assert result.match_type == "correct"

    def test_wrong_answer(self, evaluator):
        pa = ParsedAnswer(value="5 cm", raw_response="5 cm", parse_strategy="boxed", confidence=0.95)
        tp = _make_task_params()
        result = evaluator.evaluate(pa, "10 cm", tp)
        assert result.correct is False
        assert result.match_type == "wrong"

    def test_correct_no_space(self, evaluator):
        """Match should work even with spacing differences."""
        pa = ParsedAnswer(value="10cm", raw_response="10cm", parse_strategy="boxed", confidence=0.95)
        tp = _make_task_params()
        result = evaluator.evaluate(pa, "10 cm", tp)
        assert result.correct is True

    def test_parse_error(self, evaluator):
        pa = ParsedAnswer(value=None, raw_response="gibberish", parse_strategy="fallback", confidence=0.1, error="no parse")
        tp = _make_task_params()
        result = evaluator.evaluate(pa, "10 cm", tp)
        assert result.correct is False
        assert result.match_type == "parse_error"


class TestEvaluatorEqual:
    """Equal trick: model must say 'equal'."""

    def test_correct_equal(self, evaluator):
        pa = ParsedAnswer(value="equal", raw_response="equal", parse_strategy="keyword_equal", confidence=0.9)
        tp = _make_task_params(comparison_type="equal")
        result = evaluator.evaluate(pa, "equal", tp)
        assert result.correct is True
        assert result.match_type == "correct_equal"

    def test_missed_equal(self, evaluator):
        pa = ParsedAnswer(value="10 cm", raw_response="10 cm", parse_strategy="boxed", confidence=0.9)
        tp = _make_task_params(comparison_type="equal")
        result = evaluator.evaluate(pa, "equal", tp)
        assert result.correct is False
        assert result.match_type == "missed_equal"

    def test_missed_equal_parse_error(self, evaluator):
        pa = ParsedAnswer(value=None, raw_response="", parse_strategy="empty", confidence=0.0, error="empty")
        tp = _make_task_params(comparison_type="equal")
        result = evaluator.evaluate(pa, "equal", tp)
        assert result.correct is False
        assert result.match_type == "missed_equal"


class TestEvaluatorIncomparable:
    """Incomparable trick: model must say 'incomparable' or similar."""

    def test_correct_incomparable(self, evaluator):
        pa = ParsedAnswer(value="incomparable", raw_response="cannot compare", parse_strategy="keyword_incomparable", confidence=0.9)
        tp = _make_task_params(comparison_type="incomparable")
        result = evaluator.evaluate(pa, "incomparable", tp)
        assert result.correct is True
        assert result.match_type == "correct_incomparable"

    def test_missed_incomparable(self, evaluator):
        pa = ParsedAnswer(value="10 cm", raw_response="10 cm", parse_strategy="boxed", confidence=0.9)
        tp = _make_task_params(comparison_type="incomparable")
        result = evaluator.evaluate(pa, "incomparable", tp)
        assert result.correct is False
        assert result.match_type == "missed_incomparable"

    def test_missed_incomparable_parse_error(self, evaluator):
        pa = ParsedAnswer(value=None, raw_response="", parse_strategy="empty", confidence=0.0, error="empty")
        tp = _make_task_params(comparison_type="incomparable")
        result = evaluator.evaluate(pa, "incomparable", tp)
        assert result.correct is False
        assert result.match_type == "missed_incomparable"


class TestEvaluatorAggregate:
    """Test aggregate_results breakdowns."""

    def test_aggregate_with_mix(self, evaluator):
        results = [
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0,
                             details={"comparison_type": "same_unit", "number_format": "integer",
                                      "category": "length", "is_decimal_trap": False,
                                      "correct_position": "first", "predicted": "10 cm",
                                      "value1": "10", "unit1_symbol": "cm",
                                      "value2": "5", "unit2_symbol": "cm"}),
            EvaluationResult(correct=False, match_type="wrong", accuracy=0.0,
                             details={"comparison_type": "same_unit", "number_format": "decimal",
                                      "category": "mass", "is_decimal_trap": True,
                                      "correct_position": "second", "predicted": "1 kg",
                                      "value1": "1", "unit1_symbol": "kg",
                                      "value2": "2", "unit2_symbol": "kg"}),
            EvaluationResult(correct=True, match_type="correct_equal", accuracy=1.0,
                             details={"comparison_type": "equal", "number_format": "integer",
                                      "category": "length", "is_decimal_trap": False,
                                      "correct_position": "equal", "predicted": "equal",
                                      "value1": "1", "unit1_symbol": "km",
                                      "value2": "1000", "unit2_symbol": "m"}),
        ]
        agg = evaluator.aggregate_results(results)
        assert agg["total"] == 3
        assert agg["correct"] == 2
        assert "comparison_type_breakdown" in agg
        assert "same_unit" in agg["comparison_type_breakdown"]
        assert "equal" in agg["comparison_type_breakdown"]
        assert "number_format_breakdown" in agg
        assert "category_breakdown" in agg
        assert "decimal_trap_accuracy" in agg
        assert agg["decimal_trap_total"] == 1
        assert agg["decimal_trap_accuracy"] == 0.0  # the trap case was wrong


# ===========================================================================
# Plugin registration
# ===========================================================================

class TestPluginRegistration:
    """Verify the plugin is discoverable by the registry."""

    def test_plugin_import(self):
        from src.plugins.measure_comparison import plugin
        assert plugin.task_type == "measure_comparison"
        assert plugin.display_name == "Measure Comparison"

    def test_plugin_in_registry(self):
        from src.plugins import PluginRegistry
        p = PluginRegistry.get("measure_comparison")
        assert p is not None
        assert p.task_type == "measure_comparison"

    def test_plugin_components(self):
        from src.plugins.measure_comparison import plugin
        assert isinstance(plugin.get_generator(), MeasureComparisonGenerator)
        assert isinstance(plugin.get_parser(), MeasureComparisonParser)
        assert isinstance(plugin.get_evaluator(), MeasureComparisonEvaluator)


# ===========================================================================
# Round-trip integration
# ===========================================================================

class TestRoundTrip:
    """Generate → parse simulated response → evaluate."""

    def test_correct_roundtrip_same_unit(self, gen, parser, evaluator):
        cfg = _default_config(comparison_type="same_unit")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=20, seed=99)
        for tc in cases:
            expected = tc.task_params["expected_answer"]
            # Simulate a model returning the correct answer
            response = f"The answer is \\boxed{{{expected}}}."
            pa = parser.parse(response, tc.task_params)
            result = evaluator.evaluate(pa, expected, tc.task_params)
            assert result.correct, f"{tc.test_id}: expected correct for '{expected}', got {result.match_type}"

    def test_correct_roundtrip_equal(self, gen, parser, evaluator):
        cfg = _default_config(comparison_type="equal")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=20, seed=99)
        for tc in cases:
            response = "Both values are equal."
            pa = parser.parse(response, tc.task_params)
            result = evaluator.evaluate(pa, "equal", tc.task_params)
            assert result.correct, f"{tc.test_id}: expected correct_equal"
            assert result.match_type == "correct_equal"

    def test_correct_roundtrip_incomparable(self, gen, parser, evaluator):
        cfg = _default_config(comparison_type="incomparable")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=20, seed=99)
        for tc in cases:
            response = "These cannot be compared."
            pa = parser.parse(response, tc.task_params)
            result = evaluator.evaluate(pa, "incomparable", tc.task_params)
            assert result.correct, f"{tc.test_id}: expected correct_incomparable"
            assert result.match_type == "correct_incomparable"

    def test_wrong_roundtrip(self, gen, parser, evaluator):
        cfg = _default_config(comparison_type="same_unit")
        cases = gen.generate_batch(cfg, _default_prompt_config(), count=10, seed=99)
        for tc in cases:
            # Give the wrong answer: pick the non-correct option
            pos = tc.task_params["correct_position"]
            if pos == "first":
                wrong = f"{tc.task_params['value2']} {tc.task_params['unit2_symbol']}"
            else:
                wrong = f"{tc.task_params['value1']} {tc.task_params['unit1_symbol']}"
            response = f"\\boxed{{{wrong}}}"
            pa = parser.parse(response, tc.task_params)
            expected = tc.task_params["expected_answer"]
            result = evaluator.evaluate(pa, expected, tc.task_params)
            assert not result.correct, f"{tc.test_id}: expected wrong for '{wrong}'"
