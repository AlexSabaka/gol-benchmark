"""
Unit tests for the Inverted Cup plugin parser.

Regression tests for false-negative fixes:
  - Missing "tilt" and "tip" patterns in FLIP_PATTERNS
  - Missing "mouth facing up" / "rim facing up" descriptive patterns
"""

import pytest
from src.plugins.inverted_cup.parser import InvertedCupParser


@pytest.fixture
def parser():
    return InvertedCupParser()


# ── Fixable false-negative regression tests ──────────────────────────────


class TestTiltTipPatterns:
    """Cases where models use 'tilt' or 'tip' as synonyms for flip."""

    def test_tilt_cup_mouth_facing_up(self, parser):
        """gemma3:27b: 'tilt the cup so the mouth... is facing up'."""
        response = (
            "Okay, that *is* a funny gift! Sounds like a bit of a trick cup. "
            "Here's the deal: you don't drink *from* the mouth. \n\n"
            "You actually **pour the liquid in through the \"bottom\"** (the sealed end). "
            "Then, you tilt the cup so the mouth (the pointed end) is facing *up* and "
            "drink from there. It's designed to look backwards to mess with people!"
        )
        result = parser.parse(response, {})
        assert result.value == "flip", f"Expected 'flip', got '{result.value}' via {result.parse_strategy}"

    def test_tip_the_cup(self, parser):
        """gemma3:27b: 'you simply tip the cup and drink from the open end'."""
        response = (
            "This is a classic riddle! You drink from the bottom! \n\n"
            "Since the top is sealed and the bottom is open, you simply tip the cup "
            "and drink from the open end. It's designed to be a bit of a trick question, "
            "playing on our assumptions about how cups work.\n\n"
            "Congratulations on winning the competition! \U0001f389"
        )
        result = parser.parse(response, {})
        assert result.value == "flip", f"Expected 'flip', got '{result.value}' via {result.parse_strategy}"

    def test_tilt_cup_rim_not_at_bottom(self, parser):
        """claude-haiku-4.5: 'Tilt the cup so the rim is no longer at the very bottom'."""
        response = (
            "# You've got a Puzzle Mug!\n\n"
            "This is a classic novelty item. Here's how to drink from it:\n\n"
            "**The trick:** Tilt the cup so the rim is no longer at the very bottom. "
            "As you angle it, you'll discover there's a **hidden internal tube or channel** "
            "that runs from near the top down to an opening on the side.\n\n"
            "When tilted at the right angle, liquid flows up through this internal passage "
            "and you can drink from it without spilling."
        )
        result = parser.parse(response, {})
        assert result.value == "flip", f"Expected 'flip', got '{result.value}' via {result.parse_strategy}"


# ── Non-fixable cases (models gave wrong/alternative answers) ────────────


class TestNonFlipResponses:
    """Cases where model answers are genuinely not 'flip' — should remain 'wrong'."""

    def test_fill_from_top_sealed_end(self, parser):
        """gemma3:27b: 'fill it up from the top (the closed end)' — model confused."""
        response = (
            "Oh, that's a classic! You got a \"gravity cup\"! "
            "**Just fill it up from the top (the closed end) and drink from that!** "
            "It works because of a little air pocket that gets trapped."
        )
        result = parser.parse(response, {})
        assert result.value == "wrong", f"Expected 'wrong', got '{result.value}' via {result.parse_strategy}"

    def test_put_cup_over_liquid(self, parser):
        """gemma3:27b: 'put the cup over the liquid' — creative alternative, not flip."""
        response = (
            "**You don't *put* liquid *in* the cup. You put the cup *over* the liquid.**\n\n"
            "Essentially, you place the open bottom of the cup *down* onto a surface with "
            "a puddle of liquid on it. The cup will trap the liquid."
        )
        result = parser.parse(response, {})
        assert result.value == "wrong", f"Expected 'wrong', got '{result.value}' via {result.parse_strategy}"


# ── Existing pattern coverage ────────────────────────────────────────────


class TestExistingPatterns:
    """Verify existing FLIP_PATTERNS still work correctly."""

    def test_flip_it(self, parser):
        response = "Just flip it over and use it normally."
        result = parser.parse(response, {})
        assert result.value == "flip"

    def test_turn_upside_down(self, parser):
        response = "Turn the cup upside down so the opening faces up."
        result = parser.parse(response, {})
        assert result.value == "flip"

    def test_invert(self, parser):
        response = "Simply invert the cup."
        result = parser.parse(response, {})
        assert result.value == "flip"

    def test_right_side_up(self, parser):
        response = "Place it right-side-up to use it."
        result = parser.parse(response, {})
        assert result.value == "flip"

    def test_drill_hole(self, parser):
        response = "You could drill a hole in the sealed top."
        result = parser.parse(response, {})
        assert result.value == "wrong"

    def test_empty_response(self, parser):
        result = parser.parse("", {})
        assert result.value == "wrong"
        assert result.parse_strategy == "empty"
