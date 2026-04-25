"""Unit tests for Phase 1 shared-utility extractions in ``parse_utils``.

Covers the five helpers promoted in the cross-plugin alignment plan:

- ``normalize_unicode``
- ``normalize_for_label_matching``
- ``try_parse_number``
- ``detect_sentinel_keyword``
- ``has_contextual_marker``
"""
from __future__ import annotations

import re

import pytest

from src.plugins.parse_utils import (
    detect_sentinel_keyword,
    has_contextual_marker,
    normalize_for_label_matching,
    normalize_unicode,
    try_parse_number,
)


class TestNormalizeUnicode:
    def test_curly_apostrophe(self):
        assert normalize_unicode("don\u2019t") == "don't"

    def test_curly_single_quotes(self):
        assert normalize_unicode("\u2018hi\u2019") == "'hi'"

    def test_curly_double_quotes(self):
        assert normalize_unicode("\u201Chi\u201D") == '"hi"'

    def test_passthrough(self):
        assert normalize_unicode("plain text") == "plain text"


class TestNormalizeForLabelMatching:
    def test_text_wrapper_stripped(self):
        assert normalize_for_label_matching("\\text{🚲} = 18") == "🚲 = 18"

    def test_mathbf_wrapper_stripped(self):
        assert normalize_for_label_matching("\\mathbf{x} + 1") == "x + 1"

    def test_nested_wrapper_stripped(self):
        # \mathbf{\text{X}} should fully unwrap within 3 iterations
        assert normalize_for_label_matching("\\mathbf{\\text{X}}") == "X"

    def test_spacing_macros_become_space(self):
        got = normalize_for_label_matching("a\\quad b\\,c")
        assert "\\quad" not in got and "\\," not in got

    def test_math_delimiters_become_space(self):
        assert normalize_for_label_matching("$x=5$").strip() == "x=5"

    def test_passthrough(self):
        assert normalize_for_label_matching("plain") == "plain"


class TestTryParseNumber:
    def test_integer(self):
        assert try_parse_number("42") == 42
        assert isinstance(try_parse_number("42"), int)

    def test_negative_integer(self):
        assert try_parse_number("-7") == -7

    def test_float(self):
        assert try_parse_number("22.2") == 22.2
        assert isinstance(try_parse_number("22.2"), float)

    def test_float_not_truncated_to_int(self):
        # The entire reason the helper exists: int("22.2") would crash, but
        # int(float("22.2")) == 22 would silently hide wrong predictions.
        result = try_parse_number("22.2")
        assert result != 22  # float 22.2 != int 22

    def test_strips_markdown(self):
        assert try_parse_number("**5**") == 5
        assert try_parse_number("_5_") == 5
        assert try_parse_number("`5`") == 5

    def test_strips_trailing_punctuation(self):
        assert try_parse_number("5.") == 5
        assert try_parse_number("5,") == 5

    def test_word_fallback(self):
        assert try_parse_number("three", {"three": 3}) == 3

    def test_negative_word_fallback(self):
        assert try_parse_number("- three", {"three": 3}) == -3
        assert try_parse_number("negative three", {"three": 3}) == -3
        assert try_parse_number("\u2212 three", {"three": 3}) == -3

    def test_no_match_returns_none(self):
        assert try_parse_number("hello") is None


class TestDetectSentinelKeyword:
    def test_opening_match(self):
        kw = {"en": ["no solution"]}
        text = "The system has no solution. I checked twice."
        assert detect_sentinel_keyword(text, kw, "en")

    def test_closing_match(self):
        kw = {"en": ["no solution"]}
        text = "We start by checking. We compute. The system has no solution."
        assert detect_sentinel_keyword(text, kw, "en")

    def test_middle_not_matched(self):
        kw = {"en": ["no solution"]}
        # Fill with enough sentences that the middle is outside the first/last window
        text = (
            "Opening sentence one. Opening sentence two. "
            "Here is a sentence that mentions no solution in the middle. "
            "Then more reasoning. Another filler sentence. Another. "
            "Another. Another. Another. Another. Another. Closing sentence."
        )
        assert not detect_sentinel_keyword(text, kw, "en", scan_first=2, scan_last=2)

    def test_apostrophe_normalization(self):
        kw = {"ua": ["немає розв'язку"]}
        # Text uses curly U+2019 apostrophe
        text = "\u041d\u0435\u043c\u0430\u0454 \u0440\u043e\u0437\u0432\u2019\u044f\u0437\u043a\u0443."
        assert detect_sentinel_keyword(text, kw, "ua")

    def test_empty_text(self):
        kw = {"en": ["no solution"]}
        assert not detect_sentinel_keyword("", kw, "en")


class TestHasContextualMarker:
    def test_non_positional_match(self):
        pat = {"en": re.compile(r"\bonly\s+if\b", re.IGNORECASE)}
        text = "You should walk only if the weather is good."
        walk_pos = text.index("walk")
        assert has_contextual_marker(text, walk_pos, [pat], "en")

    def test_non_positional_outside_window(self):
        pat = {"en": re.compile(r"\bonly\s+if\b", re.IGNORECASE)}
        # Place "only if" far away from the walk mention
        text = "only if " + ("x" * 500) + " and then walk here"
        walk_pos = text.index("walk")
        assert not has_contextual_marker(text, walk_pos, [pat], "en")

    def test_positional_mode_requires_match_to_contain_position(self):
        # "walk or drive" should filter a drive mention inside the listing
        pat = {"en": re.compile(r"\bwalk\s+or\s+drive\b", re.IGNORECASE)}
        text = "You could walk or drive there."
        drive_pos = text.index("drive")
        # positional=True: drive_pos falls INSIDE the "walk or drive" span → True
        assert has_contextual_marker(
            text, drive_pos, [pat], "en", positional=True,
        )

    def test_positional_mode_does_not_match_adjacent_drive(self):
        # Separate option-listing earlier, then a genuine drive recommendation later
        pat = {"en": re.compile(r"\bwalk\s+or\s+drive\b", re.IGNORECASE)}
        text = "Consider walk or drive. After thinking, drive."
        second_drive = text.rindex("drive")
        # positional=True: second drive is NOT inside the earlier listing span → False
        assert not has_contextual_marker(
            text, second_drive, [pat], "en", positional=True,
        )

    def test_lang_fallback_includes_english(self):
        pat_en = {"en": re.compile(r"\bonly\s+if\b", re.IGNORECASE)}
        text = "walk only if it rains"
        pos = text.index("walk")
        # Request Spanish language; EN patterns should still apply.
        assert has_contextual_marker(text, pos, [pat_en], "es")

    def test_multiple_pattern_dicts(self):
        pat_a = {"en": re.compile(r"never", re.IGNORECASE)}
        pat_b = {"en": re.compile(r"unless", re.IGNORECASE)}
        text = "walk unless it rains"
        pos = text.index("walk")
        assert has_contextual_marker(text, pos, [pat_a, pat_b], "en")
