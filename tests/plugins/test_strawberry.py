"""
Unit tests for the Strawberry (Character-Level Reasoning) plugin.

Regression tests for false-negative fixes:
  - Bug 1: Falsy expected_answer (0, False) silently dropped by `or` operator
  - Bug 2: Boolean last-keyword extracts contextual "no" from explanations
  - Bug 3: Boolean last-keyword extracts contextual "correct" from explanations
  - Fix 4: strip_verification_tail applied to boolean parser
"""

import pytest
from src.plugins.strawberry.parser import StrawberryParser
from src.plugins.strawberry.evaluator import StrawberryEvaluator
from src.plugins.base import ParsedAnswer


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def parser():
    return StrawberryParser()


@pytest.fixture
def evaluator():
    return StrawberryEvaluator()


# ── Count Parser Tests ────────────────────────────────────────────────────

class TestCountParser:
    """Tests for the COUNT sub-type parser."""

    def test_parse_bare_zero(self, parser):
        """Response '0' should parse to integer 0."""
        result = parser.parse("0", {"sub_type": "count"})
        assert result.value == 0
        assert result.error is None

    def test_parse_zero_with_whitespace(self, parser):
        """Response '\\n\\n0' (qwen3-style) should parse to integer 0."""
        result = parser.parse("\n\n0", {"sub_type": "count"})
        assert result.value == 0

    def test_parse_zero_bold(self, parser):
        """Response with bold **0** should parse to 0."""
        result = parser.parse("The count is **0**.", {"sub_type": "count"})
        assert result.value == 0
        assert result.parse_strategy == "bold"

    def test_parse_count_label(self, parser):
        """Response with 'Answer: 3' should parse to 3."""
        result = parser.parse("Let me count... r, r, r.\nAnswer: 3", {"sub_type": "count"})
        assert result.value == 3

    def test_parse_spelled_out_zero(self, parser):
        """Response 'zero' should parse to 0."""
        result = parser.parse("There are zero instances.", {"sub_type": "count"})
        assert result.value == 0


# ── Count Evaluator Tests ─────────────────────────────────────────────────

class TestCountEvaluator:
    """Tests for the COUNT sub-type evaluator."""

    def test_eval_zero_equals_zero(self, evaluator):
        """parsed=0, expected=0 must be correct (regression for Bug 1)."""
        pa = ParsedAnswer(value=0, raw_response="0", parse_strategy="last_number")
        result = evaluator.evaluate(pa, 0, {"sub_type": "count"})
        assert result.correct is True
        assert result.match_type == "correct"

    def test_eval_count_correct(self, evaluator):
        """parsed=3, expected=3 must be correct."""
        pa = ParsedAnswer(value=3, raw_response="3", parse_strategy="last_number")
        result = evaluator.evaluate(pa, 3, {"sub_type": "count"})
        assert result.correct is True

    def test_eval_count_wrong(self, evaluator):
        """parsed=2, expected=3 must be wrong."""
        pa = ParsedAnswer(value=2, raw_response="2", parse_strategy="last_number")
        result = evaluator.evaluate(pa, 3, {"sub_type": "count"})
        assert result.correct is False
        assert result.match_type == "wrong"


# ── Boolean Parser Tests ──────────────────────────────────────────────────

class TestBooleanParser:
    """Tests for the BOOLEAN sub-type parser (anagram/pangram/lipogram)."""

    # ── Regression: Bug 2 — contextual "no" ──

    def test_lipogram_yes_with_trailing_no(self, parser):
        """'Yes, ... no other characters' must parse as True (Bug 2 regression)."""
        response = (
            'Yes, the sentence "A bright and vivid rainbow hung on the horizon '
            "after rain.\" is a lipogram that avoids the letter 's'. All letters "
            "are in the English alphabet, and there are no other characters or "
            "letters used."
        )
        result = parser.parse(response, {"sub_type": "lipogram"})
        assert result.value is True

    def test_lipogram_yes_trailing_no_variant(self, parser):
        """Another variant: 'Yes, ... no instances of the letter' → True."""
        response = (
            "Yes, the sentence avoids the letter 'x'. There are no instances "
            "of 'x' in the text."
        )
        result = parser.parse(response, {"sub_type": "lipogram"})
        assert result.value is True

    # ── Regression: Bug 3 — contextual "correct" ──

    def test_pangram_false_with_trailing_correct(self, parser):
        """'False. While grammatically correct...' must parse as False (Bug 3 regression)."""
        response = (
            "False.\n\nWhile the sentence is grammatically correct and "
            "evocative, it\u2019s not a pangram. A pangram is a sentence that "
            "contains every letter of the alphabet. This sentence doesn\u2019t.\n\n"
        )
        result = parser.parse(response, {"sub_type": "pangram"})
        assert result.value is False

    # ── Strategy 1-4 unchanged ──

    def test_boxed_true(self, parser):
        """\\boxed{True} should parse to True."""
        result = parser.parse("The answer is \\boxed{True}", {"sub_type": "anagram"})
        assert result.value is True
        assert result.parse_strategy == "boxed"

    def test_boxed_false(self, parser):
        """\\boxed{False} should parse to False."""
        result = parser.parse("\\boxed{False}", {"sub_type": "anagram"})
        assert result.value is False
        assert result.parse_strategy == "boxed"

    def test_bold_yes(self, parser):
        """**Yes** should parse to True."""
        result = parser.parse("After checking, **Yes**.", {"sub_type": "pangram"})
        assert result.value is True
        assert result.parse_strategy == "bold"

    def test_bold_no(self, parser):
        """**No** should parse to False."""
        result = parser.parse("The sentence is **No**, not a pangram.", {"sub_type": "pangram"})
        assert result.value is False
        assert result.parse_strategy == "bold"

    def test_label_line(self, parser):
        """'Answer: Yes' should parse to True."""
        result = parser.parse("Checking letters...\nAnswer: Yes", {"sub_type": "lipogram"})
        assert result.value is True
        assert result.parse_strategy == "label_line"

    def test_answer_is_no(self, parser):
        """'the answer is no' should parse to False."""
        result = parser.parse("After checking each letter, the answer is no.", {"sub_type": "anagram"})
        assert result.value is False
        assert result.parse_strategy == "answer_is"

    # ── Last keyword still works when no opening signal ──

    def test_last_keyword_no_opening(self, parser):
        """When no opening keyword exists, last-keyword should still fire."""
        response = "Checking the sentence character by character... it qualifies, so yes."
        result = parser.parse(response, {"sub_type": "pangram"})
        assert result.value is True

    # ── First-keyword strategy specifics ──

    def test_first_keyword_short_opening(self, parser):
        """Short opening 'No.' should be picked up by first_keyword strategy."""
        response = "No. The two words are not anagrams because they have different letters."
        result = parser.parse(response, {"sub_type": "anagram"})
        assert result.value is False
        assert result.parse_strategy == "first_keyword"

    def test_first_keyword_not_triggered_on_long_fragment(self, parser):
        """Fragments >= 80 chars should not trigger first_keyword strategy."""
        # Build a long first sentence so first_keyword is skipped
        long_opening = "After carefully examining every single letter in the word and comparing them one by one to the other word's letters"
        response = f"{long_opening}, the answer is no."
        result = parser.parse(response, {"sub_type": "anagram"})
        assert result.value is False
        # Should be answer_is or last_keyword, not first_keyword
        assert result.parse_strategy in ("answer_is", "last_keyword")


# ── Boolean Evaluator Tests ───────────────────────────────────────────────

class TestBooleanEvaluator:
    """Tests for the BOOLEAN sub-type evaluator."""

    def test_eval_false_equals_false(self, evaluator):
        """predicted=False, expected=False must be correct (Bug 1 regression)."""
        pa = ParsedAnswer(value=False, raw_response="No", parse_strategy="first_keyword")
        result = evaluator.evaluate(pa, False, {"sub_type": "pangram"})
        assert result.correct is True
        assert result.match_type == "correct"

    def test_eval_true_equals_true(self, evaluator):
        """predicted=True, expected=True must be correct."""
        pa = ParsedAnswer(value=True, raw_response="Yes", parse_strategy="first_keyword")
        result = evaluator.evaluate(pa, True, {"sub_type": "lipogram"})
        assert result.correct is True

    def test_eval_true_vs_false(self, evaluator):
        """predicted=True, expected=False must be wrong."""
        pa = ParsedAnswer(value=True, raw_response="Yes", parse_strategy="first_keyword")
        result = evaluator.evaluate(pa, False, {"sub_type": "anagram"})
        assert result.correct is False
        assert result.match_type == "wrong"


# ── Falsy expected_answer pipeline test ───────────────────────────────────

class TestFalsyExpectedAnswer:
    """Regression tests for the falsy expected_answer bug in run_testset.py.

    The `or` operator in the pipeline dropped expected_answer when it was
    0 or False. These tests verify the evaluator handles such values correctly
    end-to-end (parser → evaluator).
    """

    def test_count_zero_end_to_end(self, parser, evaluator):
        """Full pipeline: response '0', expected 0 → correct."""
        parsed = parser.parse("0", {"sub_type": "count"})
        assert parsed.value == 0
        result = evaluator.evaluate(parsed, 0, {"sub_type": "count"})
        assert result.correct is True

    def test_boolean_false_end_to_end(self, parser, evaluator):
        """Full pipeline: response 'False', expected False → correct."""
        parsed = parser.parse("False.", {"sub_type": "pangram"})
        assert parsed.value is False
        result = evaluator.evaluate(parsed, False, {"sub_type": "pangram"})
        assert result.correct is True

    def test_boolean_true_end_to_end(self, parser, evaluator):
        """Full pipeline: response 'Yes', expected True → correct."""
        parsed = parser.parse("Yes", {"sub_type": "lipogram"})
        assert parsed.value is True
        result = evaluator.evaluate(parsed, True, {"sub_type": "lipogram"})
        assert result.correct is True


# ── Verification tail stripping (Fix 4) ──────────────────────────────────

class TestVerificationStripping:
    """Tests that strip_verification_tail prevents verification sections
    from confusing the boolean parser."""

    def test_verification_section_ignored(self, parser):
        """Keywords in verification section should not override the answer."""
        response = (
            "Yes, this is a valid lipogram.\n\n"
            "Verification: Let me check - no 'x' found in the sentence. Correct."
        )
        result = parser.parse(response, {"sub_type": "lipogram"})
        assert result.value is True
