"""
Tests for end-first parsing refactoring.

Verifies that all parsers prefer the LAST match in responses, not the first.
Tests each parser with scenarios where:
  1. Model gives wrong answer first, corrects itself at end
  2. Model discusses intermediate values before final answer
"""
import sys
import os
import unittest.mock

# Prevent heavy imports (torch, tkinter) from src.__init__
sys.modules.setdefault('torch', unittest.mock.MagicMock())
sys.modules.setdefault('transformers', unittest.mock.MagicMock())
sys.modules.setdefault('_tkinter', unittest.mock.MagicMock())
sys.modules.setdefault('tkinter', unittest.mock.MagicMock())
sys.modules.setdefault('turtle', unittest.mock.MagicMock())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.plugins.parse_utils import re_search_last, last_sentences, last_keyword_position


# ── parse_utils tests ──────────────────────────────────────────────────

class TestParseUtils:
    def test_re_search_last_basic(self):
        m = re_search_last(r"\d+", "abc 1 def 2 ghi 3")
        assert m is not None
        assert m.group() == "3"

    def test_re_search_last_none(self):
        assert re_search_last(r"\d+", "no numbers here") is None

    def test_re_search_last_single(self):
        m = re_search_last(r"\d+", "only 42 here")
        assert m.group() == "42"

    def test_last_sentences(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = last_sentences(text, 2)
        assert len(result) == 2
        assert "Third sentence." in result[0]
        assert "Fourth sentence." in result[1]

    def test_last_sentences_short(self):
        result = last_sentences("Only one.", 3)
        assert len(result) == 1

    def test_last_keyword_position(self):
        text = "walk early, then drive later"
        pos = last_keyword_position(text, [r"walk", r"drive"])
        assert pos == text.lower().index("drive")


# ── Arithmetic parser ──────────────────────────────────────────────────

class TestArithmeticParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.arithmetic.parser import ArithmeticResponseParser
        return ArithmeticResponseParser()

    def test_last_number_skips_percentage(self, parser):
        response = "The calculation gives 42. I am 99% confident in this answer."
        result = parser.parse(response, {})
        assert result.value == 42.0

    def test_latex_boxed_last(self, parser):
        response = "First attempt: \\boxed{10}. Wait, let me recalculate... \\boxed{15}"
        result = parser.parse(response, {})
        assert result.value == 15.0

    def test_equals_last(self, parser):
        response = "Step 1: x = 5\nStep 2: x + 3 = 8\nFinal: 2x + 3 = 13"
        result = parser.parse(response, {})
        assert result.value == 13.0

    def test_answer_keyword_from_end(self, parser):
        response = "The intermediate result is 7.\nAfter correction, the final answer is 12."
        result = parser.parse(response, {})
        assert result.value == 12.0


# ── Game of Life parser ────────────────────────────────────────────────

class TestGoLParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.game_of_life.parser import GoLResponseParser
        return GoLResponseParser()

    def test_marker_search_last(self, parser):
        """If model writes 'next:' twice, use the last one."""
        response = (
            "next:\n0 1\n1 0\n\n"
            "Wait, I made an error. Corrected:\n"
            "next:\n1 1\n0 0"
        )
        task_params = {'expected_next_state': [[1, 1], [0, 0]]}
        result = parser.parse(response, task_params)
        assert result.value == [[1, 1], [0, 0]]

    def test_digit_extraction_from_end(self, parser):
        """Grid extraction should prefer the grid at the end."""
        response = (
            "Current state:\n0 0\n0 0\n\n"
            "After applying rules:\n1 1\n1 0"
        )
        task_params = {'expected_next_state': [[1, 1], [1, 0]]}
        result = parser.parse(response, task_params)
        assert result.value == [[1, 1], [1, 0]]


# ── Carwash parser ─────────────────────────────────────────────────────

class TestCarwashParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.carwash.parser import CarwashParser
        return CarwashParser()

    def test_last_sentences_not_first(self, parser):
        """Should scan last sentences, not first."""
        response = (
            "You might think walking is fine since it's close. "
            "But actually, you need to drive because the car needs the wash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_both_present_last_wins(self, parser):
        """When both drive and walk appear, last mention wins."""
        response = "Some might walk, but the correct answer is to drive."
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_drive_negation(self, parser):
        """'Don't drive' should not count as drive."""
        response = "Don't drive. You should walk to the carwash."
        result = parser.parse(response, {})
        assert result.value == "walk"

    def test_bold_last(self, parser):
        response = "Consider **walking**. Actually no, **drive** there."
        result = parser.parse(response, {})
        assert result.value == "drive"


# ── Inverted Cup parser ───────────────────────────────────────────────

class TestInvertedCupParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.inverted_cup.parser import InvertedCupParser
        return InvertedCupParser()

    def test_flip_wins_when_last(self, parser):
        response = "You could drill a hole, but simply flip the cup over."
        result = parser.parse(response, {})
        assert result.value == "flip"

    def test_wrong_wins_when_last(self, parser):
        response = "Flip it? No, just drill a hole in the bottom."
        result = parser.parse(response, {})
        assert result.value == "wrong"

    def test_last_sentences(self, parser):
        response = (
            "The cup is upside down. Various options exist. "
            "The simplest solution: just flip the cup over."
        )
        result = parser.parse(response, {})
        assert result.value == "flip"


# ── Strawberry parser ─────────────────────────────────────────────────

class TestStrawberryParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.strawberry.parser import StrawberryParser
        return StrawberryParser()

    def test_boxed_last(self, parser):
        response = "Hmm, \\boxed{2}. Wait, let me recount: s-t-r-a-w-b-e-r-r-y. \\boxed{3}"
        result = parser.parse(response, {'word_length': 10})
        assert result.value == 3

    def test_label_last(self, parser):
        response = "Count: 2\nActually I missed one. Count: 3"
        result = parser.parse(response, {'word_length': 10})
        assert result.value == 3

    def test_is_n_last_line(self, parser):
        response = "Let me count: the number of r's is 2.\nWait, checking again: the answer is 3."
        result = parser.parse(response, {'word_length': 10})
        assert result.value == 3


# ── Measure Comparison parser ─────────────────────────────────────────

class TestMeasureComparisonParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.measure_comparison.parser import MeasureComparisonParser
        return MeasureComparisonParser()

    def test_negation_gap_wide_enough(self, parser):
        """'They are definitely not equal' should not match as equal."""
        response = "They are definitely not equal. 5 kg is lighter than 20 lb."
        tp = {'value1': '5', 'unit1_symbol': 'kg', 'value2': '20', 'unit2_symbol': 'lb'}
        result = parser.parse(response, tp)
        assert result.value != "equal"

    def test_bold_last(self, parser):
        response = "First **20 lb**, but actually **5 kg** is the lighter one."
        tp = {'value1': '5', 'unit1_symbol': 'kg', 'value2': '20', 'unit2_symbol': 'lb'}
        result = parser.parse(response, tp)
        assert "5" in str(result.value)


# ── Sally-Anne parser ─────────────────────────────────────────────────

class TestSallyAnneParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.sally_anne.parser import SallyAnneResponseParser
        return SallyAnneResponseParser()

    def test_answer_pattern_last(self, parser):
        response = "Answer: box\nWait, Sally doesn't know it moved. Answer: basket"
        meta = {'container_a': 'basket', 'container_b': 'box'}
        result = parser.parse(response, meta)
        assert result.value == 'basket'

    def test_container_substring_no_false_match(self, parser):
        """'basket' should not match inside 'basketball'."""
        p = parser
        assert p._is_valid_container("basketball", ["basket"]) is False
        assert p._is_valid_container("basket", ["basket"]) is True


# ── Cellular Automata 1D parser ───────────────────────────────────────

class TestC14Parser:
    @pytest.fixture
    def parser(self):
        from src.plugins.cellular_automata_1d.parser import C14ResponseParser
        return C14ResponseParser()

    def test_digit_extraction_from_end(self, parser):
        """When model echoes input then gives output, take from end."""
        response = (
            "Input state: 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1\n"
            "Applying rule 110...\n"
            "Output: 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0"
        )
        tp = {'expected_state': [1]*16, 'width': 16}
        result = parser.parse(response, tp)
        assert result.value is not None
        # Should be from the output line, not the input
        assert result.value == [1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0]

    def test_marker_search_last(self, parser):
        response = (
            "Next state: 0 1 0 1 0 1 0 1\n"
            "Hmm wait, let me redo.\n"
            "Next state: 1 0 1 0 1 0 1 0"
        )
        tp = {'expected_state': [1, 0]*4}
        result = parser.parse(response, tp)
        assert result.value == [1, 0, 1, 0, 1, 0, 1, 0]


# ── Grid Tasks parser ─────────────────────────────────────────────────

class TestGridTasksParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.grid_tasks.parser import GridTasksResponseParser
        return GridTasksResponseParser()

    def test_last_number_not_first(self, parser):
        response = "Row 1 has 5 items, row 2 has 3. Total is 8."
        result = parser.parse(response, {})
        # last_number strategy should find 8
        assert result.value is not None

    def test_boxed_last(self, parser):
        response = "\\boxed{wrong}. Correction: \\boxed{Alice Smith}"
        result = parser.parse(response, {})
        assert result.value == "Alice Smith"

    def test_bold_last(self, parser):
        response = "The answer might be **Bob** but actually it's **Alice**."
        result = parser.parse(response, {})
        assert result.value == "Alice"


# ── Object Tracking parser ────────────────────────────────────────────

class TestObjectTrackingParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.object_tracking.parser import ObjectTrackingResponseParser
        return ObjectTrackingResponseParser()

    def test_answer_prefix_last(self, parser):
        response = "The grape is on the table. Wait, it was moved. The grape is on the counter."
        tp = {'object': 'grape', 'initial_location': 'table', 'expected_answer': 'counter'}
        result = parser.parse(response, tp)
        assert result.value == 'counter'


# ── ASCII Shapes parser ───────────────────────────────────────────────

class TestAsciiShapesParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.ascii_shapes.parser import AsciiShapesResponseParser
        return AsciiShapesResponseParser()

    def test_dimensions_last(self, parser):
        response = "It looks like 3x2 but actually measuring carefully it's 5x4."
        result = parser.parse(response, {'question_type': 'dimensions'})
        assert result.value == "5x4"

    def test_position_last_wins(self, parser):
        """When both positive and negative appear, last one wins."""
        response = "Yes it appears to be there. But on closer look, no, it is not present."
        result = parser.parse(response, {'question_type': 'position'})
        assert result.value is False


# ── Linda Fallacy parser ──────────────────────────────────────────────

class TestLindaFallacyParser:
    @pytest.fixture
    def parser(self):
        from src.plugins.linda_fallacy.parser import LindaResponseParser
        return LindaResponseParser()

    def test_dedup_word_level(self, parser):
        """'bank teller' and 'bank' should NOT be deduped."""
        rankings = [
            "Linda is a bank teller",
            "Linda works at a bank",
            "Linda is a teacher",
            "Linda is a doctor",
            "Linda is a nurse",
            "Linda is a lawyer",
        ]
        result = parser._deduplicate_rankings(rankings)
        # Both should survive — different at word level
        assert len(result) == 6


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
