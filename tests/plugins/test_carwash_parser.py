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
        "empty", "boxed", "label_line", "bold_label", "label_newline",
        "bold", "italic", "first_sentence", "strong_intro", "full_text",
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


# ── Bold-label extraction (v2.5 annotation round: qwen3-8b) ──


class TestBoldLabelExtraction:
    """Bold-wrapped labels like **Answer**: Walk must be caught by label_line
    or bold_label, not fall through to the generic bold strategy."""

    def test_bold_answer_colon_plain(self, parser):
        """**Answer**: Walk  →  plain answer after bold label."""
        response = (
            "The distance is short, so driving might seem wasteful.\n\n"
            "**Answer**: Walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_bold_final_answer_colon_plain(self, parser):
        """**Final Answer**: Walk  →  'final answer' label in ANSWER_LABELS."""
        response = (
            "Driving introduces unnecessary complexity.\n\n"
            "**Final Answer**: Walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_bold_answer_colon_bold_answer(self, parser):
        """**Answer**: **Drive to the carwash**  →  bold answer after bold label."""
        response = (
            "Walking is eco-friendly, but the car must reach the wash.\n\n"
            "**Answer**: **Drive to the carwash**"
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_bold_recommendation_no_colon(self, parser):
        """**Final Recommendation** **Walk**  →  bold_label strategy (no colon)."""
        response = (
            "Considering all factors...\n\n"
            "**Final Recommendation** **Walk to the carwash**"
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "bold_label"

    def test_bold_label_inside_single_bold(self, parser):
        """**Answer: Drive to the carwash.**  →  colon inside bold span."""
        response = (
            "The car needs to be at the carwash.\n\n"
            "**Answer: Drive to the carwash.**"
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_label_only_bold_skipped(self, parser):
        """**Recommendation** as a label bold should not count as an answer bold."""
        response = (
            "**Recommendation**\n"
            "After analysis, **drive** to the carwash.\n"
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "bold"

    def test_bold_best_option_label(self, parser):
        """**Best Option**: Walk  →  newly added label."""
        response = (
            "Both options are valid for such a short distance.\n\n"
            "**Best Option**: Walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_bold_conclusion_colon_plain(self, parser):
        """**Conclusion**: Drive  →  conclusion label."""
        response = (
            "The car physically needs to reach the facility.\n\n"
            "**Conclusion**: Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"


# ── Negative patterns: option-listing and explanatory assertions ──


class TestNegativePatterns:
    """Prevent false positives from discussion/comparison contexts."""

    def test_walk_or_drive_in_discussion(self, parser):
        """'walk or drive' in reasoning, drive in recommendation."""
        response = (
            "The question is whether to walk or drive.\n"
            "Walking is faster for short distances, but the car must be there.\n\n"
            "Recommendation: Drive."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_walking_is_faster_explanatory(self, parser):
        """'**Walking is faster**' as explanatory bold, not answer."""
        response = (
            "Let's compare the two options:\n"
            "- **Walking is faster** for such a short distance\n"
            "- **Driving ensures the car arrives**\n\n"
            "**Answer**: Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_determine_walk_or_drive(self, parser):
        """'to determine whether to walk or drive' is deliberation."""
        response = (
            "We need to determine whether to walk or drive.\n"
            "After careful analysis: drive."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_drive_or_walk_symmetric(self, parser):
        """'drive or walk' symmetric option listing."""
        response = (
            "Should you drive or walk to the carwash?\n"
            "Given the car needs washing, you should drive."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_walking_would_be_faster_in_bold(self, parser):
        """Explanatory bold 'Walking would be faster' should not win."""
        response = (
            "**Walking would be faster** for 200 metres, but the car itself "
            "needs to reach the carwash.\n\n"
            "**Conclusion**: Drive."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"


# ── Label-newline and bold_label colon-inside-bold (round 2) ──


class TestLabelNewline:
    """Label on one line, answer on the next — heading or bold label patterns."""

    def test_heading_recommendation_bold_answer(self, parser):
        """### **Recommendation**\\n**Walk to the carwash**"""
        response = (
            "Analysis of factors...\n\n"
            "### **Recommendation**\n"
            "**Walk to the carwash** for this short distance."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy in ("bold_label", "label_newline")

    def test_heading_answer_bold_answer(self, parser):
        """### **Answer**\\n**Drive to the carwash**"""
        response = (
            "Weighing the options...\n\n"
            "### **Answer**\n"
            "**Drive to the carwash**."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy in ("bold_label", "label_newline")

    def test_label_colon_newline_bold_answer(self, parser):
        """**Best Option**:  \\n**Walk** — label_line's \\s* spans the newline."""
        response = (
            "Consider the distance and convenience.\n\n"
            "**Best Option**:\n"
            "**Walk** to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_label_colon_newline_plain_answer(self, parser):
        """**Decision**:\\nDrive — label_line's \\s* spans the newline."""
        response = (
            "The car must be at the wash.\n\n"
            "**Decision**:\n"
            "Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_bold_label_colon_inside_bold_newline(self, parser):
        """**Answer:**  \\nThe user should **walk**"""
        response = (
            "**Answer:**\n"
            "The user should **walk** to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"

    def test_heading_label_plain_answer(self, parser):
        """### Recommendation\\nDrive to the carwash."""
        response = (
            "Many factors to consider.\n\n"
            "### Recommendation\n"
            "Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_newline"


# ── Multilingual verb conjugation coverage (round 3: nemotron-3 annotations) ──


class TestMultilingualConjugation:
    """Conjugated verb forms models actually produce (marchez, camina,
    gehe, fahre, conduisez) must be recognized by _score()."""

    # -- French --

    def test_french_marchez(self, parser):
        """Imperative 'Marchez' — most common FR walk form (7 cases)."""
        response = "Recommandation : Marchez au lavage auto."
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "walk"

    def test_french_marche(self, parser):
        """3rd person 'marche' — 3 cases in annotation data."""
        response = "Il est préférable de marche vers le lavage."
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "walk"

    def test_french_conduisez(self, parser):
        """Imperative 'Conduisez' — conduis- stem, 5 cases."""
        response = "Réponse finale : Conduisez votre voiture au lavage."
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "drive"

    def test_french_conduisez_vs_marchez(self, parser):
        """Both conjugated forms present — last keyword wins."""
        response = (
            "On pourrait marchez, mais la voiture doit y être.\n"
            "Conclusion : Conduisez."
        )
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "drive"

    # -- Spanish --

    def test_spanish_camina(self, parser):
        """Imperative 'Camina' — 4 cases in data."""
        response = "Recomendación: Camina al lavadero."
        result = parser.parse(response, {"language": "es"})
        assert result.value == "walk"

    def test_spanish_camine(self, parser):
        """Subjunctive 'Camine' — 1 case."""
        response = "Es mejor que camine al lavadero de autos."
        result = parser.parse(response, {"language": "es"})
        assert result.value == "walk"

    def test_spanish_caminando(self, parser):
        """Gerund 'caminando' — covered by camin[aeo]\\w* pattern."""
        response = "La mejor opción es ir caminando al lavadero."
        result = parser.parse(response, {"language": "es"})
        assert result.value == "walk"

    # -- German --

    def test_german_gehe(self, parser):
        """1st person 'Gehe' — 2 cases."""
        response = "Empfehlung: Gehe zu Fuß zur Waschanlage."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "walk"

    def test_german_fahre(self, parser):
        """1st person 'Fahre' — 3 cases."""
        response = "Empfehlung: Fahre mit dem Auto zur Waschanlage."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "drive"

    def test_german_losgehen(self, parser):
        """Compound verb 'losgehen' — 1 case."""
        response = "Am besten direkt losgehen zur Waschanlage."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "walk"

    def test_german_fuss_standalone(self, parser):
        """Standalone 'Fuß' without 'zu' prefix — 4 cases."""
        response = "Fazit: Fuß ist die beste Wahl."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "walk"

    def test_german_losfahren(self, parser):
        """Compound verb 'losfahren'."""
        response = "Sofort losfahren zur Waschanlage."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "drive"


# ── Round 4: vs/versus comparison filtering ──


class TestVsComparisonFiltering:
    """'Walk vs. Drive' headings and comparisons must not cause false matches.
    Annotation v2.6: 9 negative 'vs' + 2 negative 'Walk vs' keywords."""

    def test_walk_vs_drive_heading(self, parser):
        """Comparison heading before labelled answer."""
        response = (
            "## Walk vs. Drive\n"
            "Analysis of both options...\n\n"
            "Conclusion: Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_drive_vs_walk_heading(self, parser):
        """Reversed comparison heading, walk answer."""
        response = (
            "## Drive vs. Walk\n"
            "Driving adds complexity.\n\n"
            "Recommendation: Walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_vs_in_bold_heading(self, parser):
        """Bold comparison heading."""
        response = (
            "**Walk vs Drive**\n"
            "For 200 metres, walking is faster.\n\n"
            "Answer: Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_vs_without_label(self, parser):
        """Comparison without a labelled answer — strong_intro or full_text."""
        response = (
            "Walk versus Drive comparison.\n"
            "The best option is to drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_walk_versus_drive(self, parser):
        """Spelled-out 'versus'."""
        response = (
            "Walking versus driving analysis.\n"
            "Recommendation: Drive."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"


# ── Round 4: drive conditional filtering ──


class TestDriveConditionalFiltering:
    """Drive mentions in option-listing / deliberation framing must be filtered
    so that the actual answer wins the tie-break."""

    def test_whether_to_drive_then_walk_answer(self, parser):
        """'Whether to drive or walk' framing, model answers walk."""
        response = (
            "Whether to drive or walk depends on distance.\n\n"
            "Conclusion: Walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_drive_or_walk_question_walk_answer(self, parser):
        """Question framing with walk answer."""
        response = (
            "Should you drive or walk?\n\n"
            "Answer: Walk."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"

    def test_option_listing_both_filtered_fallthrough(self, parser):
        """Both keywords in option-listing only — _score returns None,
        later strategy picks up the standalone answer."""
        response = "Drive or walk to the carwash? Drive."
        result = parser.parse(response, {})
        assert result.value == "drive"

    def test_drive_in_reasoning_walk_in_label(self, parser):
        """Drive in reasoning, walk in labelled answer."""
        response = (
            "You could drive, but it's unnecessary for 200 metres.\n\n"
            "Recommendation: Walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_determine_drive_or_walk(self, parser):
        """'determine whether to drive or walk' — deliberation framing."""
        response = (
            "We need to determine whether to drive or walk.\n"
            "After analysis of the short distance:\n\n"
            "Conclusion: Walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"


# ── Round 4: new label words ──


class TestNewLabels:
    """Labels added from context_anchor_groups in v2.6 report."""

    def test_german_zusammenfassung(self, parser):
        response = "Zusammenfassung: Fahren Sie zum Autowaschen."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_german_kurzantwort(self, parser):
        response = "Kurzantwort: Gehen Sie zu Fuß."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_german_handlungsanleitung(self, parser):
        response = "Handlungsanleitung: Fahren Sie zur Waschanlage."
        result = parser.parse(response, {"language": "de"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_french_action_recommandee(self, parser):
        response = "Action recommandée: Conduisez au lavage."
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"

    def test_french_choix(self, parser):
        response = "Choix: Marcher au lavage auto."
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "walk"
        assert result.parse_strategy == "label_line"

    def test_spanish_resumen(self, parser):
        response = "Resumen: Conduce al lavado de autos."
        result = parser.parse(response, {"language": "es"})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"


# ── Round 4: "therefore" in strong_intro ──


class TestThereforeStrongIntro:
    """'Therefore', 'daher', 'donc', 'por lo tanto' as conclusion connectors
    in _STRONG_INTRO. 4 cases in context_anchor_groups."""

    def test_therefore_drive(self, parser):
        """Multi-line so first_sentence falls through (first line has no keyword)."""
        response = (
            "Both options were considered.\n"
            "Therefore, drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "strong_intro"

    def test_therefore_walk(self, parser):
        response = (
            "The analysis is complete.\n"
            "Therefore, walk to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "walk"
        assert result.parse_strategy == "strong_intro"

    def test_german_daher(self, parser):
        response = (
            "Die Analyse ist abgeschlossen.\n"
            "Daher fahren Sie zur Waschanlage."
        )
        result = parser.parse(response, {"language": "de"})
        assert result.value == "drive"
        assert result.parse_strategy == "strong_intro"

    def test_french_donc(self, parser):
        response = (
            "L'analyse est terminée.\n"
            "Donc conduisez votre voiture au lavage."
        )
        result = parser.parse(response, {"language": "fr"})
        assert result.value == "drive"
        assert result.parse_strategy == "strong_intro"

    def test_spanish_por_lo_tanto(self, parser):
        response = (
            "El análisis está completo.\n"
            "Por lo tanto conduce al lavado."
        )
        result = parser.parse(response, {"language": "es"})
        assert result.value == "drive"
        assert result.parse_strategy == "strong_intro"

    def test_therefore_with_label_takes_precedence(self, parser):
        """Label strategy beats strong_intro — therefore in reasoning won't
        override a labelled answer."""
        response = (
            "Therefore, walking is faster for short distances.\n\n"
            "Conclusion: Drive to the carwash."
        )
        result = parser.parse(response, {})
        assert result.value == "drive"
        assert result.parse_strategy == "label_line"
