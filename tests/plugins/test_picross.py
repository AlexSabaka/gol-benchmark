"""Tests for the Picross (Nonogram) benchmark plugin."""

import pytest

from src.plugins import PluginRegistry
from src.plugins.base import EvaluationResult, ParsedAnswer
from src.plugins.picross.evaluator import PicrossEvaluator
from src.plugins.picross.grid_gen import difficulty_to_size, generate_puzzle
from src.plugins.picross.parser import PicrossParser
from src.plugins.picross.solver import backtrack_solve, derive_clues, is_line_solvable, line_solve

import random


# ── Plugin Discovery ─────────────────────────────────────────────────────


class TestPluginDiscovery:
    def test_plugin_registered(self):
        plugin = PluginRegistry.get("picross")
        assert plugin is not None
        assert plugin.task_type == "picross"
        assert plugin.display_name == "Picross (Nonogram)"

    def test_components_instantiate(self):
        plugin = PluginRegistry.get("picross")
        assert plugin.get_generator() is not None
        assert plugin.get_parser() is not None
        assert plugin.get_evaluator() is not None


# ── Solver ───────────────────────────────────────────────────────────────


class TestSolver:
    def test_derive_clues_simple(self):
        grid = [[1, 0, 1], [0, 0, 0], [1, 1, 1]]
        row_clues, col_clues = derive_clues(grid)
        assert row_clues == [[1, 1], [0], [3]]
        assert col_clues == [[1, 1], [1], [1, 1]]

    def test_derive_clues_empty(self):
        grid = [[0, 0], [0, 0]]
        row_clues, col_clues = derive_clues(grid)
        assert row_clues == [[0], [0]]
        assert col_clues == [[0], [0]]

    def test_derive_clues_full(self):
        grid = [[1, 1], [1, 1]]
        row_clues, col_clues = derive_clues(grid)
        assert row_clues == [[2], [2]]
        assert col_clues == [[2], [2]]

    def test_line_solve_trivial(self):
        """3×3 grid with rows [3], [0], [3] should be line-solvable."""
        row_clues = [[3], [0], [3]]
        col_clues = [[1, 1], [1, 1], [1, 1]]
        result = line_solve(row_clues, col_clues)
        assert result is not None
        assert result == [[1, 1, 1], [0, 0, 0], [1, 1, 1]]

    def test_line_solve_returns_none_for_ambiguous(self):
        """A grid that's not line-solvable returns None."""
        # 2×2 with row clues [1],[1] and col clues [1],[1] has 2 solutions
        row_clues = [[1], [1]]
        col_clues = [[1], [1]]
        result = line_solve(row_clues, col_clues)
        assert result is None

    def test_is_line_solvable(self):
        grid = [[1, 1, 1], [0, 0, 0], [1, 1, 1]]
        row_clues, col_clues = derive_clues(grid)
        assert is_line_solvable(row_clues, col_clues) is True

    def test_backtrack_solve_unique(self):
        row_clues = [[3], [0], [3]]
        col_clues = [[1, 1], [1, 1], [1, 1]]
        solutions = backtrack_solve(row_clues, col_clues, max_solutions=2)
        assert len(solutions) == 1

    def test_backtrack_solve_multiple(self):
        row_clues = [[1], [1]]
        col_clues = [[1], [1]]
        solutions = backtrack_solve(row_clues, col_clues, max_solutions=2)
        assert len(solutions) == 2


# ── Grid Generation ──────────────────────────────────────────────────────


class TestGridGeneration:
    def test_generate_trivial(self):
        rng = random.Random(42)
        puzzle = generate_puzzle(size=3, density=0.5, rng=rng)
        assert len(puzzle["grid"]) == 3
        assert all(len(row) == 3 for row in puzzle["grid"])
        assert puzzle["is_line_solvable"] is True

    def test_generate_easy(self):
        rng = random.Random(123)
        puzzle = generate_puzzle(size=5, density=0.5, rng=rng)
        assert len(puzzle["grid"]) == 5
        assert all(len(row) == 5 for row in puzzle["grid"])
        assert puzzle["is_line_solvable"] is True

    def test_difficulty_to_size(self):
        assert difficulty_to_size("trivial") == 3
        assert difficulty_to_size("easy") == 5
        assert difficulty_to_size("hard") == 10
        assert difficulty_to_size("nightmare") == 15
        assert difficulty_to_size("unknown_fallback") == 5

    def test_grid_round_trips(self):
        """Generated grid should round-trip through derive_clues → line_solve."""
        rng = random.Random(99)
        puzzle = generate_puzzle(size=3, density=0.5, rng=rng, require_line_solvable=True)
        row_clues, col_clues = derive_clues(puzzle["grid"])
        assert row_clues == puzzle["row_clues"]
        assert col_clues == puzzle["col_clues"]
        solved = line_solve(row_clues, col_clues)
        assert solved == puzzle["grid"]


# ── Generator ────────────────────────────────────────────────────────────


class TestGenerator:
    def _default_config(self, **overrides):
        config = {
            "difficulty": ["trivial"],
            "puzzles_per_difficulty": 2,
            "density": 0.5,
            "require_line_solvable": True,
            "clue_format": "inline",
            "require_unique": False,
            "cell_markers": "1,0",
            "partial_solution": False,
        }
        config.update(overrides)
        return config

    def _default_prompt_config(self, **overrides):
        pc = {
            "name": "test",
            "language": "en",
            "user_style": "minimal",
            "system_style": "analytical",
        }
        pc.update(overrides)
        return pc

    def test_generate_batch_count(self):
        gen = PluginRegistry.get("picross").get_generator()
        cases = gen.generate_batch(self._default_config(), self._default_prompt_config(), count=2, seed=42)
        assert len(cases) == 2

    def test_generate_batch_task_type(self):
        gen = PluginRegistry.get("picross").get_generator()
        cases = gen.generate_batch(self._default_config(), self._default_prompt_config(), count=1, seed=42)
        assert cases[0].task_type == "picross"
        assert cases[0].test_id.startswith("picross_")

    def test_generate_batch_prompt_not_empty(self):
        gen = PluginRegistry.get("picross").get_generator()
        cases = gen.generate_batch(self._default_config(), self._default_prompt_config(), count=1, seed=42)
        assert cases[0].prompts["user"].strip() != ""
        assert cases[0].prompts["system"].strip() != ""

    def test_generate_batch_expected_grid(self):
        gen = PluginRegistry.get("picross").get_generator()
        cases = gen.generate_batch(self._default_config(), self._default_prompt_config(), count=1, seed=42)
        grid = cases[0].task_params["expected_grid"]
        assert isinstance(grid, list)
        assert all(isinstance(row, list) for row in grid)
        assert all(cell in (0, 1) for row in grid for cell in row)

    def test_generate_json_format(self):
        gen = PluginRegistry.get("picross").get_generator()
        cases = gen.generate_batch(
            self._default_config(clue_format="json"),
            self._default_prompt_config(),
            count=1, seed=42,
        )
        assert "JSON" in cases[0].prompts["user"] or "json" in cases[0].prompts["user"].lower()

    def test_generate_grid_header_format(self):
        gen = PluginRegistry.get("picross").get_generator()
        cases = gen.generate_batch(
            self._default_config(clue_format="grid_header"),
            self._default_prompt_config(),
            count=1, seed=42,
        )
        # Grid header has the separator line with ─┼
        assert "─┼" in cases[0].prompts["user"]

    def test_generate_partial_solution(self):
        gen = PluginRegistry.get("picross").get_generator()
        cases = gen.generate_batch(
            self._default_config(partial_solution=True, cell_markers="X,."),
            self._default_prompt_config(),
            count=1, seed=42,
        )
        assert "partial_grid" in cases[0].task_params
        partial = cases[0].task_params["partial_grid"]
        assert any(cell == -1 for row in partial for cell in row)

    def test_generate_multilingual(self):
        gen = PluginRegistry.get("picross").get_generator()
        for lang in ["en", "es", "fr", "de", "zh", "ua"]:
            cases = gen.generate_batch(
                self._default_config(),
                self._default_prompt_config(language=lang),
                count=1, seed=42,
            )
            assert cases[0].prompts["user"].strip() != "", f"Empty prompt for {lang}"

    def test_config_schema(self):
        gen = PluginRegistry.get("picross").get_generator()
        schema = gen.get_config_schema()
        names = [f.name for f in schema]
        assert "difficulty" in names
        assert "puzzles_per_difficulty" in names
        assert "density" in names
        assert "clue_format" in names


# ── Parser ───────────────────────────────────────────────────────────────


class TestParser:
    def _params(self, **overrides):
        p = {"grid_size": [3, 3], "filled_cell": "1", "empty_cell": "0"}
        p.update(overrides)
        return p

    def test_parse_clean_grid(self):
        parser = PicrossParser()
        resp = "1 1 0\n0 1 1\n1 0 1"
        result = parser.parse(resp, self._params())
        assert result.value == [[1, 1, 0], [0, 1, 1], [1, 0, 1]]

    def test_parse_with_text_preamble(self):
        parser = PicrossParser()
        resp = "Here is the solution:\n1 1 0\n0 1 1\n1 0 1"
        result = parser.parse(resp, self._params())
        assert result.value == [[1, 1, 0], [0, 1, 1], [1, 0, 1]]

    def test_parse_x_dot_markers(self):
        parser = PicrossParser()
        resp = "X . X\n. X .\nX X X"
        result = parser.parse(resp, self._params(filled_cell="X", empty_cell="."))
        assert result.value == [[1, 0, 1], [0, 1, 0], [1, 1, 1]]

    def test_parse_unicode_markers(self):
        parser = PicrossParser()
        resp = "■ ■ □\n□ ■ ■\n■ □ ■"
        result = parser.parse(resp, self._params())
        assert result.value == [[1, 1, 0], [0, 1, 1], [1, 0, 1]]

    def test_parse_code_block(self):
        parser = PicrossParser()
        resp = "```\n1 1 0\n0 1 1\n1 0 1\n```"
        result = parser.parse(resp, self._params())
        assert result.value == [[1, 1, 0], [0, 1, 1], [1, 0, 1]]

    def test_parse_end_first(self):
        """Parser should use end-first: pick final grid, not intermediate one."""
        parser = PicrossParser()
        resp = (
            "Initial attempt:\n0 0 0\n0 0 0\n0 0 0\n\n"
            "Wait, let me reconsider.\n\n"
            "Final answer:\n1 1 0\n0 1 1\n1 0 1"
        )
        result = parser.parse(resp, self._params())
        assert result.value == [[1, 1, 0], [0, 1, 1], [1, 0, 1]]

    def test_parse_wrong_dimensions_fails(self):
        parser = PicrossParser()
        resp = "1 1\n0 0"
        result = parser.parse(resp, self._params())
        assert result.value is None

    def test_parse_garbage_fails(self):
        parser = PicrossParser()
        resp = "I don't know how to solve this."
        result = parser.parse(resp, self._params())
        assert result.value is None
        assert result.error is not None

    def test_parse_keyword_search(self):
        parser = PicrossParser()
        resp = (
            "Let me work through this...\n"
            "The answer is:\n"
            "Solution:\n"
            "1 0 1\n0 1 0\n1 1 1\n\n"
            "I hope that's correct!"
        )
        result = parser.parse(resp, self._params())
        assert result.value == [[1, 0, 1], [0, 1, 0], [1, 1, 1]]


# ── Evaluator ────────────────────────────────────────────────────────────


class TestEvaluator:
    def _params(self, expected_grid, **overrides):
        p = {
            "expected_grid": expected_grid,
            "grid_size": [len(expected_grid), len(expected_grid[0])],
            "filled_cell": "1",
            "empty_cell": "0",
        }
        p.update(overrides)
        return p

    def test_exact_match(self):
        ev = PicrossEvaluator()
        grid = [[1, 0], [0, 1]]
        parsed = ParsedAnswer(value=grid, raw_response="", parse_strategy="test")
        result = ev.evaluate(parsed, grid, self._params(grid))
        assert result.correct is True
        assert result.match_type == "exact"
        assert result.accuracy == 1.0

    def test_partial_match(self):
        ev = PicrossEvaluator()
        expected = [[1, 0], [0, 1]]
        actual = [[1, 1], [0, 1]]  # 1 cell wrong out of 4
        parsed = ParsedAnswer(value=actual, raw_response="", parse_strategy="test")
        result = ev.evaluate(parsed, expected, self._params(expected))
        assert result.correct is False
        assert result.match_type == "partial"
        assert result.details["raw_accuracy"] == 0.75
        # Normalized: 2*(0.75 - 0.5) = 0.5
        assert abs(result.accuracy - 0.5) < 1e-6

    def test_dimension_mismatch(self):
        ev = PicrossEvaluator()
        expected = [[1, 0], [0, 1]]
        actual = [[1, 0, 1]]  # Wrong dimensions
        parsed = ParsedAnswer(value=actual, raw_response="", parse_strategy="test")
        result = ev.evaluate(parsed, expected, self._params(expected))
        assert result.correct is False
        assert result.match_type == "dimension_mismatch"

    def test_parse_error(self):
        ev = PicrossEvaluator()
        expected = [[1, 0], [0, 1]]
        parsed = ParsedAnswer(value=None, raw_response="gibberish", parse_strategy="none", error="parse failed")
        result = ev.evaluate(parsed, expected, self._params(expected))
        assert result.correct is False
        assert result.match_type == "parse_error"
        assert result.accuracy == 0.0

    def test_all_wrong_gives_negative_normalized(self):
        ev = PicrossEvaluator()
        expected = [[1, 1], [1, 1]]
        actual = [[0, 0], [0, 0]]  # All wrong → raw 0.0 → normalized 2*(0-0.5) = -1.0
        parsed = ParsedAnswer(value=actual, raw_response="", parse_strategy="test")
        result = ev.evaluate(parsed, expected, self._params(expected))
        assert result.accuracy == -1.0

    def test_aggregate_results(self):
        ev = PicrossEvaluator()
        results = [
            EvaluationResult(correct=True, match_type="exact", accuracy=1.0, details={"raw_accuracy": 1.0}),
            EvaluationResult(correct=False, match_type="partial", accuracy=0.5, details={"raw_accuracy": 0.75}),
            EvaluationResult(correct=False, match_type="parse_error", accuracy=0.0, details={}),
        ]
        agg = ev.aggregate_results(results)
        assert agg["total"] == 3
        assert agg["correct"] == 1
        assert abs(agg["accuracy"] - 1 / 3) < 1e-6
        assert "normalized_accuracy" in agg
