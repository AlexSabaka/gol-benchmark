"""
Unit tests for the Carwash Paradox plugin parser.

Derived from the 300-case English annotation sweep (Improvement Report v2.4)
across gpt-5.4-nano / claude-3.5-haiku / claude-3-haiku. Each test targets a
specific parser gap the annotations surfaced. Per-language smoke tests verify
that the 6-language keyword/label infrastructure works end-to-end.
"""

import pytest

from src.plugins.carwash.parser import CarwashParser


@pytest.fixture
def parser():
    return CarwashParser()


# ── Strategy-reorder regression: label_line must beat bold on mixed input ──


class TestLabelLineBeatsBold:
    """The critical refactor: 'Recommendation: Drive' must win over bolded
    explanation bullets like '**Walking costs no fuel**'."""

    def test_label_drive_after_walk_bullets(self, parser):
        response = (
            "Arguments for walking:\n"
            "- **Walking costs basically no fuel**\n"
            "- **No wear on the vehicle**\n\n"
            "However, you need the car *at* the carwash.\n\n"
            "Recommendation: Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_conclusion_drive_after_walk_bold(self, parser):
        """Matches carwash_999_0067 shape: 'Recommendation: Drive to the carwash'."""
        response = (
            "For a short distance, **walking would be faster** on paper.\n"
            "But the physical object (the car) needs to reach the wash.\n\n"
            "Conclusion: Drive to the carwash.\n"
            "Rationale: physical constraint dominates."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_bottom_line_label(self, parser):
        """New label in _EXTRA_LABELS: 'bottom line'."""
        response = (
            "Walking seems appealing for such a short trip, but...\n\n"
            "**Bottom line:** Drive — the carwash needs the car."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_tldr_label(self, parser):
        response = "Lots of reasoning about **walking** being eco-friendly.\n\nTL;DR: drive."
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_final_answer_label(self, parser):
        response = "Some analysis mentioning walk a few times.\n\nFinal answer: drive."
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"


# ── New drive keyword: "by car" / "in the car" standalone ──


class TestByCarKeyword:
    """carwash_999_0004 regression: '**Answer: By car.**'."""

    def test_by_car_as_answer(self, parser):
        response = (
            "The riddle is nudging you toward the answer that's *not* the "
            "intuitive walking option.\n\n**Answer: By car.**"
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_in_the_car_standalone(self, parser):
        response = "The best choice here is clearly to get in the car."
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_by_car_does_not_match_carwash(self, parser):
        """\\bcar\\b must not fire on 'carwash' (word-boundary check)."""
        response = "Just walk to the carwash, it's only 50 metres."
        result = parser.parse(response, {})
        assert result.value == "walk"


# ── New bold extraction strategy: italic ──


class TestItalicStrategy:
    """carwash_999_0022 / 0028: '... the recommended option is to *walk*'."""

    def test_italic_star_drive_at_end(self, parser):
        response = "After considering all factors, the recommended option is to *drive* to the carwash."
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_italic_underscore_walk_at_end(self, parser):
        """carwash_999_0018 variant: '_Walk_'."""
        response = (
            "For this very short distance there's no strong reason to use the "
            "car unless you physically can't walk comfortably.\n\n"
            "Answer: _Walk_ (assuming you're able to walk comfortably)."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"

    def test_italic_does_not_match_inside_bold(self, parser):
        """Lookarounds prevent ** …  ** from being parsed as italic '* … *'."""
        response = "Some text here. **Drive**."
        result = parser.parse(response, {})
        assert result.value == "drive"
        # Should hit 'bold', not 'italic'
        assert result.parse_strategy == "bold"


# ── New strong_intro phrases: "is to X" / "would be to X" ──


class TestStrongIntroInfinitive:
    def test_is_to_drive(self, parser):
        response = (
            "Looking at everything together — travel time, fuel cost, and the "
            "fact that the vehicle must actually reach the wash — the correct "
            "thing to do in this situation is to drive over there."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_would_be_to_drive(self, parser):
        response = (
            "Given the 100-metre distance and the dirt-transfer issue, "
            "the optimal choice in this scenario would be to drive."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_action_is_to_walk(self, parser):
        response = (
            "Considering fuel efficiency and the short distance, after "
            "weighing the tradeoffs carefully, the recommended action is to walk."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"


# ── Strategy 1 regression: boxed ──


class TestBoxed:
    def test_boxed_drive(self, parser):
        response = "After analysis \\boxed{drive}"
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "boxed"

    def test_boxed_walk(self, parser):
        response = "After analysis \\boxed{walk}"
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "boxed"


# ── Conditional-walk suppression (regression for _is_conditional_walk) ──


class TestConditionalWalkSuppression:
    def test_walk_for_exercise_then_drive(self, parser):
        response = (
            "You could walk for exercise if you felt like it, but realistically "
            "you should drive given that the car physically has to get washed."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_walking_back_would_be_awkward(self, parser):
        """Concessive walk mention shouldn't flip a drive answer."""
        response = (
            "Walking there would leave the car at home, and walking back would be "
            "awkward. Conclusion: Drive."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"


# ── Fallback / ambiguous ──


class TestFallback:
    def test_empty_response(self, parser):
        result = parser.parse("", {})
        assert result.value == "other"
        assert result.parse_strategy == "empty"

    def test_no_signal(self, parser):
        response = "Interesting question. It depends on many factors really."
        result = parser.parse(response, {})
        assert result.value == "other"
        assert result.parse_strategy == "fallback"


# ── parse_strategy persistence (data_quality warning fix verification) ──


class TestParseStrategyEmission:
    """Every non-empty parse must return a concrete parse_strategy (not 'unknown'
    or empty). Regression against the 300/300 'no_parse_strategy' data-quality
    warning in Improvement Report v2.4."""

    VALID_STRATEGIES = {
        "empty", "boxed", "label_line", "bold", "italic",
        "first_sentence", "strong_intro", "full_text",
        "last_sentences", "fallback",
    }

    @pytest.mark.parametrize("response", [
        "Recommendation: Drive.",
        "**Walk**",
        "\\boxed{drive}",
        "the recommended option is to *walk*",
        "You should drive.",
        "is to drive",
        "Walk to the carwash.",
        "",
        "I don't know.",
    ])
    def test_strategy_is_concrete(self, parser, response):
        result = parser.parse(response, {})
        assert result.parse_strategy in self.VALID_STRATEGIES
        assert result.parse_strategy != "unknown"
        assert result.parse_strategy != ""


# ── Per-language smoke tests ──


class TestMultilingualLabelLine:
    """Verify _EXTRA_LABELS + _STRONG_INTRO dicts work for all 6 languages.
    Each test uses a localized 'Recommendation:' equivalent."""

    def test_spanish_recomendacion(self, parser):
        response = "Mucho análisis...\n\nRecomendación: conducir al lavadero."
        result = parser.parse(response, {"language": "es"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_french_recommandation(self, parser):
        response = "Beaucoup d'analyse...\n\nRecommandation : conduire jusqu'au lavage."
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_german_empfehlung(self, parser):
        response = "Viel Analyse...\n\nEmpfehlung: mit dem Auto fahren."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_chinese_tuijian(self, parser):
        response = "分析很多。\n\n推荐:开车去。"
        result = parser.parse(response, {"language": "zh"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_ukrainian_rekomendaciya(self, parser):
        response = "Багато аналізу...\n\nРекомендація: їхати машиною."
        result = parser.parse(response, {"language": "ua"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"


class TestMultilingualByCar:
    """Standalone 'by car' / equivalents per language should resolve to drive."""

    def test_spanish_en_coche(self, parser):
        response = "La mejor forma es en coche."
        result = parser.parse(response, {"language": "es"})
        assert result.value == "drive"

    def test_french_en_voiture(self, parser):
        response = "Le mieux est en voiture."
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "drive"

    def test_german_im_auto(self, parser):
        response = "Am besten im Auto."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "drive"

    def test_ukrainian_mashynoju(self, parser):
        response = "Найкраще — машиною."
        result = parser.parse(response, {"language": "ua"})
        assert result.value == "drive"


# ── Evaluator-adjacent: ParsedAnswer shape ──


class TestParsedAnswerShape:
    def test_raw_response_preserved(self, parser):
        response = "Recommendation: Drive."
        result = parser.parse(response, {})
        assert result.raw_response == response

    def test_confidence_is_float(self, parser):
        result = parser.parse("Recommendation: Drive.", {})
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
