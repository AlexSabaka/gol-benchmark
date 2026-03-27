"""
Tests for the decimal-framing comparison type in measure_comparison plugin.

Covers:
  - Adversarial and control pair generation
  - Version-compare helper
  - Framing template completeness
  - Full generate_batch integration
  - Decimal-specific parsing
  - Decimal evaluation
  - Framing-sensitivity aggregate metric
"""
from __future__ import annotations

import random
import pytest

from src.plugins.measure_comparison.generator import (
    MeasureComparisonGenerator,
    DECIMAL_FRAMING_TEMPLATES,
    DECIMAL_COMP_WORDS,
)
from src.plugins.measure_comparison.parser import MeasureComparisonParser
from src.plugins.measure_comparison.evaluator import MeasureComparisonEvaluator
from src.plugins.base import ParsedAnswer, EvaluationResult


# =========================================================================
# Pair Generation & Helpers
# =========================================================================

class TestVersionCompare:
    """Unit tests for the _version_compare helper."""

    gen = MeasureComparisonGenerator()

    def test_equal(self):
        assert self.gen._version_compare("1.0", "1.0") == 0

    def test_a_bigger_minor(self):
        assert self.gen._version_compare("9.11", "9.9") == 1

    def test_b_bigger_minor(self):
        assert self.gen._version_compare("9.9", "9.11") == -1

    def test_a_bigger_major(self):
        assert self.gen._version_compare("10.1", "9.99") == 1

    def test_longer_wins(self):
        # "1.0.1" > "1.0" because extra component
        assert self.gen._version_compare("1.0.1", "1.0") == 1


class TestAdversarialPairGeneration:
    """Verify adversarial pairs have conflicting decimal vs version order."""

    gen = MeasureComparisonGenerator()

    def test_basic_invariant(self):
        """Decimal winner != version winner for adversarial pairs."""
        rng = random.Random(42)
        for _ in range(50):
            a_str, b_str, a_float, b_float = self.gen._make_adversarial_decimal_pair(rng)
            # a_float > b_float (a wins as decimal)
            assert a_float > b_float, f"{a_str} should be > {b_str} as decimal"
            # b wins as version (b has higher minor component)
            vcmp = self.gen._version_compare(a_str, b_str)
            assert vcmp < 0, (
                f"Version compare should say {b_str} > {a_str}, got {vcmp}"
            )

    def test_same_integer_part(self):
        """Both values share the same integer part."""
        rng = random.Random(123)
        for _ in range(20):
            a_str, b_str, _, _ = self.gen._make_adversarial_decimal_pair(rng)
            a_int = a_str.split(".")[0]
            b_int = b_str.split(".")[0]
            assert a_int == b_int


class TestControlPairGeneration:
    """Verify control pairs agree across both interpretations."""

    gen = MeasureComparisonGenerator()

    def test_both_orderings_agree(self):
        """Decimal and version order should agree for control pairs."""
        rng = random.Random(42)
        for _ in range(50):
            a_str, b_str, a_float, b_float = self.gen._make_control_decimal_pair(rng)
            assert a_float > b_float, f"{a_str} should be > {b_str} as decimal"
            vcmp = self.gen._version_compare(a_str, b_str)
            assert vcmp > 0, (
                f"Version compare should also say {a_str} > {b_str}, got {vcmp}"
            )


# =========================================================================
# Framing Templates
# =========================================================================

class TestDecimalFramingTemplates:
    """Verify template structure and completeness."""

    def test_en_has_all_framings(self):
        assert set(DECIMAL_FRAMING_TEMPLATES["en"].keys()) == {
            "neutral", "decimal", "version", "date",
        }

    def test_each_framing_has_templates(self):
        for framing, templates in DECIMAL_FRAMING_TEMPLATES["en"].items():
            assert len(templates) >= 2, f"{framing} should have ≥2 templates"

    def test_templates_have_placeholders(self):
        for framing, templates in DECIMAL_FRAMING_TEMPLATES["en"].items():
            for t in templates:
                assert "{val1}" in t, f"Missing {{val1}} in {framing}: {t}"
                assert "{val2}" in t, f"Missing {{val2}} in {framing}: {t}"

    def test_comp_words_match_framings(self):
        for framing in DECIMAL_FRAMING_TEMPLATES["en"]:
            assert framing in DECIMAL_COMP_WORDS["en"], (
                f"Missing comp words for {framing}"
            )


# =========================================================================
# Generator Integration
# =========================================================================

class TestDecimalGeneration:
    """Integration tests for generate_batch with comparison_type='decimal'."""

    gen = MeasureComparisonGenerator()

    def _generate(self, count=5, seed=42, framings=None, adversarial_ratio=0.6):
        config = {
            "comparison_type": "decimal",
            "decimal_framings": framings or ["neutral", "decimal", "version", "date"],
            "decimal_adversarial_ratio": adversarial_ratio,
        }
        prompt_config = {"user_style": "minimal", "system_style": "analytical"}
        return self.gen.generate_batch(config, prompt_config, count, seed=seed)

    def test_case_count(self):
        """count=5, 4 framings → 20 test cases."""
        cases = self._generate(count=5)
        assert len(cases) == 20

    def test_fewer_framings(self):
        """count=5, 2 framings → 10 test cases."""
        cases = self._generate(count=5, framings=["neutral", "version"])
        assert len(cases) == 10

    def test_all_decimal_type(self):
        """Every case should be comparison_type='decimal'."""
        cases = self._generate(count=3)
        for tc in cases:
            assert tc.task_params["comparison_type"] == "decimal"

    def test_framing_group_integrity(self):
        """Each framing group has exactly len(framings) cases with same pair."""
        cases = self._generate(count=5)
        groups = {}
        for tc in cases:
            gid = tc.task_params["framing_group_id"]
            groups.setdefault(gid, []).append(tc)

        assert len(groups) == 5
        for gid, group in groups.items():
            assert len(group) == 4  # 4 framings
            v1s = {tc.task_params["value1"] for tc in group}
            v2s = {tc.task_params["value2"] for tc in group}
            assert len(v1s) == 1, "All framings should share same val1"
            assert len(v2s) == 1, "All framings should share same val2"

    def test_adversarial_pairs_differ_across_framings(self):
        """For adversarial pairs, neutral/decimal and version/date should have different answers."""
        cases = self._generate(count=20, adversarial_ratio=1.0, seed=99)
        groups = {}
        for tc in cases:
            gid = tc.task_params["framing_group_id"]
            groups.setdefault(gid, []).append(tc)

        for gid, group in groups.items():
            answers_by_framing = {
                tc.task_params["framing"]: tc.task_params["expected_answer"]
                for tc in group
            }
            # neutral and decimal should agree
            assert answers_by_framing["neutral"] == answers_by_framing["decimal"]
            # version and date should agree
            assert answers_by_framing["version"] == answers_by_framing["date"]
            # But the two groups should differ
            assert answers_by_framing["neutral"] != answers_by_framing["version"], (
                f"Adversarial pair should have different answers: {answers_by_framing}"
            )

    def test_control_pairs_agree(self):
        """For control pairs, all framings should have the same answer."""
        cases = self._generate(count=20, adversarial_ratio=0.0, seed=99)
        groups = {}
        for tc in cases:
            gid = tc.task_params["framing_group_id"]
            groups.setdefault(gid, []).append(tc)

        for gid, group in groups.items():
            answers = {tc.task_params["expected_answer"] for tc in group}
            assert len(answers) == 1, (
                f"Control pair should agree across framings: {answers}"
            )

    def test_seed_reproducibility(self):
        """Same seed → identical test cases."""
        a = self._generate(count=3, seed=42)
        b = self._generate(count=3, seed=42)
        assert len(a) == len(b)
        for tc_a, tc_b in zip(a, b):
            assert tc_a.test_id == tc_b.test_id
            assert tc_a.task_params == tc_b.task_params

    def test_unique_test_ids(self):
        """All test IDs should be unique."""
        cases = self._generate(count=10)
        ids = [tc.test_id for tc in cases]
        assert len(ids) == len(set(ids))

    def test_prompts_vary_by_framing(self):
        """Prompt text should differ across framings within a group."""
        cases = self._generate(count=1)
        prompts = [tc.prompts["user"] for tc in cases]
        assert len(set(prompts)) > 1, "Different framings should produce different prompts"

    def test_no_unit_symbols(self):
        """Decimal cases should have empty unit symbols."""
        cases = self._generate(count=3)
        for tc in cases:
            assert tc.task_params["unit1_symbol"] == ""
            assert tc.task_params["unit2_symbol"] == ""
            assert tc.task_params["unit1"] == ""
            assert tc.task_params["unit2"] == ""


# =========================================================================
# Parser
# =========================================================================

class TestDecimalParsing:
    """Tests for decimal-specific response parsing."""

    parser = MeasureComparisonParser()

    def _tp(self, v1="9.9", v2="9.11"):
        return {
            "comparison_type": "decimal",
            "value1": v1,
            "value2": v2,
            "unit1_symbol": "",
            "unit2_symbol": "",
        }

    def test_direct_match(self):
        result = self.parser.parse("9.9", self._tp())
        assert result.value == "9.9"

    def test_boxed(self):
        result = self.parser.parse(r"The answer is \boxed{9.11}", self._tp())
        assert result.value == "9.11"
        assert result.parse_strategy == "decimal_boxed"

    def test_bold(self):
        result = self.parser.parse("The bigger value is **9.9**.", self._tp())
        assert result.value == "9.9"
        assert result.parse_strategy == "decimal_bold"

    def test_label_line(self):
        result = self.parser.parse("Thinking...\nAnswer: 9.11", self._tp())
        assert result.value == "9.11"
        assert "decimal_" in result.parse_strategy

    def test_value_in_sentence(self):
        result = self.parser.parse(
            "As a decimal number, 9.9 is greater than 9.11 because ...",
            self._tp(),
        )
        # End-first: should pick the last bare match
        assert result.value in ("9.9", "9.11")

    def test_position_keyword(self):
        result = self.parser.parse("The first one is bigger.", self._tp())
        assert result.value == "9.9"
        assert result.parse_strategy == "decimal_position"

    def test_fallback_on_garbage(self):
        result = self.parser.parse("I have no idea what you're asking.", self._tp())
        assert result.value is None
        assert result.error is not None

    def test_float_normalization(self):
        """'9.90' should match '9.9'."""
        result = self.parser.parse(r"\boxed{9.90}", self._tp())
        assert result.value == "9.9"


# =========================================================================
# Evaluator
# =========================================================================

class TestDecimalEvaluation:
    """Tests for decimal evaluation path."""

    evaluator = MeasureComparisonEvaluator()

    def _eval(self, predicted, expected, framing="neutral", is_adversarial=False, gid="g1"):
        pa = ParsedAnswer(
            value=predicted, raw_response=predicted or "",
            parse_strategy="test", confidence=0.9,
        )
        tp = {
            "comparison_type": "decimal",
            "framing": framing,
            "framing_group_id": gid,
            "is_adversarial": is_adversarial,
            "value1": "9.9",
            "value2": "9.11",
        }
        return self.evaluator.evaluate(pa, expected, tp)

    def test_correct(self):
        r = self._eval("9.9", "9.9")
        assert r.correct
        assert r.match_type == "correct"

    def test_wrong(self):
        r = self._eval("9.11", "9.9")
        assert not r.correct
        assert r.match_type == "wrong"

    def test_float_normalization(self):
        r = self._eval("9.90", "9.9")
        assert r.correct

    def test_details_include_framing(self):
        r = self._eval("9.9", "9.9", framing="version", is_adversarial=True, gid="fg_42_0001")
        assert r.details["framing"] == "version"
        assert r.details["framing_group_id"] == "fg_42_0001"
        assert r.details["is_adversarial"] is True

    def test_parse_error(self):
        pa = ParsedAnswer(
            value=None, raw_response="gibberish",
            parse_strategy="fallback", confidence=0.1,
            error="Could not parse",
        )
        tp = {"comparison_type": "decimal"}
        r = self.evaluator.evaluate(pa, "9.9", tp)
        assert not r.correct
        assert r.match_type == "parse_error"


# =========================================================================
# Framing-Sensitivity Metric
# =========================================================================

class TestFramingSensitivity:
    """Tests for the framing_analysis section in aggregate_results."""

    evaluator = MeasureComparisonEvaluator()

    def _make_result(
        self, correct, predicted, expected, framing, gid, is_adversarial,
    ) -> EvaluationResult:
        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details={
                "predicted": predicted,
                "expected": expected,
                "comparison_type": "decimal",
                "framing": framing,
                "framing_group_id": gid,
                "is_adversarial": is_adversarial,
                "value1": "9.9",
                "value2": "9.11",
                "unit1": "",
                "unit2": "",
                "unit1_symbol": "",
                "unit2_symbol": "",
                "category": "decimal",
                "number_format": "decimal",
                "question_direction": "bigger",
                "correct_position": "first",
                "is_decimal_trap": is_adversarial,
                "parse_strategy": "test",
                "confidence": 0.9,
            },
        )

    def test_sensitivity_zero_when_model_always_same(self):
        """Model always says 9.9 regardless of framing → sensitivity = 0."""
        results = []
        for framing in ["neutral", "decimal", "version", "date"]:
            # For neutral/decimal, 9.9 is correct; for version/date, 9.11 is correct
            correct = framing in ("neutral", "decimal")
            results.append(self._make_result(
                correct=correct, predicted="9.9",
                expected="9.9" if correct else "9.11",
                framing=framing, gid="g1", is_adversarial=True,
            ))

        agg = self.evaluator.aggregate_results(results)
        fa = agg["framing_analysis"]
        assert fa["adversarial_groups"] == 1
        assert fa["framing_sensitivity_rate"] == 0.0  # didn't vary answer
        assert fa["adversarial_perfect_rate"] == 0.0  # got version/date wrong

    def test_sensitivity_one_when_model_varies(self):
        """Model correctly adapts answer per framing → sensitivity = 1."""
        results = []
        for framing in ["neutral", "decimal", "version", "date"]:
            if framing in ("neutral", "decimal"):
                predicted, expected = "9.9", "9.9"
            else:
                predicted, expected = "9.11", "9.11"
            results.append(self._make_result(
                correct=True, predicted=predicted, expected=expected,
                framing=framing, gid="g1", is_adversarial=True,
            ))

        agg = self.evaluator.aggregate_results(results)
        fa = agg["framing_analysis"]
        assert fa["framing_sensitivity_rate"] == 1.0
        assert fa["adversarial_perfect_rate"] == 1.0
        assert fa["perfect_group_rate"] == 1.0

    def test_framing_accuracy_by_type(self):
        """Check per-framing accuracy breakdown."""
        results = []
        # Two groups: one adversarial (g1), one control (g2)
        # g1: model always says 9.9
        for framing in ["neutral", "decimal", "version", "date"]:
            correct = framing in ("neutral", "decimal")
            results.append(self._make_result(
                correct=correct, predicted="9.9",
                expected="9.9" if correct else "9.11",
                framing=framing, gid="g1", is_adversarial=True,
            ))
        # g2: control, all correct with 3.5
        for framing in ["neutral", "decimal", "version", "date"]:
            results.append(self._make_result(
                correct=True, predicted="3.5", expected="3.5",
                framing=framing, gid="g2", is_adversarial=False,
            ))

        agg = self.evaluator.aggregate_results(results)
        fa = agg["framing_analysis"]
        assert fa["total_groups"] == 2
        # neutral: 2/2 correct, version: 1/2 correct
        assert fa["framing_accuracy_by_type"]["neutral"]["accuracy"] == 1.0
        assert fa["framing_accuracy_by_type"]["version"]["accuracy"] == 0.5
        assert fa["perfect_group_rate"] == 0.5  # g2 perfect, g1 not

    def test_no_framing_analysis_without_decimal_cases(self):
        """Non-decimal results should not produce framing_analysis."""
        results = [
            EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details={
                    "comparison_type": "same_unit",
                    "number_format": "integer",
                    "category": "length",
                    "value1": "10", "value2": "5",
                    "unit1": "cm", "unit2": "cm",
                    "unit1_symbol": "cm", "unit2_symbol": "cm",
                    "question_direction": "bigger",
                    "correct_position": "first",
                    "is_decimal_trap": False,
                    "parse_strategy": "test",
                    "confidence": 0.9,
                    "predicted": "10 cm", "expected": "10 cm",
                },
            ),
        ]
        agg = self.evaluator.aggregate_results(results)
        assert "framing_analysis" not in agg


# =========================================================================
# Mixed-type generation ('all') includes decimal
# =========================================================================

class TestAllTypeIncludesDecimal:
    """When comparison_type='all', decimal should appear in the mix."""

    gen = MeasureComparisonGenerator()

    def test_decimal_appears_in_all(self):
        config = {
            "comparison_type": "all",
            "type_weights": {
                "same_unit": 0.0, "mixed_unit": 0.0,
                "equal": 0.0, "incomparable": 0.0, "decimal": 1.0,
            },
            "decimal_framings": ["neutral", "version"],
            "decimal_adversarial_ratio": 1.0,
        }
        prompt_config = {"user_style": "minimal", "system_style": "analytical"}
        cases = self.gen.generate_batch(config, prompt_config, count=3, seed=42)
        # 3 pairs × 2 framings = 6 cases
        assert len(cases) == 6
        for tc in cases:
            assert tc.task_params["comparison_type"] == "decimal"
