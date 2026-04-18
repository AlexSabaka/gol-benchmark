"""Picture Algebra Test Case Generator.

Generates small systems of linear equations whose variables are rendered as
emoji / alpha / nonsense tokens, producing reproducible integer solutions
verified with sympy.  Trick cases (underdetermined / inconsistent) are mixed
in at a configurable rate so sensitivity to impossible systems can be
measured inside the same testset.
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sympy import Matrix, Rational, linsolve, symbols as sympy_symbols

from src.plugins.base import ConfigField, TestCase, TestCaseGenerator
from src.plugins.picture_algebra.data.emoji_pools import EMOJI_POOLS

# ── constants ───────────────────────────────────────────────────────────

ALPHA_SYMBOLS = ["x", "y", "z"]
NONSENSE_SYMBOLS = ["FOO", "BAR", "BAZ"]

DETERMINACY_UNIQUE = "unique"
DETERMINACY_UNDER = "underdetermined"
DETERMINACY_INCONSISTENT = "inconsistent"

SENTINEL_CANNOT_DETERMINE = "CANNOT_BE_DETERMINED"
SENTINEL_NO_SOLUTION = "NO_SOLUTION"

# Localized phrases for the query-target slot in prompts.  The i18n body
# interpolates one of these via ``{query_target}``.
_QUERY_TARGET_ALL = {
    "en": "all variables",
    "es": "todas las variables",
    "fr": "toutes les variables",
    "de": "alle Variablen",
    "zh": "所有变量",
    "ua": "всі змінні",
}


DIFFICULTY_PRESETS: Dict[str, Dict[str, Any]] = {
    "easy": dict(
        num_variables=2, num_equations=2, operations="add_only",
        solution_range_min=1, solution_range_max=10, coefficient_range=3,
        surface_form="alpha", emoji_category="food",
        question_scope="all", trick_rate=0.0,
    ),
    "medium": dict(
        num_variables=2, num_equations=2, operations="add_subtract",
        solution_range_min=1, solution_range_max=20, coefficient_range=5,
        surface_form="emoji", emoji_category="food",
        question_scope="all", trick_rate=0.0,
    ),
    "hard": dict(
        num_variables=3, num_equations=3, operations="add_multiply",
        solution_range_min=1, solution_range_max=20, coefficient_range=5,
        surface_form="emoji", emoji_category="mixed",
        question_scope="all", trick_rate=0.1,
    ),
    "nightmare": dict(
        num_variables=3, num_equations=4, operations="all",
        solution_range_min=1, solution_range_max=30, coefficient_range=7,
        surface_form="emoji", emoji_category="mixed",
        question_scope="specific", trick_rate=0.25,
    ),
}


# ── coefficient sampling ────────────────────────────────────────────────

def _coefficient_pool(operations: str, coef_range: int) -> List[int]:
    """Build the set of allowed coefficients for an equation term.

    `add_only` and `add_multiply` both keep terms positive; the difference
    lives at the prompt-rendering layer — add_multiply is rendered with an
    explicit multiplication glyph (2·🍎) whereas add_only uses repeated
    addition (🍎 + 🍎).
    """
    if operations == "add_only":
        return list(range(1, coef_range + 1))
    if operations == "add_subtract":
        return [c for c in range(-coef_range, coef_range + 1) if c != 0]
    if operations == "add_multiply":
        return list(range(1, coef_range + 1))
    # "all"
    return [c for c in range(-coef_range, coef_range + 1) if c != 0]


# ── linear system generation ────────────────────────────────────────────

def _sample_solutions(n: int, lo: int, hi: int, rng: random.Random) -> List[int]:
    return [rng.randint(lo, hi) for _ in range(n)]


def _build_equation(
    num_vars: int,
    solutions: List[int],
    coef_pool: List[int],
    rng: random.Random,
) -> Tuple[List[int], int]:
    """Sample one equation with at least two non-zero coefficients.

    We allow a random subset of variables to have coefficient 0 so equations
    vary in sparsity, but keep at least two non-zero terms for the equation
    to be informative.
    """
    while True:
        coeffs = [rng.choice(coef_pool + [0]) for _ in range(num_vars)]
        if sum(1 for c in coeffs if c != 0) >= 2:
            break
    rhs = sum(c * s for c, s in zip(coeffs, solutions))
    return coeffs, rhs


def _verify_unique(
    coeffs_list: List[List[int]],
    rhs_list: List[int],
    expected_solutions: List[int],
) -> bool:
    """Verify the system has a unique integer solution matching *expected*."""
    num_vars = len(expected_solutions)
    if not coeffs_list:
        return False
    sym_list = sympy_symbols(f"pa_v0:{num_vars}")
    A = Matrix(coeffs_list)
    b = Matrix(rhs_list)
    try:
        solset = linsolve((A, b), *sym_list)
    except Exception:
        return False
    if len(solset) != 1:
        return False
    sol = next(iter(solset))
    if any(getattr(v, "free_symbols", set()) for v in sol):
        return False  # contains a free parameter → not unique
    try:
        return [Rational(int(s)) for s in sol] == [Rational(e) for e in expected_solutions]
    except (TypeError, ValueError):
        return False


def _is_consistent(
    coeffs_list: List[List[int]],
    rhs_list: List[int],
    num_vars: int,
) -> bool:
    """Return True iff the system has at least one solution (any)."""
    if not coeffs_list:
        return True
    sym_list = sympy_symbols(f"pa_v0:{num_vars}")
    A = Matrix(coeffs_list)
    b = Matrix(rhs_list)
    try:
        solset = linsolve((A, b), *sym_list)
    except Exception:
        return False
    return len(solset) > 0


def _generate_unique_system(
    num_vars: int,
    num_eqs: int,
    operations: str,
    sol_lo: int,
    sol_hi: int,
    coef_range: int,
    rng: random.Random,
    max_attempts: int = 30,
) -> Optional[Dict[str, Any]]:
    """Generate a linear system with a unique integer solution.

    Resamples when the rng happens to pick linearly-dependent equations.
    Returns ``None`` when exhausted (extremely unlikely with sane ranges).
    """
    coef_pool = _coefficient_pool(operations, coef_range)
    for _ in range(max_attempts):
        solutions = _sample_solutions(num_vars, sol_lo, sol_hi, rng)
        coeffs_list: List[List[int]] = []
        rhs_list: List[int] = []
        for _ in range(num_eqs):
            coeffs, rhs = _build_equation(num_vars, solutions, coef_pool, rng)
            coeffs_list.append(coeffs)
            rhs_list.append(rhs)
        if _verify_unique(coeffs_list, rhs_list, solutions):
            return {
                "coeffs": coeffs_list,
                "rhs": rhs_list,
                "solutions": solutions,
                "determinacy": DETERMINACY_UNIQUE,
            }
    return None


def _generate_underdetermined_system(
    num_vars: int,
    operations: str,
    sol_lo: int,
    sol_hi: int,
    coef_range: int,
    rng: random.Random,
) -> Dict[str, Any]:
    """Drop an equation so the system has infinite solutions.

    Seed with any consistent integer solution so the equations have a real
    RHS — the model's task is to notice it cannot pin down a unique answer.
    """
    coef_pool = _coefficient_pool(operations, coef_range)
    solutions = _sample_solutions(num_vars, sol_lo, sol_hi, rng)
    num_eqs = max(1, num_vars - 1)
    coeffs_list: List[List[int]] = []
    rhs_list: List[int] = []
    for _ in range(num_eqs):
        coeffs, rhs = _build_equation(num_vars, solutions, coef_pool, rng)
        coeffs_list.append(coeffs)
        rhs_list.append(rhs)
    return {
        "coeffs": coeffs_list,
        "rhs": rhs_list,
        "solutions": None,
        "determinacy": DETERMINACY_UNDER,
    }


def _generate_inconsistent_system(
    num_vars: int,
    num_eqs: int,
    operations: str,
    sol_lo: int,
    sol_hi: int,
    coef_range: int,
    rng: random.Random,
    max_attempts: int = 30,
) -> Optional[Dict[str, Any]]:
    """Take a unique system and perturb one RHS to break consistency."""
    base = _generate_unique_system(
        num_vars, max(num_eqs, num_vars), operations,
        sol_lo, sol_hi, coef_range, rng, max_attempts=max_attempts,
    )
    if base is None:
        return None
    for _ in range(max_attempts):
        coeffs_list = [list(c) for c in base["coeffs"]]
        rhs_list = list(base["rhs"])
        idx = rng.randrange(len(rhs_list))
        # Shift RHS by a non-zero integer. Use sol_hi as a sensible span.
        shift = rng.choice([v for v in range(-max(3, sol_hi), max(3, sol_hi) + 1) if v != 0])
        rhs_list[idx] += shift
        if not _is_consistent(coeffs_list, rhs_list, num_vars):
            return {
                "coeffs": coeffs_list,
                "rhs": rhs_list,
                "solutions": None,
                "determinacy": DETERMINACY_INCONSISTENT,
            }
    return None


# ── variable rendering ──────────────────────────────────────────────────

def _pick_tokens(
    surface_form: str,
    emoji_category: str,
    num_vars: int,
    rng: random.Random,
) -> List[str]:
    if surface_form == "alpha":
        return list(ALPHA_SYMBOLS[:num_vars])
    if surface_form == "nonsense":
        return list(NONSENSE_SYMBOLS[:num_vars])
    # emoji
    pool = EMOJI_POOLS.get(emoji_category, EMOJI_POOLS["mixed"])
    if num_vars > len(pool):
        raise ValueError(
            f"Emoji pool '{emoji_category}' has {len(pool)} items, "
            f"need {num_vars}"
        )
    return rng.sample(pool, num_vars)


def _render_term(coef: int, token: str, operations: str, is_first: bool) -> str:
    """Render a single ``coef * token`` term within an equation.

    * `add_only`: repeated addition (🍎 + 🍎 + 🍎) for positive integer coefs.
      Falls through to numeric prefix when coef is 0 or out of range.
    * `add_multiply` / `all`: numeric prefix with middle dot (2·🍎).
    * `add_subtract`: `+` / `-` with absolute value as prefix (skip when abs=1).
    """
    if coef == 0:
        return ""
    sign = "+" if coef > 0 else "-"
    mag = abs(coef)

    if operations == "add_only" and coef > 0 and mag <= 4:
        # Repeated addition for the small-coefficient case
        repeated = " + ".join([token] * mag)
        return repeated if is_first else f"+ {repeated}"

    if mag == 1:
        body = token
    else:
        body = f"{mag}·{token}"

    if is_first:
        return f"-{body}" if coef < 0 else body
    return f"{sign} {body}"


def _render_equation(
    coeffs: List[int],
    rhs: int,
    tokens: List[str],
    operations: str,
) -> str:
    """Render one equation as a single string line."""
    parts: List[str] = []
    first = True
    for coef, token in zip(coeffs, tokens):
        term = _render_term(coef, token, operations, is_first=first)
        if term:
            parts.append(term)
            first = False
    if not parts:
        # Degenerate — all coefficients were zero.  Should not happen given
        # _build_equation's guard but fall back gracefully.
        parts.append("0")
    return " ".join(parts) + f" = {rhs}"


def _format_variable_list(tokens: List[str]) -> str:
    return ", ".join(tokens)


# ── generator class ─────────────────────────────────────────────────────

class PictureAlgebraGenerator(TestCaseGenerator):
    """Generator for picture_algebra."""

    GENERATOR_VERSION = "1.0.0"

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None,
    ) -> List[TestCase]:
        rng = random.Random(seed if seed is not None else 42)

        # ── resolve difficulty preset ───────────────────────────────────
        difficulty = config.get("difficulty")
        if difficulty and difficulty in DIFFICULTY_PRESETS:
            preset = DIFFICULTY_PRESETS[difficulty]
            effective = {**preset}
            # explicit overrides beat preset
            for k, v in config.items():
                if k in preset and v != preset[k]:
                    effective[k] = v
        else:
            effective = dict(config)

        num_vars = int(effective.get("num_variables", 2))
        num_eqs = int(effective.get("num_equations", 2))
        operations = str(effective.get("operations", "add_subtract"))
        sol_lo = int(effective.get("solution_range_min", 1))
        sol_hi = int(effective.get("solution_range_max", 20))
        coef_range = int(effective.get("coefficient_range", 5))
        surface_form = str(effective.get("surface_form", "emoji"))
        emoji_category = str(effective.get("emoji_category", "food"))
        question_scope = str(effective.get("question_scope", "all"))
        trick_rate = float(effective.get("trick_rate", 0.0))

        # Clamp sensible bounds so explicit overrides can't break the generator.
        num_vars = max(2, min(3, num_vars))
        num_eqs = max(num_vars, min(4, num_eqs))
        sol_hi = max(sol_lo + 1, sol_hi)
        trick_rate = max(0.0, min(1.0, trick_rate))

        language = prompt_config.get("language", "en")
        user_style = prompt_config.get("user_style", "minimal")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")

        tests: List[TestCase] = []

        # Token-selection RNG is independent of the system-generation RNG so
        # that the SAME seed produces the SAME underlying math across different
        # ``surface_form`` values — the GSM-Symbolic experimental design hinges
        # on this invariant.  Emoji pool sampling consumes RNG state that
        # alpha/nonsense slicing does not, so without the split, cross-form
        # runs with the same seed would diverge after the first emoji case.
        token_rng_seed = (seed if seed is not None else 42) ^ 0xA1B2C3D4
        token_rng = random.Random(token_rng_seed)

        for idx in range(count):
            # Trick-vs-unique decision
            is_trick = rng.random() < trick_rate
            trick_kind: Optional[str] = None
            system_data: Optional[Dict[str, Any]] = None

            if is_trick:
                # Try the primary trick kind, then the other one if it fails
                # (inconsistent systems can occasionally resist perturbation).
                kinds = ["underdetermined", "inconsistent"]
                rng.shuffle(kinds)
                for kind in kinds:
                    if kind == "underdetermined":
                        system_data = _generate_underdetermined_system(
                            num_vars, operations, sol_lo, sol_hi, coef_range, rng,
                        )
                    else:
                        system_data = _generate_inconsistent_system(
                            num_vars, num_eqs, operations,
                            sol_lo, sol_hi, coef_range, rng,
                        )
                    if system_data is not None:
                        trick_kind = kind
                        break

            if system_data is None:
                # Not a trick case (or both trick kinds failed)
                system_data = _generate_unique_system(
                    num_vars, num_eqs, operations,
                    sol_lo, sol_hi, coef_range, rng,
                )
                trick_kind = None

            if system_data is None:
                raise RuntimeError(
                    "Unable to generate a unique linear system after many "
                    "attempts — widen solution_range or coefficient_range."
                )

            determinacy = system_data["determinacy"]
            coeffs_list: List[List[int]] = system_data["coeffs"]
            rhs_list: List[int] = system_data["rhs"]
            solutions_list = system_data.get("solutions")

            # Rendered variable tokens (uses token_rng so alpha/emoji/nonsense
            # runs with the same seed produce identical equation structures).
            tokens = _pick_tokens(surface_form, emoji_category, num_vars, token_rng)
            variable_ids = [f"v{i}" for i in range(num_vars)]
            variable_map = dict(zip(tokens, variable_ids))

            # Rendered equation strings
            equations_text = [
                _render_equation(coeffs, rhs, tokens, operations)
                for coeffs, rhs in zip(coeffs_list, rhs_list)
            ]

            # Structured representation (for evaluator breakdowns + debugging)
            equations_structured = [
                {
                    "coeffs": dict(zip(variable_ids, coeffs)),
                    "rhs": rhs,
                }
                for coeffs, rhs in zip(coeffs_list, rhs_list)
            ]

            # Ground truth answer
            solutions_canonical: Optional[Dict[str, int]] = None
            if solutions_list is not None:
                solutions_canonical = dict(zip(variable_ids, solutions_list))

            if determinacy == DETERMINACY_UNIQUE:
                expected_answer: Any = dict(zip(tokens, solutions_list or []))
            elif determinacy == DETERMINACY_UNDER:
                expected_answer = SENTINEL_CANNOT_DETERMINE
            else:  # inconsistent
                expected_answer = SENTINEL_NO_SOLUTION

            # Question scope: all variables by default, or a random single var
            if question_scope == "specific" and determinacy == DETERMINACY_UNIQUE:
                queried_variable = rng.choice(tokens)
                query_target = queried_variable
                # Narrow expected to just that variable for strict grading
                expected_answer = {queried_variable: expected_answer[queried_variable]}
            else:
                queried_variable = None
                query_target = _QUERY_TARGET_ALL.get(language, _QUERY_TARGET_ALL["en"])

            equations_block = "\n".join(equations_text)
            variable_list_str = _format_variable_list(tokens)

            user_prompt, system_prompt, full_prompt = self._build_prompts_yaml(
                "picture_algebra", language, user_style, system_style,
                equations=equations_block,
                variable_list=variable_list_str,
                query_target=query_target,
            )

            tests.append(TestCase(
                test_id=f"picture_algebra_{idx:04d}",
                task_type="picture_algebra",
                config_name=config_name,
                prompts={
                    "system": system_prompt,
                    "user": user_prompt,
                    "full": full_prompt,
                },
                task_params={
                    "expected_answer": expected_answer,
                    "variables": tokens,
                    "variable_ids": variable_ids,
                    "variable_map": variable_map,
                    "equations_text": equations_text,
                    "equations_structured": equations_structured,
                    "solutions_canonical": solutions_canonical,
                    "determinacy": determinacy,
                    "trick_kind": trick_kind,
                    "surface_form": surface_form,
                    "emoji_category": emoji_category if surface_form == "emoji" else None,
                    "operations": operations,
                    "num_variables": num_vars,
                    "num_equations": len(equations_text),
                    "question_scope": question_scope,
                    "queried_variable": queried_variable,
                },
                prompt_metadata={
                    "user_style": user_style,
                    "system_style": system_style,
                    "language": language,
                },
                generation_metadata={
                    "seed": seed,
                    "generator_version": self.GENERATOR_VERSION,
                    "created_at": datetime.now().isoformat(),
                },
            ))

        return tests

    # ── config schema (for web UI) ──────────────────────────────────────

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "difficulty": "medium",
            "count": 10,
            "num_variables": 2,
            "num_equations": 2,
            "operations": "add_subtract",
            "solution_range_min": 1,
            "solution_range_max": 20,
            "coefficient_range": 5,
            "surface_form": "emoji",
            "emoji_category": "food",
            "question_scope": "all",
            "trick_rate": 0.0,
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(
                name="difficulty", label="Difficulty preset",
                field_type="select", default="medium",
                options=["easy", "medium", "hard", "nightmare"],
                help=(
                    "Overrides individual fields below with curated combinations. "
                    "Explicit values for other fields take precedence when they "
                    "differ from the preset."
                ),
            ),
            ConfigField(
                name="count", label="Number of test cases",
                field_type="number", default=10, min_value=1, max_value=200,
            ),
            ConfigField(
                name="num_variables", label="Number of variables",
                field_type="number", default=2, min_value=2, max_value=3,
                help="Unknowns in the system (2=easier, 3=harder)",
            ),
            ConfigField(
                name="num_equations", label="Number of equations",
                field_type="number", default=2, min_value=2, max_value=4,
                help="Must be ≥ num_variables for a determined system",
            ),
            ConfigField(
                name="operations", label="Operators",
                field_type="select", default="add_subtract",
                options=["add_only", "add_subtract", "add_multiply", "all"],
                help=(
                    "add_only uses repeated addition (🍎 + 🍎); "
                    "add_multiply uses numeric prefix (2·🍎); "
                    "add_subtract mixes + and - signs"
                ),
            ),
            ConfigField(
                name="solution_range_min", label="Solution range min",
                field_type="number", default=1, min_value=-10, max_value=20,
                help="Lower bound on the integer value each variable can take",
                group="advanced",
            ),
            ConfigField(
                name="solution_range_max", label="Solution range max",
                field_type="number", default=20, min_value=1, max_value=50,
                help="Upper bound on the integer value each variable can take",
                group="advanced",
            ),
            ConfigField(
                name="coefficient_range", label="Coefficient magnitude",
                field_type="number", default=5, min_value=1, max_value=10,
                help="|c| ceiling for equation coefficients",
                group="advanced",
            ),
            ConfigField(
                name="surface_form", label="Surface form",
                field_type="select", default="emoji",
                options=["emoji", "alpha", "nonsense"],
                help=(
                    "Rendering of the unknowns. emoji = 🍎/🍌; alpha = x/y/z; "
                    "nonsense = FOO/BAR. Run the same seed with different surface "
                    "forms to measure semantic interference."
                ),
            ),
            ConfigField(
                name="emoji_category", label="Emoji pool",
                field_type="select", default="food",
                options=["food", "animals", "objects", "mixed"],
                help="Ignored unless surface_form=emoji",
            ),
            ConfigField(
                name="question_scope", label="Question scope",
                field_type="select", default="all",
                options=["all", "specific"],
                help=(
                    "all = solve for every variable; specific = the question "
                    "asks for one randomly chosen variable only"
                ),
            ),
            ConfigField(
                name="trick_rate", label="Trick case rate",
                field_type="number", default=0.0,
                min_value=0.0, max_value=1.0, step=0.1,
                group="advanced",
                help=(
                    "Fraction of cases that are underdetermined or "
                    "inconsistent — model should respond 'cannot be "
                    "determined' / 'no solution' rather than guess"
                ),
            ),
        ]
