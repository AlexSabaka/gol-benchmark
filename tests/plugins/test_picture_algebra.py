"""Tests for the Picture Algebra benchmark plugin."""
from __future__ import annotations

import pytest

from src.plugins import PluginRegistry
from src.plugins.base import EvaluationResult, ParsedAnswer
from src.plugins.picture_algebra.data.emoji_pools import EMOJI_POOLS
from src.plugins.picture_algebra.evaluator import PictureAlgebraEvaluator
from src.plugins.picture_algebra.generator import (
    ALPHA_SYMBOLS,
    DIFFICULTY_PRESETS,
    NONSENSE_SYMBOLS,
    PictureAlgebraGenerator,
    SENTINEL_CANNOT_DETERMINE,
    SENTINEL_NO_SOLUTION,
)
from src.plugins.picture_algebra.parser import PictureAlgebraParser


# ── Plugin Discovery ─────────────────────────────────────────────────────


class TestPluginDiscovery:
    def test_plugin_registered(self):
        plugin = PluginRegistry.get("picture_algebra")
        assert plugin is not None
        assert plugin.task_type == "picture_algebra"
        assert plugin.display_name == "Picture Algebra"

    def test_components_instantiate(self):
        plugin = PluginRegistry.get("picture_algebra")
        assert plugin.get_generator() is not None
        assert plugin.get_parser() is not None
        assert plugin.get_evaluator() is not None


# ── Generator ────────────────────────────────────────────────────────────


def _default_prompt_config(**overrides):
    pc = {
        "name": "test",
        "language": "en",
        "user_style": "minimal",
        "system_style": "analytical",
    }
    pc.update(overrides)
    return pc


class TestGenerator:
    def test_deterministic_with_seed(self):
        gen = PictureAlgebraGenerator()
        config = {"difficulty": "easy", "count": 5}
        pc = _default_prompt_config()
        a = gen.generate_batch(config, pc, count=5, seed=123)
        b = gen.generate_batch(config, pc, count=5, seed=123)
        assert [c.task_params["equations_text"] for c in a] == \
               [c.task_params["equations_text"] for c in b]
        assert [c.task_params["expected_answer"] for c in a] == \
               [c.task_params["expected_answer"] for c in b]

    def test_unique_systems_roundtrip(self):
        """Plug the stored solutions back into the stored coefficients → RHS."""
        gen = PictureAlgebraGenerator()
        cases = gen.generate_batch(
            {"difficulty": "medium", "count": 8, "trick_rate": 0.0},
            _default_prompt_config(), count=8, seed=7,
        )
        for c in cases:
            assert c.task_params["determinacy"] == "unique"
            sols = c.task_params["solutions_canonical"]
            for eq in c.task_params["equations_structured"]:
                computed = sum(eq["coeffs"][v] * sols[v] for v in sols)
                assert computed == eq["rhs"]

    def test_alpha_surface_form(self):
        gen = PictureAlgebraGenerator()
        cases = gen.generate_batch(
            {"difficulty": "easy", "count": 3, "surface_form": "alpha"},
            _default_prompt_config(), count=3, seed=1,
        )
        for c in cases:
            for tok in c.task_params["variables"]:
                assert tok in ALPHA_SYMBOLS

    def test_nonsense_surface_form(self):
        gen = PictureAlgebraGenerator()
        cases = gen.generate_batch(
            {"difficulty": "easy", "count": 3, "surface_form": "nonsense"},
            _default_prompt_config(), count=3, seed=1,
        )
        for c in cases:
            for tok in c.task_params["variables"]:
                assert tok in NONSENSE_SYMBOLS

    def test_emoji_category_food(self):
        gen = PictureAlgebraGenerator()
        cases = gen.generate_batch(
            {"difficulty": "medium", "count": 5, "surface_form": "emoji", "emoji_category": "food"},
            _default_prompt_config(), count=5, seed=11,
        )
        for c in cases:
            for tok in c.task_params["variables"]:
                assert tok in EMOJI_POOLS["food"]

    def test_trick_cases_underdetermined(self):
        gen = PictureAlgebraGenerator()
        cases = gen.generate_batch(
            {
                "difficulty": "hard", "count": 5,
                "trick_rate": 1.0, "surface_form": "alpha",
            },
            _default_prompt_config(), count=5, seed=9,
        )
        # With trick_rate=1.0 every case must be a sentinel
        sentinels = {SENTINEL_CANNOT_DETERMINE, SENTINEL_NO_SOLUTION}
        for c in cases:
            assert c.task_params["determinacy"] in {"underdetermined", "inconsistent"}
            assert c.task_params["expected_answer"] in sentinels

    def test_multilingual_prompts(self):
        gen = PictureAlgebraGenerator()
        for lang in ["en", "es", "fr", "de", "zh", "ua"]:
            cases = gen.generate_batch(
                {"difficulty": "easy", "count": 1, "surface_form": "alpha"},
                _default_prompt_config(language=lang), count=1, seed=42,
            )
            user = cases[0].prompts["user"]
            assert user.strip() != "", f"Empty prompt for {lang}"
            # Each variable token should appear at least once in the rendered prompt
            for tok in cases[0].task_params["variables"]:
                assert tok in user

    def test_question_scope_specific_narrows_expected(self):
        gen = PictureAlgebraGenerator()
        cases = gen.generate_batch(
            {"difficulty": "hard", "count": 3, "question_scope": "specific",
             "trick_rate": 0.0},
            _default_prompt_config(), count=3, seed=13,
        )
        for c in cases:
            exp = c.task_params["expected_answer"]
            if c.task_params["determinacy"] == "unique":
                assert isinstance(exp, dict)
                assert len(exp) == 1
                assert c.task_params["queried_variable"] in exp

    def test_same_seed_same_math_across_surface_forms(self):
        """GSM-Symbolic invariant: same seed → same underlying system
        regardless of surface_form.  Emoji pool sampling must not perturb the
        system-generation RNG state.
        """
        gen = PictureAlgebraGenerator()
        base = {"difficulty": "medium", "count": 4, "trick_rate": 0.3}
        pc = _default_prompt_config()
        a = gen.generate_batch({**base, "surface_form": "alpha"}, pc, count=4, seed=99)
        e = gen.generate_batch({**base, "surface_form": "emoji"}, pc, count=4, seed=99)
        n = gen.generate_batch({**base, "surface_form": "nonsense"}, pc, count=4, seed=99)
        for ac, ec, nc in zip(a, e, n):
            assert ac.task_params["equations_structured"] == \
                   ec.task_params["equations_structured"] == \
                   nc.task_params["equations_structured"]
            assert ac.task_params["determinacy"] == \
                   ec.task_params["determinacy"] == \
                   nc.task_params["determinacy"]

    def test_config_schema(self):
        gen = PictureAlgebraGenerator()
        fields = {f.name for f in gen.get_config_schema()}
        for required in (
            "difficulty", "count", "num_variables", "num_equations",
            "operations", "surface_form", "emoji_category",
            "question_scope", "trick_rate",
        ):
            assert required in fields

    def test_difficulty_preset_keys(self):
        # Every preset must cover every live config key so explicit overrides
        # have something to diff against.
        keys = set(DIFFICULTY_PRESETS["medium"].keys())
        for name, preset in DIFFICULTY_PRESETS.items():
            assert set(preset.keys()) == keys, f"Preset {name} has asymmetric keys"


# ── Parser ───────────────────────────────────────────────────────────────


def _params(tokens, expected, scope="all", lang="en", determinacy="unique"):
    return {
        "variables": list(tokens),
        "num_variables": len(tokens),
        "language": lang,
        "expected_answer": expected,
        "question_scope": scope,
        "determinacy": determinacy,
    }


class TestParser:
    def test_label_line_basic(self):
        p = PictureAlgebraParser()
        r = p.parse("So x = 5 and y = 7.", _params(["x", "y"], {"x": 5, "y": 7}))
        assert r.value == {"x": 5, "y": 7}
        assert r.parse_strategy == "label_line"

    def test_label_line_end_first_overrides_earlier(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "First guess: x = 1, y = 1. Actually x = 5, y = 7.",
            _params(["x", "y"], {"x": 5, "y": 7}),
        )
        assert r.value == {"x": 5, "y": 7}

    def test_label_line_with_label_repeat(self):
        """'Solving for y: y = 7' should capture 7, not the inner y."""
        p = PictureAlgebraParser()
        r = p.parse(
            "Solving for y: y = 7.",
            _params(["x", "y"], {"y": 7}, scope="specific"),
        )
        assert r.value == {"y": 7}

    def test_boxed_multivar(self):
        p = PictureAlgebraParser()
        r = p.parse(
            r"Therefore \boxed{x=5, y=7}.",
            _params(["x", "y"], {"x": 5, "y": 7}),
        )
        assert r.parse_strategy == "boxed_multivar"
        assert r.value == {"x": 5, "y": 7}

    def test_coord_tuple(self):
        p = PictureAlgebraParser()
        # coord_tuple fires only when no label_line/bold/block matches
        r = p.parse(
            "The solution is (5, 7).",
            _params(["x", "y"], {"x": 5, "y": 7}),
        )
        assert r.value == {"x": 5, "y": 7}
        assert r.parse_strategy == "coord_tuple"

    def test_coord_tuple_arity_mismatch(self):
        """A 2-tuple response for a 3-variable problem should NOT positionally match."""
        p = PictureAlgebraParser()
        r = p.parse(
            "The solution is (5, 7).",
            _params(["x", "y", "z"], {"x": 5, "y": 7, "z": 9}),
        )
        # Either None or something non-positional — key requirement is that
        # we don't silently accept a 2-tuple as an answer to a 3-var system.
        assert r.value != {"x": 5, "y": 7, "z": 9}

    def test_emoji_tokens(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "After substitution: 🍎 = 4, 🍌 = 9.",
            _params(["🍎", "🍌"], {"🍎": 4, "🍌": 9}),
        )
        assert r.value == {"🍎": 4, "🍌": 9}

    def test_cannot_be_determined_strong(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "Analyzing the equations, we see there are infinitely many solutions — cannot be determined.",
            _params(["x", "y"], SENTINEL_CANNOT_DETERMINE, determinacy="underdetermined"),
        )
        assert r.value == "CANNOT_BE_DETERMINED"
        assert r.parse_strategy == "cannot_be_determined"

    def test_no_solution_strong(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "The equations are inconsistent — there is no solution.",
            _params(["x", "y"], SENTINEL_NO_SOLUTION, determinacy="inconsistent"),
        )
        assert r.value == "NO_SOLUTION"

    def test_word_number_en(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "Therefore x equals five.",
            _params(["x"], {"x": 5}, scope="specific"),
        )
        assert r.value == {"x": 5}

    def test_multilingual_ua(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "Відповідь: x = 5, y = 7.",
            _params(["x", "y"], {"x": 5, "y": 7}, lang="ua"),
        )
        assert r.value == {"x": 5, "y": 7}

    def test_foreign_labels(self):
        """Model answered for different variables → preserve keys so evaluator can classify."""
        p = PictureAlgebraParser()
        r = p.parse(
            "Let me call them a and b. a = 5, b = 7.",
            _params(["x", "y"], {"x": 5, "y": 7}),
        )
        assert r.parse_strategy == "foreign_labels"
        assert r.value == {"a": 5, "b": 7}

    def test_negative_integer(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "x = -3, y = 5",
            _params(["x", "y"], {"x": -3, "y": 5}),
        )
        assert r.value == {"x": -3, "y": 5}

    def test_empty_response(self):
        p = PictureAlgebraParser()
        r = p.parse("", _params(["x", "y"], {"x": 5, "y": 7}))
        assert r.value is None
        assert r.parse_strategy == "empty"


# ── Evaluator ────────────────────────────────────────────────────────────


def _eval(predicted, expected, **params):
    e = PictureAlgebraEvaluator()
    tp = {"variables": list(expected.keys()) if isinstance(expected, dict) else [],
          "num_variables": len(expected) if isinstance(expected, dict) else 2,
          "language": "en", "question_scope": params.get("question_scope", "all"),
          "determinacy": params.get("determinacy", "unique"),
          "surface_form": params.get("surface_form", "alpha"),
          "emoji_category": params.get("emoji_category"),
          "operations": params.get("operations", "add_subtract"),
          "num_equations": params.get("num_equations", 2),
          "queried_variable": params.get("queried_variable"),
          }
    parsed = ParsedAnswer(
        value=predicted, raw_response="", parse_strategy="test",
        error=params.get("error"),
    )
    return e.evaluate(parsed, expected, tp)


class TestEvaluator:
    def test_correct(self):
        r = _eval({"x": 5, "y": 7}, {"x": 5, "y": 7})
        assert r.match_type == "correct"
        assert r.accuracy == 1.0

    def test_wrong_value(self):
        r = _eval({"x": 5, "y": 12}, {"x": 5, "y": 7}, question_scope="specific",
                  queried_variable="y")
        # question_scope=specific so one-wrong collapses to wrong_value
        r2 = _eval({"y": 12}, {"y": 7}, question_scope="specific", queried_variable="y")
        assert r2.match_type == "wrong_value"

    def test_wrong_variable(self):
        r = _eval({"a": 5, "b": 7}, {"x": 5, "y": 7})
        assert r.match_type == "wrong_variable"
        assert r.accuracy == 0.0

    def test_partial(self):
        r = _eval({"x": 5, "y": 12}, {"x": 5, "y": 7})
        assert r.match_type == "partial"
        assert abs(r.accuracy - 0.5) < 1e-9

    def test_partial_3of2_correct(self):
        r = _eval({"x": 5, "y": 7, "z": 0}, {"x": 5, "y": 7, "z": 9})
        assert r.match_type == "partial"
        assert abs(r.accuracy - 2 / 3) < 1e-9

    def test_system_error(self):
        r = _eval(
            "CANNOT_BE_DETERMINED", "CANNOT_BE_DETERMINED",
            determinacy="underdetermined",
        )
        assert r.match_type == "system_error"
        assert r.accuracy == 1.0

    def test_system_error_any_sentinel_accepted(self):
        """NO_SOLUTION on an underdetermined system is still system_error."""
        r = _eval(
            "NO_SOLUTION", "CANNOT_BE_DETERMINED",
            determinacy="underdetermined",
        )
        assert r.match_type == "system_error"

    def test_system_error_missed(self):
        r = _eval({"x": 3}, "CANNOT_BE_DETERMINED", determinacy="underdetermined")
        assert r.match_type == "system_error_missed"

    def test_system_error_false_positive(self):
        r = _eval("CANNOT_BE_DETERMINED", {"x": 5, "y": 7})
        assert r.match_type == "system_error_false_positive"

    def test_parse_error(self):
        r = _eval(None, {"x": 5, "y": 7}, error="boom")
        assert r.match_type == "parse_error"

    # ── aggregation ─────────────────────────────────────────────────

    def test_aggregate_includes_breakdowns(self):
        e = PictureAlgebraEvaluator()
        results = [
            EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details={"surface_form": "alpha", "operations": "add_subtract",
                         "num_variables": 2, "determinacy": "unique",
                         "emoji_category": None, "question_scope": "all"},
            ),
            EvaluationResult(
                correct=False, match_type="wrong_value", accuracy=0.0,
                details={"surface_form": "emoji", "operations": "add_subtract",
                         "num_variables": 2, "determinacy": "unique",
                         "emoji_category": "food", "question_scope": "all"},
            ),
        ]
        agg = e.aggregate_results(results)
        assert agg["total"] == 2
        assert agg["correct"] == 1
        assert "surface_form_breakdown" in agg
        assert "alpha" in agg["surface_form_breakdown"]
        assert "emoji" in agg["surface_form_breakdown"]

    def test_semantic_interference_delta(self):
        e = PictureAlgebraEvaluator()
        results = [
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0,
                             details={"surface_form": "alpha"}),
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0,
                             details={"surface_form": "alpha"}),
            EvaluationResult(correct=False, match_type="wrong_value", accuracy=0.0,
                             details={"surface_form": "emoji"}),
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0,
                             details={"surface_form": "emoji"}),
        ]
        agg = e.aggregate_results(results)
        # alpha = 2/2 = 1.0, emoji = 1/2 = 0.5 → delta = 0.5
        assert "semantic_interference_delta" in agg
        assert abs(agg["semantic_interference_delta"] - 0.5) < 1e-9

    def test_no_delta_when_single_surface_form(self):
        e = PictureAlgebraEvaluator()
        results = [
            EvaluationResult(correct=True, match_type="correct", accuracy=1.0,
                             details={"surface_form": "alpha"}),
        ]
        agg = e.aggregate_results(results)
        assert "semantic_interference_delta" not in agg


# ── Integration ──────────────────────────────────────────────────────────


# ── Round 1 regression tests ─────────────────────────────────────────────
#
# Each case below is seeded from a real annotation-report span
# (qwen3.5:0.8b, 2026-04-19).  When any of these regress, the parser is
# back to shipping `foreign_labels` / `last_numbers` instead of the clean
# emoji extraction — see `docs/picture-algebra-parser-round-1.md`.


class TestRound1Regressions:
    """Round 1 annotation-data-driven regression tests (v2.25.1)."""

    @staticmethod
    def _params(tokens, expected, **overrides):
        tp = {
            "variables": list(tokens),
            "num_variables": len(tokens),
            "language": "en",
            "question_scope": "all",
            "determinacy": "unique",
            "expected_answer": expected,
        }
        tp.update(overrides)
        return tp

    def _parse_and_evaluate(self, response, tokens, expected, **tp_overrides):
        from src.plugins.picture_algebra.evaluator import PictureAlgebraEvaluator
        parser = PictureAlgebraParser()
        evaluator = PictureAlgebraEvaluator()
        tp = self._params(tokens, expected, **tp_overrides)
        parsed = parser.parse(response, tp)
        result = evaluator.evaluate(parsed, expected, tp)
        return parsed, result

    # 1. LaTeX \text{<emoji>} wrapping — case 0001 shape
    def test_latex_text_wrapped_emoji(self):
        response = "Answer: $\\text{🚲} = 18, \\text{🧸} = 3$"
        parsed, result = self._parse_and_evaluate(
            response, ["🚲", "🧸"], {"🚲": 18, "🧸": 3},
        )
        assert parsed.parse_strategy == "label_line"
        assert result.match_type == "correct"

    # 2. Dollar-dollar inline LaTeX with \quad — case 0015 shape
    def test_latex_dollardollar_quad_separator(self):
        response = (
            "Solving:\n"
            "$$\n"
            "\\text{🍌} = 5, \\quad \\text{🍟} = 17\n"
            "$$"
        )
        parsed, result = self._parse_and_evaluate(
            response, ["🍌", "🍟"], {"🍌": 5, "🍟": 17},
        )
        assert parsed.parse_strategy == "label_line"
        assert result.match_type == "correct"

    # 3. "This matches" in reasoning MUST NOT strip the conclusion
    def test_mid_response_verification_does_not_strip_conclusion(self):
        response = (
            "From eq1: -4(11) + 8 = -36 (Correct)\n"
            "From eq2: -4(11) + 4 = -40 (Correct)\n"
            "(This matches the second equation.)\n\n"
            "### Conclusion\n"
            "The values for the variables are:\n"
            "- **🦏 = 11**\n"
            "- **🧀 = 4**"
        )
        parsed, result = self._parse_and_evaluate(
            response, ["🦏", "🧀"], {"🦏": 11, "🧀": 4},
        )
        assert parsed.parse_strategy == "label_line"
        assert result.match_type == "correct"
        assert parsed.value == {"🦏": 11, "🧀": 4}

    # 4. Bold-on-token-only (**🦆** = 4)
    def test_bold_on_token_only(self):
        response = "Final answer:\n*   **🦆** = 4\n*   **🥐** = 10"
        parsed, result = self._parse_and_evaluate(
            response, ["🦆", "🥐"], {"🦆": 4, "🥐": 10},
        )
        assert parsed.parse_strategy == "label_line"
        assert result.match_type == "correct"

    # 5. Bold on value only (🦆 = **4**)
    def test_bold_on_value_only(self):
        response = "After solving: 🦆 = **4**, 🥐 = **10**."
        parsed, result = self._parse_and_evaluate(
            response, ["🦆", "🥐"], {"🦆": 4, "🥐": 10},
        )
        assert parsed.parse_strategy == "label_line"
        assert result.match_type == "correct"

    # 6. \boxed{\text{...}} — LaTeX inside boxed
    def test_boxed_with_latex_text(self):
        response = r"Therefore \boxed{\text{🚲} = 18, \text{🧸} = 3}."
        parsed, result = self._parse_and_evaluate(
            response, ["🚲", "🧸"], {"🚲": 18, "🧸": 3},
        )
        assert parsed.parse_strategy == "boxed_multivar"
        assert result.match_type == "correct"

    # 7. foreign_labels guard: emoji answer present → don't use reasoning's x/y
    def test_foreign_labels_guard_when_emoji_present(self):
        response = (
            "Let x = 🍎 and y = 🍌.\n"
            "Solving: x = 3, y = 5.\n"
            "### Answer\n"
            "🍎 = 3, 🍌 = 5."
        )
        parsed, result = self._parse_and_evaluate(
            response, ["🍎", "🍌"], {"🍎": 3, "🍌": 5},
        )
        assert parsed.parse_strategy == "label_line"
        assert "x" not in parsed.value and "y" not in parsed.value
        assert result.match_type == "correct"

    # 8. Alias remap: `Let x = 🍎` declared, model only answers with x/y
    def test_alias_detection_remaps_to_emoji(self):
        response = (
            "Let x = 🐯 and y = 🧸.\n"
            "From the equations we get x = 14, y = 18."
        )
        parsed, result = self._parse_and_evaluate(
            response, ["🐯", "🧸"], {"🐯": 14, "🧸": 18},
        )
        assert parsed.parse_strategy == "foreign_labels_aliased"
        assert parsed.value == {"🐯": 14, "🧸": 18}
        assert result.match_type == "correct"
        assert result.details.get("alias_remap_applied") is True

    # 9. Alias via dollar-wrap + "represent" phrasing (from manual_keyword_distribution)
    def test_alias_with_dollar_wrap_and_represent(self):
        response = (
            "Let $x$ represent the value of the symbol **🐯**.\n"
            "Let $y$ represent the value of the symbol **🧸**.\n"
            "After solving: $$x = 14, \\quad y = 18$$"
        )
        parsed, result = self._parse_and_evaluate(
            response, ["🐯", "🧸"], {"🐯": 14, "🧸": 18},
        )
        assert parsed.parse_strategy == "foreign_labels_aliased"
        assert result.match_type == "correct"
        assert result.details.get("alias_remap_applied") is True

    # 10. Non-integer prediction surfaces as wrong_value + non_integer_prediction flag
    def test_non_integer_prediction_flagged(self):
        # Model got one value wrong with a decimal; expected integers
        response = "- 🎁 = 57\n- 🐴 = 22.2"
        parsed, result = self._parse_and_evaluate(
            response, ["🎁", "🐴"], {"🎁": 57, "🐴": 22},
        )
        # 🎁 correct, 🐴 non-integer → partial (one correct, one wrong)
        assert result.match_type == "partial"
        assert result.details.get("non_integer_prediction") is True
        # Predicted 🐴 kept as float so the flag is meaningful
        assert isinstance(parsed.value["🐴"], float)

    # 11. List-marker prefixes (``*   🐶 = 13``)
    def test_list_marker_prefix(self):
        response = "The values for the variables are:\n*   🐶 = 13\n*   🎳 = 3"
        parsed, result = self._parse_and_evaluate(
            response, ["🐶", "🎳"], {"🐶": 13, "🎳": 3},
        )
        assert parsed.parse_strategy == "label_line"
        assert result.match_type == "correct"

    # 12. Integer comparison no longer silently truncates float predictions
    def test_integer_expected_rejects_float_prediction(self):
        """Regression: `int(22.2) == 22` used to score as correct.  Compare
        as floats now so fractional predictions are graded wrong."""
        from src.plugins.base import ParsedAnswer
        from src.plugins.picture_algebra.evaluator import PictureAlgebraEvaluator
        e = PictureAlgebraEvaluator()
        # Parser-shaped ParsedAnswer with a float value
        parsed = ParsedAnswer(
            value={"🐴": 22.2}, raw_response="", parse_strategy="label_line",
        )
        tp = self._params(["🐴"], {"🐴": 22}, question_scope="specific",
                          queried_variable="🐴")
        result = e.evaluate(parsed, {"🐴": 22}, tp)
        assert result.match_type == "wrong_value"
        assert result.details.get("non_integer_prediction") is True


# ── Round 2 multilingual regression tests ────────────────────────────────
#
# Each case below is seeded from a real annotation-report span across 5
# models × 6 languages (gemma3 12b/27b cloud, gpt-5.4-mini ×2, rnj-1 8b).
# When any of these regress, multilingual sentinel detection or
# single-value boxed handling has broken — see Round 2 plan and
# CHANGELOG v2.25.2.


class TestRound2Multilingual:
    """Round 2 multilingual sentinel + boxed regression tests (v2.25.2)."""

    @staticmethod
    def _params(tokens, language="en", **overrides):
        tp = {
            "variables": list(tokens),
            "num_variables": len(tokens),
            "language": language,
            "question_scope": "all",
            "determinacy": "underdetermined",
        }
        tp.update(overrides)
        return tp

    # ── multilingual sentinel coverage ──────────────────────────────

    def test_es_sentinel_no_unique_solution(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "Resolviendo el sistema… **Respuesta:** El sistema no tiene una única solución.",
            self._params(["🧸", "🍪", "🦊"], language="es"),
        )
        assert r.parse_strategy == "cannot_be_determined"
        assert r.value in ("CANNOT_BE_DETERMINED", "NO_SOLUTION")

    def test_fr_sentinel_pas_solution_unique(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "Après calcul… **Réponse :** Le système n'a pas de solution unique.",
            self._params(["🐢"], language="fr"),
        )
        assert r.parse_strategy == "cannot_be_determined"
        assert r.value in ("CANNOT_BE_DETERMINED", "NO_SOLUTION")

    def test_de_sentinel_keine_eindeutige_loesung_first_sentence(self):
        """Models often LEAD with the conclusion — strict mode must check first sentences too."""
        p = PictureAlgebraParser()
        r = p.parse(
            "Das System hat **keine eindeutige Lösung**.\n\n"
            "Es gibt 2 Gleichungen mit 3 Unbekannten:\n"
            "4·🎁 + 🍓 - 5·🥑 = -69. Wenn wir 🥑 = -304 setzen, dann gilt …",
            self._params(["🎁", "🍓", "🥑"], language="de"),
        )
        assert r.parse_strategy == "cannot_be_determined"

    def test_zh_sentinel_no_unique_solution(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "解方程组得到 x = 4, y = 2, z = 41\n\n**结论:** 方程组没有唯一解",
            self._params(["🍞"], language="zh", question_scope="specific",
                         queried_variable="🍞"),
        )
        assert r.parse_strategy == "cannot_be_determined"

    def test_ua_sentinel_with_curly_apostrophe(self):
        """Curly apostrophe (U+2019) must be normalized to straight (U+0027) for matching."""
        p = PictureAlgebraParser()
        r = p.parse(
            "Розв’язуючи… Система не має єдиного розв’язку.",
            self._params(["🐯", "🧸"], language="ua"),
        )
        assert r.parse_strategy == "cannot_be_determined"

    def test_ua_sentinel_with_straight_apostrophe(self):
        p = PictureAlgebraParser()
        r = p.parse(
            "Розв'язуючи… Система не має єдиного розв'язку.",
            self._params(["🐯", "🧸"], language="ua"),
        )
        assert r.parse_strategy == "cannot_be_determined"

    def test_es_parametric_partial_answer(self):
        """Model gave one variable + said the rest are parametric — that's underdetermined."""
        p = PictureAlgebraParser()
        r = p.parse(
            "**Respuesta:**\n*   🦊 = 9\n*   🍓 y 🦒 pueden tomar múltiples valores enteros, "
            "donde 🦒 = 56 - 2·🍓",
            self._params(["🦊", "🍓", "🦒"], language="es"),
        )
        assert r.parse_strategy == "cannot_be_determined"

    # ── boxed_single_value coverage ─────────────────────────────────

    def test_boxed_single_value_specific_scope(self):
        """`\\boxed{11}` with question_scope='specific' assigns to queried_variable."""
        p = PictureAlgebraParser()
        r = p.parse(
            "After calculation, all paths give the same result.\n\n"
            r"Final Answer: The final answer is $\boxed{11}$",
            self._params(["🐶"], language="en",
                         question_scope="specific", queried_variable="🐶"),
        )
        assert r.parse_strategy == "boxed_single_value"
        assert r.value == {"🐶": 11}

    def test_boxed_single_value_with_preceding_token(self):
        """`<token> est : \\[\\boxed{N}\\]` — nearest preceding token wins."""
        p = PictureAlgebraParser()
        r = p.parse(
            "Calculons les équations.\ny = 2\n\n"
            "Ainsi, la valeur de 🐢 est :\n\n"
            r"\[" "\n" r"\boxed{2}" "\n" r"\]",
            self._params(["🐢"], language="fr",
                         question_scope="all"),
        )
        assert r.parse_strategy == "boxed_single_value"
        assert r.value == {"🐢": 2}

    def test_boxed_single_value_inline_token(self):
        """`🐢 = $ \\boxed{2} $` — token immediately precedes boxed."""
        p = PictureAlgebraParser()
        r = p.parse(
            r"After all checks: 🐢 = $ \boxed{2} $",
            self._params(["🐢"], language="en",
                         question_scope="specific", queried_variable="🐢"),
        )
        assert r.parse_strategy == "boxed_single_value"
        assert r.value == {"🐢": 2}


class TestIntegration:
    def test_end_to_end(self):
        """Generate → fake correct response → parse → evaluate → correct."""
        plugin = PluginRegistry.get("picture_algebra")
        gen = plugin.get_generator()
        parser = plugin.get_parser()
        evaluator = plugin.get_evaluator()

        cases = gen.generate_batch(
            {"difficulty": "easy", "count": 2, "surface_form": "alpha", "trick_rate": 0.0},
            _default_prompt_config(), count=2, seed=42,
        )
        for c in cases:
            exp = c.task_params["expected_answer"]
            # Fake a model response that gives the right answer
            response = "Therefore " + ", ".join(f"{k} = {v}" for k, v in exp.items()) + "."
            parsed = parser.parse(response, c.task_params)
            # Merge prompt_metadata so parser/evaluator get language etc.
            result = evaluator.evaluate(parsed, exp, {**c.task_params, **c.prompt_metadata})
            assert result.correct, f"Failed on {c.test_id}: {result.match_type}"
