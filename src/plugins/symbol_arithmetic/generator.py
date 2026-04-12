"""
Symbol Arithmetic Test Case Generator

Generates arbitrary binary-operation tables over abstract symbol sets and
expressions requiring sequential lookup to evaluate.  Computes ground-truth
answers plus commutativity / associativity assumption traces for the evaluator.
"""
from __future__ import annotations

import math
import random
from datetime import datetime
from itertools import product
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import ConfigField, TestCase, TestCaseGenerator

# ── symbol pools ────────────────────────────────────────────────────────
ALPHA_SYMBOLS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
EMOJI_SYMBOLS = ["🔴", "🟢", "🔵", "🟠", "🟡", "🟣", "⚫️", "⚪️", "🟤", "🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "⬛️", "⬜️", "🟫"]
NONSENSE_SYMBOLS = ["FOO", "BAR", "BAZ", "QUX", "ZAP", "MIX"]

OPERATOR_SYMBOL = "★"

DIFFICULTY_PRESETS: Dict[str, Dict[str, Any]] = {
    "easy": dict(set_size=3, operation_class="commutative", expression_depth=1,
                 symbol_type="alpha", table_completeness="full"),
    "medium": dict(set_size=4, operation_class="non_commutative", expression_depth=2,
                   symbol_type="alpha", table_completeness="full"),
    "hard": dict(set_size=5, operation_class="non_associative", expression_depth=3,
                 symbol_type="emoji", table_completeness="full"),
    "nightmare": dict(set_size=6, operation_class="arbitrary", expression_depth=4,
                      symbol_type="emoji", table_completeness="partial"),
}


# ── expression tree ─────────────────────────────────────────────────────

class _Node:
    """Binary expression tree node."""
    __slots__ = ("left", "right", "symbol")

    def __init__(self, symbol: Optional[str] = None,
                 left: Optional["_Node"] = None,
                 right: Optional["_Node"] = None):
        self.symbol = symbol    # non-None for leaves
        self.left = left
        self.right = right

    @property
    def is_leaf(self) -> bool:
        return self.symbol is not None

    # ── rendering ───────────────────────────────────────────────────
    def to_str(self, op: str = OPERATOR_SYMBOL) -> str:
        if self.is_leaf:
            return self.symbol
        return f"({self.left.to_str(op)} {op} {self.right.to_str(op)})"


def _random_tree(depth: int, symbols: List[str], rng: random.Random) -> _Node:
    """Build a random full binary tree of the given depth.

    depth=1 → one operation (two leaf children).
    depth=N → root op whose children are trees of depth up to N-1,
              with at least one child at depth N-1 (guarantees stated depth).
    """
    if depth <= 0:
        return _Node(symbol=rng.choice(symbols))
    if depth == 1:
        return _Node(left=_Node(symbol=rng.choice(symbols)),
                     right=_Node(symbol=rng.choice(symbols)))

    # Guarantee we reach the requested depth on at least one side
    deep_side = rng.choice(["left", "right"])
    if deep_side == "left":
        left = _random_tree(depth - 1, symbols, rng)
        right = _random_tree(rng.randint(0, depth - 1), symbols, rng)
    else:
        left = _random_tree(rng.randint(0, depth - 1), symbols, rng)
        right = _random_tree(depth - 1, symbols, rng)
    return _Node(left=left, right=right)


# ── table evaluation ────────────────────────────────────────────────────

_UNDEFINED = "UNDEFINED"


def _evaluate(node: _Node, table: Dict[str, Dict[str, Optional[str]]]) -> Optional[str]:
    """Evaluate an expression tree against *table*.

    Returns the resulting symbol, or ``None`` if any lookup hits a
    missing / ``None`` cell (partial-table case).
    """
    if node.is_leaf:
        return node.symbol
    left_val = _evaluate(node.left, table)
    if left_val is None:
        return None
    right_val = _evaluate(node.right, table)
    if right_val is None:
        return None
    return table.get(left_val, {}).get(right_val)


# ── commutativity trace ─────────────────────────────────────────────────

def _commuted_variants(node: _Node) -> List[_Node]:
    """Generate expression variants where at least one op node has operands swapped.

    For k internal nodes there are 2^k - 1 non-identity variants. We enumerate
    them via bitmask.
    """
    ops = _collect_ops(node)
    n = len(ops)
    if n == 0:
        return []
    variants: List[_Node] = []
    for mask in range(1, 1 << n):          # skip 0 (identity)
        swap_set = {id(ops[i]) for i in range(n) if mask & (1 << i)}
        variants.append(_clone_with_swaps(node, swap_set))
    return variants


def _collect_ops(node: _Node) -> List[_Node]:
    """Collect all internal (non-leaf) nodes in pre-order."""
    if node.is_leaf:
        return []
    return [node] + _collect_ops(node.left) + _collect_ops(node.right)


def _clone_with_swaps(node: _Node, swap_ids: set) -> _Node:
    if node.is_leaf:
        return _Node(symbol=node.symbol)
    left = _clone_with_swaps(node.left, swap_ids)
    right = _clone_with_swaps(node.right, swap_ids)
    if id(node) in swap_ids:
        left, right = right, left
    return _Node(left=left, right=right)


# ── associativity trace (alternative bracketings) ───────────────────────

def _all_bracketings(leaves: List[str]) -> List[_Node]:
    """Enumerate all full-binary-tree structures over *leaves* (Catalan number).

    Safe up to ~7 leaves (Catalan(6)=132).
    """
    if len(leaves) == 1:
        return [_Node(symbol=leaves[0])]
    trees: List[_Node] = []
    for i in range(1, len(leaves)):
        for lt in _all_bracketings(leaves[:i]):
            for rt in _all_bracketings(leaves[i:]):
                trees.append(_Node(left=lt, right=rt))
    return trees


def _collect_leaves(node: _Node) -> List[str]:
    """Collect leaf symbols in left-to-right order."""
    if node.is_leaf:
        return [node.symbol]
    return _collect_leaves(node.left) + _collect_leaves(node.right)


def _regrouped_variants(node: _Node) -> List[_Node]:
    """Generate alternative bracketings of the same leaf sequence.

    Returns all bracketings *except* the one structurally identical to *node*
    (detected by matching the expression string).
    """
    leaves = _collect_leaves(node)
    if len(leaves) > 7:
        # Catalan explosion guard — skip for very large expressions
        return []
    original_str = node.to_str()
    return [t for t in _all_bracketings(leaves) if t.to_str() != original_str]


# ── table generation ────────────────────────────────────────────────────

def _generate_table(
    symbols: List[str],
    operation_class: str,
    rng: random.Random,
    max_attempts: int = 200,
) -> Dict[str, Dict[str, str]]:
    """Generate a random operation table satisfying *operation_class*."""
    n = len(symbols)

    for _ in range(max_attempts):
        table: Dict[str, Dict[str, str]] = {}
        for a in symbols:
            table[a] = {}
            for b in symbols:
                table[a][b] = rng.choice(symbols)

        if operation_class == "commutative":
            # Mirror upper triangle
            for i, a in enumerate(symbols):
                for j, b in enumerate(symbols):
                    if j > i:
                        table[b][a] = table[a][b]
            return table

        if operation_class == "non_commutative":
            if _has_non_commutative_pair(table, symbols):
                return table
            # Force one asymmetric pair
            a, b = rng.sample(symbols, 2)
            others = [s for s in symbols if s != table[a][b]]
            if others:
                table[b][a] = rng.choice(others)
                return table
            continue

        if operation_class == "non_associative":
            if _is_non_associative(table, symbols):
                return table
            continue  # retry until we get one

        # arbitrary — anything goes
        return table

    # If max_attempts exhausted (very unlikely), return last table
    return table


def _has_non_commutative_pair(table, symbols) -> bool:
    for a in symbols:
        for b in symbols:
            if table[a][b] != table[b][a]:
                return True
    return False


def _is_non_associative(table, symbols) -> bool:
    for a, b, c in product(symbols, repeat=3):
        ab = table[a][b]
        left = table[ab][c]
        bc = table[b][c]
        right = table[a][bc]
        if left != right:
            return True
    return False


def _make_partial(
    table: Dict[str, Dict[str, str]],
    symbols: List[str],
    fraction: float,
    rng: random.Random,
) -> Dict[str, Dict[str, Optional[str]]]:
    """Remove some entries from *table* (set to None)."""
    n = len(symbols)
    total = n * n
    to_remove = max(1, int(math.floor(fraction * total)))
    all_pairs = [(a, b) for a in symbols for b in symbols]
    rng.shuffle(all_pairs)
    out: Dict[str, Dict[str, Optional[str]]] = {
        a: dict(row) for a, row in table.items()
    }
    for a, b in all_pairs[:to_remove]:
        out[a][b] = None
    return out


# ── table formatting ────────────────────────────────────────────────────

def _format_matrix(table: Dict[str, Dict[str, Optional[str]]],
                   symbols: List[str], op: str = OPERATOR_SYMBOL) -> str:
    """Render the table as a row/column matrix."""
    # Determine column width (max symbol width + 1)
    w = max(len(s) for s in symbols + [op]) + 1
    # Header row
    header = op.ljust(w) + "| " + "  ".join(s.ljust(w) for s in symbols)
    sep = "-" * w + "+" + "-" * (len(symbols) * (w + 2))
    rows = [header, sep]
    for a in symbols:
        cells = []
        for b in symbols:
            val = table[a].get(b)
            cells.append(("?" if val is None else val).ljust(w))
        rows.append(a.ljust(w) + "| " + "  ".join(cells))
    return "\n".join(rows)


def _format_pairs(table: Dict[str, Dict[str, Optional[str]]],
                  symbols: List[str], op: str = OPERATOR_SYMBOL) -> str:
    """Render the table as enumerated pairs."""
    lines = []
    for a in symbols:
        for b in symbols:
            val = table[a].get(b)
            rhs = "?" if val is None else val
            lines.append(f"{a} {op} {b} = {rhs}")
    return "\n".join(lines)


# ── generator class ─────────────────────────────────────────────────────

class SymbolArithmeticGenerator(TestCaseGenerator):
    """Test case generator for the symbol_arithmetic benchmark."""

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None,
    ) -> List[TestCase]:
        rng = random.Random(seed if seed is not None else 42)

        # ── resolve difficulty preset ───────────────────────────────
        difficulty = config.get("difficulty")
        if difficulty and difficulty in DIFFICULTY_PRESETS:
            effective = {**DIFFICULTY_PRESETS[difficulty], **{
                k: v for k, v in config.items()
                if k not in ("difficulty",) and k in DIFFICULTY_PRESETS[difficulty]
                and v != DIFFICULTY_PRESETS[difficulty].get(k)  # keep explicit overrides
            }}
        else:
            effective = dict(config)

        set_size: int = int(effective.get("set_size", 4))
        expression_depth: int = int(effective.get("expression_depth", 2))
        operation_class: str = effective.get("operation_class", "arbitrary")
        table_completeness: str = effective.get("table_completeness", "full")
        table_format: str = effective.get("table_format", "matrix")
        symbol_type: str = effective.get("symbol_type", "alpha")
        partial_frac: float = float(effective.get("partial_missing_fraction", 0.15))

        # ── choose symbol set ───────────────────────────────────────
        pool = {"alpha": ALPHA_SYMBOLS, "emoji": EMOJI_SYMBOLS,
                "nonsense_words": NONSENSE_SYMBOLS}
        symbols = random.sample(pool.get(symbol_type, ALPHA_SYMBOLS), set_size)

        # ── prompt config ───────────────────────────────────────────
        language = prompt_config.get("language", "en")
        user_style = prompt_config.get("user_style", "minimal")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")

        # ── generate one table per batch (stable across cases) ──────
        full_table = _generate_table(symbols, operation_class, rng)
        if table_completeness == "partial":
            table = _make_partial(full_table, symbols, partial_frac, rng)
        else:
            table: Dict[str, Dict[str, Optional[str]]] = full_table  # type: ignore[assignment]

        # Format table string
        if table_format == "pairs":
            table_str = _format_pairs(table, symbols)
        else:
            table_str = _format_matrix(table, symbols)

        symbol_set_str = ", ".join(symbols)

        tests: List[TestCase] = []

        for idx in range(count):
            # ── build expression tree ───────────────────────────────
            tree = _random_tree(expression_depth, symbols, rng)
            expr_str = tree.to_str(OPERATOR_SYMBOL)

            # ── ground truth ────────────────────────────────────────
            result = _evaluate(tree, table)
            expected = result if result is not None else _UNDEFINED

            # ── commuted trace ──────────────────────────────────────
            commuted_answers: List[str] = []
            for variant in _commuted_variants(tree):
                val = _evaluate(variant, table)
                val_str = val if val is not None else _UNDEFINED
                if val_str != expected:
                    commuted_answers.append(val_str)
            commuted_answers = sorted(set(commuted_answers))

            # ── regrouped trace ─────────────────────────────────────
            regrouped_answers: List[str] = []
            for variant in _regrouped_variants(tree):
                val = _evaluate(variant, table)
                val_str = val if val is not None else _UNDEFINED
                if val_str != expected:
                    regrouped_answers.append(val_str)
            regrouped_answers = sorted(set(regrouped_answers))

            # ── prompts ─────────────────────────────────────────────
            user_prompt, system_prompt, full_prompt = self._build_prompts_yaml(
                "symbol_arithmetic", language, user_style, system_style,
                symbol_set=symbol_set_str,
                operation_table=table_str,
                expression=expr_str,
                operator_symbol=OPERATOR_SYMBOL,
            )

            # ── serialisable table (lists, not nested dicts w/ None) ────
            serial_table: Dict[str, Dict[str, Optional[str]]] = {
                a: {b: table[a][b] for b in symbols} for a in symbols
            }

            tests.append(TestCase(
                test_id=f"symbol_arithmetic_{idx:04d}",
                task_type="symbol_arithmetic",
                config_name=config_name,
                prompts={
                    "system": system_prompt,
                    "user": user_prompt,
                    "full": full_prompt,
                },
                task_params={
                    "expected_answer": expected,
                    "expression": expr_str,
                    "operation_table": serial_table,
                    "symbols": symbols,
                    "operation_class": operation_class,
                    "table_completeness": table_completeness,
                    "table_format": table_format,
                    "symbol_type": symbol_type,
                    "expression_depth": expression_depth,
                    "commuted_answers": commuted_answers,
                    "regrouped_answers": regrouped_answers,
                },
                prompt_metadata={
                    "user_style": user_style,
                    "system_style": system_style,
                    "language": language,
                },
                generation_metadata={
                    "seed": seed,
                    "generator_version": "1.0.0",
                    "created_at": datetime.now().isoformat(),
                },
            ))

        return tests

    # ── config schema (for web UI) ──────────────────────────────────────

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "set_size": 4,
            "expression_depth": 2,
            "operation_class": "arbitrary",
            "table_completeness": "full",
            "table_format": "matrix",
            "symbol_type": "alpha",
            "count": 10,
            "partial_missing_fraction": 0.15,
            "difficulty": "medium",
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(
                name="difficulty", label="Difficulty preset",
                field_type="select", default="medium",
                options=["easy", "medium", "hard", "nightmare"],
                help="Overrides individual fields below with curated combinations",
            ),
            ConfigField(
                name="count", label="Number of test cases",
                field_type="number", default=10, min_value=1, max_value=200,
            ),
            ConfigField(
                name="set_size", label="Symbol set size",
                field_type="number", default=4, min_value=3, max_value=6,
                help="3=easy, 6=hard",
            ),
            ConfigField(
                name="expression_depth", label="Expression depth",
                field_type="number", default=2, min_value=1, max_value=5,
                help="Number of nested operations (1=single lookup, 5=deep chain)",
            ),
            ConfigField(
                name="operation_class", label="Operation class",
                field_type="select", default="arbitrary",
                options=["commutative", "non_commutative", "non_associative", "arbitrary"],
                help="Controls which algebraic properties the generated table has",
            ),
            ConfigField(
                name="table_completeness", label="Table completeness",
                field_type="select", default="full",
                options=["full", "partial"],
                help="Partial tables have some entries removed — model should detect & flag",
            ),
            ConfigField(
                name="table_format", label="Table display format",
                field_type="select", default="matrix",
                options=["matrix", "pairs"],
                help="How the operation table is presented in the prompt",
            ),
            ConfigField(
                name="symbol_type", label="Symbol type",
                field_type="select", default="alpha",
                options=["alpha", "emoji", "nonsense_words"],
            ),
            ConfigField(
                name="partial_missing_fraction", label="Partial table missing fraction",
                field_type="number", default=0.15, min_value=0.05, max_value=0.5,
                step=0.05, group="advanced",
                help="Fraction of table entries removed when table_completeness=partial",
            ),
        ]
