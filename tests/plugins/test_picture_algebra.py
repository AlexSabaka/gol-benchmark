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
