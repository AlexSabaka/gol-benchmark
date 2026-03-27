"""
Integration tests for the symbol_arithmetic plugin.

Covers: table generation properties, expression evaluation, partial-table
undefined detection, commutativity/associativity traces, parser strategies,
evaluator match-type classification, difficulty presets, and end-to-end
plugin-registry integration.
"""
from __future__ import annotations

import random
from itertools import product

import pytest

# ── generator internals (white-box tests) ───────────────────────────────
from src.plugins.symbol_arithmetic.generator import (
    ALPHA_SYMBOLS,
    DIFFICULTY_PRESETS,
    EMOJI_SYMBOLS,
    NONSENSE_SYMBOLS,
    OPERATOR_SYMBOL,
    _UNDEFINED,
    _Node,
    _all_bracketings,
    _collect_leaves,
    _commuted_variants,
    _evaluate,
    _format_matrix,
    _format_pairs,
    _generate_table,
    _has_non_commutative_pair,
    _is_non_associative,
    _make_partial,
    _random_tree,
    _regrouped_variants,
)
from src.plugins.symbol_arithmetic.evaluator import SymbolArithmeticEvaluator
from src.plugins.symbol_arithmetic.parser import SymbolArithmeticParser
from src.plugins.base import ParsedAnswer


# ═══════════════════════════════════════════════════════════════════════
# 1. Table generation — algebraic properties
# ═══════════════════════════════════════════════════════════════════════

class TestTableGeneration:

    def test_commutative_table_is_symmetric(self):
        rng = random.Random(42)
        syms = ALPHA_SYMBOLS[:4]
        table = _generate_table(syms, "commutative", rng)
        for a in syms:
            for b in syms:
                assert table[a][b] == table[b][a], f"{a},{b}"

    def test_non_commutative_has_asymmetric_pair(self):
        rng = random.Random(42)
        syms = ALPHA_SYMBOLS[:4]
        table = _generate_table(syms, "non_commutative", rng)
        assert _has_non_commutative_pair(table, syms)

    def test_non_associative_has_counterexample(self):
        rng = random.Random(42)
        syms = ALPHA_SYMBOLS[:4]
        table = _generate_table(syms, "non_associative", rng)
        assert _is_non_associative(table, syms)

    def test_arbitrary_returns_valid_table(self):
        rng = random.Random(42)
        syms = ALPHA_SYMBOLS[:5]
        table = _generate_table(syms, "arbitrary", rng)
        for a in syms:
            for b in syms:
                assert table[a][b] in syms

    def test_partial_table_has_none_entries(self):
        rng = random.Random(42)
        syms = ALPHA_SYMBOLS[:4]
        table = _generate_table(syms, "arbitrary", rng)
        partial = _make_partial(table, syms, 0.25, rng)
        none_count = sum(1 for a in syms for b in syms if partial[a][b] is None)
        assert none_count >= 1


# ═══════════════════════════════════════════════════════════════════════
# 2. Expression evaluation — ground truth
# ═══════════════════════════════════════════════════════════════════════

class TestExpressionEvaluation:

    def _simple_table(self):
        """A ★ B = C, A ★ A = A, B ★ A = B, etc."""
        return {
            "A": {"A": "A", "B": "C", "C": "B"},
            "B": {"A": "B", "B": "A", "C": "C"},
            "C": {"A": "C", "B": "B", "C": "A"},
        }

    def test_depth_1_evaluation(self):
        table = self._simple_table()
        # A ★ B → lookup table["A"]["B"] → "C"
        tree = _Node(left=_Node(symbol="A"), right=_Node(symbol="B"))
        assert _evaluate(tree, table) == "C"

    def test_depth_2_evaluation(self):
        table = self._simple_table()
        # (A ★ B) ★ C → C ★ C → lookup table["C"]["C"] → "A"
        inner = _Node(left=_Node(symbol="A"), right=_Node(symbol="B"))
        tree = _Node(left=inner, right=_Node(symbol="C"))
        assert _evaluate(tree, table) == "A"

    def test_partial_table_undefined(self):
        table = {
            "A": {"A": "A", "B": None},
            "B": {"A": "B", "B": "A"},
        }
        tree = _Node(left=_Node(symbol="A"), right=_Node(symbol="B"))
        assert _evaluate(tree, table) is None

    def test_random_tree_evaluates(self):
        rng = random.Random(99)
        syms = ALPHA_SYMBOLS[:3]
        table = _generate_table(syms, "arbitrary", rng)
        tree = _random_tree(3, syms, rng)
        result = _evaluate(tree, table)
        assert result in syms  # full table → always defined


# ═══════════════════════════════════════════════════════════════════════
# 3. Commutativity trace
# ═══════════════════════════════════════════════════════════════════════

class TestCommutativityTrace:

    def test_single_op_commuted(self):
        # Non-commutative table: A★B=C, B★A=B
        table = {
            "A": {"A": "A", "B": "C"},
            "B": {"A": "B", "B": "B"},
        }
        tree = _Node(left=_Node(symbol="A"), right=_Node(symbol="B"))
        original = _evaluate(tree, table)
        assert original == "C"

        variants = _commuted_variants(tree)
        assert len(variants) == 1  # only one internal node → 1 variant
        swapped_val = _evaluate(variants[0], table)
        assert swapped_val == "B"  # B ★ A = B

    def test_commutative_table_no_trace(self):
        """If the table is commutative, all commuted answers equal the original."""
        table = {
            "A": {"A": "A", "B": "C"},
            "B": {"A": "C", "B": "B"},
        }
        tree = _Node(left=_Node(symbol="A"), right=_Node(symbol="B"))
        original = _evaluate(tree, table)
        for v in _commuted_variants(tree):
            assert _evaluate(v, table) == original


# ═══════════════════════════════════════════════════════════════════════
# 4. Associativity trace (regrouping)
# ═══════════════════════════════════════════════════════════════════════

class TestAssociativityTrace:

    def test_depth2_regrouped(self):
        # (A ★ B) ★ C  vs  A ★ (B ★ C)
        table = {
            "A": {"A": "B", "B": "C", "C": "A"},
            "B": {"A": "A", "B": "B", "C": "C"},
            "C": {"A": "C", "B": "A", "C": "B"},
        }
        # Original: (A ★ B) ★ C = C ★ C = B
        inner = _Node(left=_Node(symbol="A"), right=_Node(symbol="B"))
        tree = _Node(left=inner, right=_Node(symbol="C"))
        assert _evaluate(tree, table) == "B"

        variants = _regrouped_variants(tree)
        assert len(variants) >= 1
        # Alternative: A ★ (B ★ C) = A ★ C = A
        alt_vals = {_evaluate(v, table) for v in variants}
        assert "A" in alt_vals

    def test_all_bracketings_count(self):
        """Catalan(n-1) bracketings for n leaves."""
        # 3 leaves → Catalan(2) = 2 bracketings
        assert len(_all_bracketings(["A", "B", "C"])) == 2
        # 4 leaves → Catalan(3) = 5
        assert len(_all_bracketings(["A", "B", "C", "D"])) == 5


# ═══════════════════════════════════════════════════════════════════════
# 5. Table formatting
# ═══════════════════════════════════════════════════════════════════════

class TestTableFormatting:

    def test_matrix_format_contains_all_symbols(self):
        table = {"A": {"A": "B", "B": "A"}, "B": {"A": "A", "B": "B"}}
        text = _format_matrix(table, ["A", "B"])
        assert "A" in text and "B" in text
        assert OPERATOR_SYMBOL in text

    def test_pairs_format_line_count(self):
        syms = ["A", "B", "C"]
        table = {a: {b: "A" for b in syms} for a in syms}
        text = _format_pairs(table, syms)
        assert len(text.strip().split("\n")) == 9  # 3×3

    def test_partial_table_shows_question_marks(self):
        table = {"A": {"A": "B", "B": None}, "B": {"A": None, "B": "A"}}
        text = _format_matrix(table, ["A", "B"])
        assert "?" in text


# ═══════════════════════════════════════════════════════════════════════
# 6. Parser strategies
# ═══════════════════════════════════════════════════════════════════════

class TestParser:
    SYMS = ["A", "B", "C"]
    PARAMS = {"symbols": ["A", "B", "C"]}

    def _parse(self, response: str):
        return SymbolArithmeticParser().parse(response, self.PARAMS)

    def test_undefined_detection(self):
        pa = self._parse("The lookup is not defined in the table.")
        assert pa.value == "UNDEFINED"
        assert pa.parse_strategy == "undefined_detection"

    def test_boxed_symbol(self):
        pa = self._parse("Working... so \\boxed{B}")
        assert pa.value == "B"
        assert pa.parse_strategy == "boxed_symbol"

    def test_labelled_answer(self):
        pa = self._parse("Step 1: ... Step 2: ... Final answer: C")
        assert pa.value == "C"
        assert pa.parse_strategy == "labelled_answer"

    def test_equals_pattern(self):
        pa = self._parse("(A ★ B) ★ C = B")
        assert pa.value == "B"
        assert pa.parse_strategy == "equals_pattern"

    def test_bold_symbol(self):
        pa = self._parse("The result is **A**.")
        assert pa.value == "A"
        assert pa.parse_strategy == "bold_symbol"

    def test_last_symbol_fallback(self):
        pa = self._parse("First I get A, then B, then finally C")
        assert pa.value == "C"
        assert pa.parse_strategy == "last_symbol"

    def test_empty_response(self):
        pa = self._parse("")
        assert not pa.success
        assert pa.parse_strategy == "failed"

    def test_no_valid_symbol(self):
        pa = self._parse("I think the answer is 42")
        assert not pa.success

    def test_emoji_symbols(self):
        params = {"symbols": ["🔴", "🟢", "🔵"]}
        pa = SymbolArithmeticParser().parse("The result is 🟢", params)
        assert pa.value == "🟢"

    def test_nonsense_word_symbols(self):
        params = {"symbols": ["FOO", "BAR", "BAZ"]}
        pa = SymbolArithmeticParser().parse("Final answer: BAZ", params)
        assert pa.value == "BAZ"


# ═══════════════════════════════════════════════════════════════════════
# 7. Evaluator match types
# ═══════════════════════════════════════════════════════════════════════

class TestEvaluator:
    ev = SymbolArithmeticEvaluator()
    base_params = {
        "expected_answer": "C",
        "expression": "(A ★ B)",
        "operation_class": "non_commutative",
        "expression_depth": 1,
        "table_format": "matrix",
        "symbol_type": "alpha",
        "table_completeness": "full",
        "commuted_answers": ["B"],
        "regrouped_answers": ["A"],
    }

    def _pa(self, value, strategy="last_symbol", error=None):
        return ParsedAnswer(value=value, raw_response="...", parse_strategy=strategy, error=error)

    def test_correct(self):
        r = self.ev.evaluate(self._pa("C"), "C", self.base_params)
        assert r.correct and r.match_type == "correct"

    def test_wrong_assumed_commutative(self):
        r = self.ev.evaluate(self._pa("B"), "C", self.base_params)
        assert not r.correct and r.match_type == "wrong_assumed_commutative"

    def test_wrong_assumed_associative(self):
        r = self.ev.evaluate(self._pa("A"), "C", self.base_params)
        assert not r.correct and r.match_type == "wrong_assumed_associative"

    def test_wrong_arbitrary(self):
        r = self.ev.evaluate(self._pa("D"), "C", self.base_params)
        assert not r.correct and r.match_type == "wrong_arbitrary"

    def test_undefined_correct(self):
        params = {**self.base_params, "expected_answer": "UNDEFINED"}
        r = self.ev.evaluate(self._pa("UNDEFINED"), "UNDEFINED", params)
        assert r.correct and r.match_type == "undefined_correct"

    def test_undefined_wrong(self):
        params = {**self.base_params, "expected_answer": "UNDEFINED"}
        r = self.ev.evaluate(self._pa("C"), "UNDEFINED", params)
        assert not r.correct and r.match_type == "undefined_wrong"

    def test_undefined_missed(self):
        r = self.ev.evaluate(self._pa("UNDEFINED"), "C", self.base_params)
        assert not r.correct and r.match_type == "undefined_missed"

    def test_parse_error(self):
        r = self.ev.evaluate(
            self._pa(None, strategy="failed", error="nope"), "C", self.base_params
        )
        assert not r.correct and r.match_type == "parse_error"

    def test_aggregate_results(self):
        results = [
            self.ev.evaluate(self._pa("C"), "C", self.base_params),
            self.ev.evaluate(self._pa("B"), "C", self.base_params),  # commutative
            self.ev.evaluate(self._pa("D"), "C", self.base_params),  # arbitrary
        ]
        agg = self.ev.aggregate_results(results)
        assert agg["accuracy"] == pytest.approx(1 / 3)
        assert agg["match_types"]["correct"] == 1
        assert agg["match_types"]["wrong_assumed_commutative"] == 1
        assert agg["commutativity_assumption_rate"] == pytest.approx(0.5)


# ═══════════════════════════════════════════════════════════════════════
# 8. End-to-end plugin integration
# ═══════════════════════════════════════════════════════════════════════

class TestPluginIntegration:

    def test_registry_discovery(self):
        from src.plugins import PluginRegistry
        p = PluginRegistry.get("symbol_arithmetic")
        assert p is not None
        assert p.task_type == "symbol_arithmetic"
        assert p.display_name == "Symbol Arithmetic"

    def test_generate_parse_evaluate_pipeline(self):
        from src.plugins import PluginRegistry
        plugin = PluginRegistry.get("symbol_arithmetic")
        generator = plugin.get_generator()
        parser = plugin.get_parser()
        evaluator = plugin.get_evaluator()

        cases = generator.generate_batch(
            config={"set_size": 3, "expression_depth": 1,
                    "operation_class": "commutative", "table_completeness": "full",
                    "symbol_type": "alpha"},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=5, seed=42,
        )
        assert len(cases) == 5

        for tc in cases:
            expected = tc.task_params["expected_answer"]
            # Simulate a "correct" model response
            fake_response = f"After looking up the table, the answer is {expected}."
            pa = parser.parse(fake_response, tc.task_params)
            ev = evaluator.evaluate(pa, expected, tc.task_params)
            assert ev.correct, f"Failed on {tc.test_id}: expected {expected}, got {pa.value}"

    def test_config_schema_returns_fields(self):
        from src.plugins import PluginRegistry
        plugin = PluginRegistry.get("symbol_arithmetic")
        schema = plugin.get_generator().get_config_schema()
        names = {f.name for f in schema}
        assert "difficulty" in names
        assert "set_size" in names
        assert "operation_class" in names


# ═══════════════════════════════════════════════════════════════════════
# 9. Difficulty presets
# ═══════════════════════════════════════════════════════════════════════

class TestDifficultyPresets:

    def _gen(self, difficulty: str, count: int = 3):
        from src.plugins import PluginRegistry
        gen = PluginRegistry.get("symbol_arithmetic").get_generator()
        return gen.generate_batch(
            config={"difficulty": difficulty},
            prompt_config={"user_style": "minimal", "system_style": "analytical"},
            count=count, seed=7,
        )

    def test_easy_uses_3_symbols(self):
        cases = self._gen("easy")
        assert len(cases[0].task_params["symbols"]) == 3
        assert cases[0].task_params["operation_class"] == "commutative"

    def test_medium_uses_4_symbols_non_commutative(self):
        cases = self._gen("medium")
        assert len(cases[0].task_params["symbols"]) == 4
        assert cases[0].task_params["operation_class"] == "non_commutative"

    def test_hard_uses_emoji(self):
        cases = self._gen("hard")
        assert cases[0].task_params["symbol_type"] == "emoji"
        assert cases[0].task_params["operation_class"] == "non_associative"

    def test_nightmare_is_partial(self):
        cases = self._gen("nightmare")
        assert cases[0].task_params["table_completeness"] == "partial"
        assert len(cases[0].task_params["symbols"]) == 6
