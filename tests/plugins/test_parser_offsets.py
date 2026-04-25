"""Unit tests for `resolve_parser_offsets` (Phase 2).

The helper is the universal fallback called at result-write time when a
plugin parser doesn't emit `char_start` / `char_end` natively. Covers:

- Type dispatch (str, int, float, bool, list, dict, None)
- End-first preference (last occurrence wins)
- Case-insensitive fallback for capitalisation variants
- Graceful `None` return on types with no meaningful single region
"""
from __future__ import annotations

import pytest

from src.plugins.parse_utils import resolve_parser_offsets


class TestStringValues:
    def test_exact_match_simple(self):
        response = "The answer is drive."
        assert resolve_parser_offsets(response, "drive") == (14, 19)

    def test_picks_last_occurrence(self):
        """End-first convention — multiple mentions return the last."""
        response = "drive first. Then something else. Final answer: drive"
        start, end = resolve_parser_offsets(response, "drive")
        assert response[start:end] == "drive"
        # Must be the LAST occurrence.
        assert start == response.rfind("drive")

    def test_case_insensitive_fallback(self):
        """Model says 'Drive' with a capital; normalised value is 'drive'."""
        response = "Therefore, Drive to the carwash."
        out = resolve_parser_offsets(response, "drive")
        assert out is not None
        start, end = out
        assert response[start:end].lower() == "drive"

    def test_trimmed_needle(self):
        """Whitespace around the value is stripped before search."""
        response = "The answer is walk."
        assert resolve_parser_offsets(response, "  walk  ") == (14, 18)

    def test_value_not_in_response(self):
        assert resolve_parser_offsets("completely unrelated text", "drive") is None

    def test_empty_response(self):
        assert resolve_parser_offsets("", "drive") is None

    def test_empty_value(self):
        assert resolve_parser_offsets("some text", "") is None

    def test_whitespace_only_value(self):
        assert resolve_parser_offsets("some text", "   ") is None


class TestNumericValues:
    def test_int_stringified(self):
        response = "After computation, the result is 42."
        assert resolve_parser_offsets(response, 42) == (33, 35)

    def test_float_stringified(self):
        response = "Pi is approximately 3.14 according to memory."
        out = resolve_parser_offsets(response, 3.14)
        assert out is not None
        start, end = out
        assert response[start:end] == "3.14"

    def test_int_last_occurrence(self):
        response = "5 apples, 5 oranges, and 5 pears"
        start, end = resolve_parser_offsets(response, 5)
        assert start == response.rfind("5")
        assert response[start:end] == "5"

    def test_negative_int(self):
        response = "The delta is -17 units."
        out = resolve_parser_offsets(response, -17)
        assert out is not None
        start, end = out
        assert response[start:end] == "-17"

    def test_int_not_present(self):
        assert resolve_parser_offsets("no numbers here", 42) is None


class TestBooleanValues:
    def test_true_matches_lowercase(self):
        response = "The statement is true."
        out = resolve_parser_offsets(response, True)
        assert out is not None
        start, end = out
        assert response[start:end] == "true"

    def test_false_matches_lowercase(self):
        response = "This is false."
        out = resolve_parser_offsets(response, False)
        assert out is not None
        start, end = out
        assert response[start:end] == "false"

    def test_bool_before_int_check(self):
        """`bool` is a subclass of `int` in Python — ensure bool is checked
        first so `True` doesn't search for the substring "1"."""
        response = "The value 1 is here, but the statement is true."
        out = resolve_parser_offsets(response, True)
        assert out is not None
        start, end = out
        # Should land on "true", not "1".
        assert response[start:end] == "true"


class TestNonScalarValues:
    def test_list_returns_none(self):
        """Grid plugins return list[int]; no meaningful single region."""
        assert resolve_parser_offsets("some response", [0, 1, 0, 1]) is None

    def test_nested_list_returns_none(self):
        """Grid plugins return list[list[int]]."""
        grid = [[0, 1, 0], [1, 0, 1]]
        assert resolve_parser_offsets("grid here", grid) is None

    def test_dict_returns_none(self):
        """Picture-algebra / misquote return dict values."""
        assert resolve_parser_offsets("response", {"x": 1, "y": 2}) is None

    def test_tuple_returns_none(self):
        """Tuple is not covered by the scalar dispatch."""
        assert resolve_parser_offsets("response", (1, 2, 3)) is None

    def test_none_value_returns_none(self):
        assert resolve_parser_offsets("response", None) is None


class TestOffsetCorrectness:
    def test_offsets_slice_back_to_value(self):
        """Invariant: response[start:end] must equal the needle (modulo case)."""
        response = "Preamble text. The final answer is WALK. That's it."
        out = resolve_parser_offsets(response, "walk")
        assert out is not None
        start, end = out
        assert response[start:end].lower() == "walk"

    def test_exclusive_end_offset(self):
        """`end` is exclusive — `response[start:end]` is the full substring."""
        response = "drive"
        assert resolve_parser_offsets(response, "drive") == (0, 5)
