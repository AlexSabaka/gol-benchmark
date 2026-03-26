"""
Family Relations – Test Case Generator

Generates procedural family-counting puzzles across four sub-types:

  sibling_count      — how many sisters / brothers does X have?
  shared_children    — all daughters share one brother; how many children?
  generational       — grandchildren / great-grandchildren counting
  perspective_shift  — constraint-based puzzles from different viewpoints

Every answer is a non-negative integer computed deterministically at
generation time.
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.plugins.family_relations.prompts import USER_PROMPT_TEMPLATES

# ---------------------------------------------------------------------------
# Name generation (same pattern as sally_anne / grid_tasks)
# ---------------------------------------------------------------------------

try:
    import names as _names_lib
    _NAMES_AVAILABLE = True
except ImportError:
    _names_lib = None
    _NAMES_AVAILABLE = False

_FALLBACK_MALE = [
    "James", "David", "Carlos", "Ahmed", "Ben", "Tom", "Oscar", "Leo",
    "Max", "Oliver", "Ethan", "Henry", "George", "Frank", "Ivan", "Raj",
]
_FALLBACK_FEMALE = [
    "Sally", "Maria", "Emma", "Aisha", "Beth", "Clara", "Diana", "Fiona",
    "Grace", "Hannah", "Iris", "Julia", "Lily", "Nora", "Rosa", "Zoe",
]


def _random_name(gender: str, rng: random.Random) -> str:
    if _NAMES_AVAILABLE:
        # names library uses global random; seed externally
        return _names_lib.get_first_name(gender="male" if gender == "m" else "female")
    pool = _FALLBACK_MALE if gender == "m" else _FALLBACK_FEMALE
    return rng.choice(pool)


def _unique_names(genders: List[str], rng: random.Random) -> List[str]:
    """Return len(genders) unique first names matching requested genders."""
    seen: set[str] = set()
    result: list[str] = []
    for g in genders:
        for _ in range(40):
            n = _random_name(g, rng)
            if n not in seen:
                seen.add(n)
                result.append(n)
                break
        else:
            # extremely unlikely fallback
            fallback = f"Person{len(result)+1}"
            result.append(fallback)
    return result


# ---------------------------------------------------------------------------
# Pronoun helpers
# ---------------------------------------------------------------------------

_PRONOUNS = {
    "m": {"subject": "he", "object": "him", "possessive": "his"},
    "f": {"subject": "she", "object": "her", "possessive": "her"},
}

_PARENT_LABEL = {"m": "father", "f": "mother"}
_CHILD_LABEL  = {"m": "son",    "f": "daughter"}
_SIBLING_LABEL = {"m": "brother", "f": "sister"}

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

# Templates moved to prompts.py


# ===================================================================
# Puzzle template functions
#
# Each returns (question_text: str, expected_answer: int, metadata: dict)
# ===================================================================

# ---- sibling_count ------------------------------------------------

def _sibling_count_classic(rng: random.Random) -> Tuple[str, int, Dict]:
    """'{Name} has N brothers. Each brother has M sisters. How many sisters does {Name} have?'
    Answer: M - 1  (subtract self — the brothers' sister count *includes* {Name}).
    Wait — actually: the brothers' M sisters include {Name}, so {Name} has M-1 other sisters.
    But we need M >= 1 for the puzzle to make sense ({Name} herself is one of the sisters).
    """
    subject_gender = rng.choice(["f", "m"])
    ask_about = "f" if subject_gender == "f" else "m"  # asking about same-gender siblings

    name = _random_name(subject_gender, rng)

    if subject_gender == "f":
        # "{Name} has N brothers.  Each brother has M sisters."
        n_brothers = rng.randint(1, 5)
        # total sisters seen by each brother = subject + extra sisters
        total_sisters_per_brother = rng.randint(1, 4)  # includes subject
        answer = total_sisters_per_brother - 1  # subtract subject
        puzzle = (
            f"{name} has {n_brothers} {_plural('brother', n_brothers)}. "
            f"Each brother has {total_sisters_per_brother} "
            f"{_plural('sister', total_sisters_per_brother)}. "
            f"How many sisters does {name} have?"
        )
    else:
        # "{Name} has N sisters.  Each sister has M brothers."
        n_sisters = rng.randint(1, 5)
        total_brothers_per_sister = rng.randint(1, 4)
        answer = total_brothers_per_sister - 1
        puzzle = (
            f"{name} has {n_sisters} {_plural('sister', n_sisters)}. "
            f"Each sister has {total_brothers_per_sister} "
            f"{_plural('brother', total_brothers_per_sister)}. "
            f"How many brothers does {name} have?"
        )

    meta = {
        "template": "sibling_count_classic",
        "subject_name": name,
        "subject_gender": subject_gender,
        "trap": "counting_self_as_sibling",
    }
    return puzzle, answer, meta


def _sibling_count_both_genders(rng: random.Random) -> Tuple[str, int, Dict]:
    """{Name} has N brothers and M sisters.  How many children do {Name}'s parents have?
    Answer: N + M + 1 (include {Name}).
    """
    name_gender = rng.choice(["f", "m"])
    name = _random_name(name_gender, rng)
    n_brothers = rng.randint(1, 4)
    n_sisters = rng.randint(1, 4)
    answer = n_brothers + n_sisters + 1

    puzzle = (
        f"{name} has {n_brothers} {_plural('brother', n_brothers)} "
        f"and {n_sisters} {_plural('sister', n_sisters)}. "
        f"How many children do {name}'s parents have in total?"
    )
    meta = {
        "template": "sibling_count_both_genders",
        "subject_name": name,
        "subject_gender": name_gender,
        "trap": "forgetting_subject",
    }
    return puzzle, answer, meta


# ---- shared_children -----------------------------------------------

def _shared_children_basic(rng: random.Random) -> Tuple[str, int, Dict]:
    """'A parent has D daughters. Each daughter has exactly B brother(s).
    How many children does the parent have?'
    Answer: D + B  (all daughters share the same B brothers).
    """
    parent_gender = rng.choice(["m", "f"])
    parent_label = _PARENT_LABEL[parent_gender]

    # which group is stated first, which is the "shared" sibling
    if rng.choice([True, False]):
        # daughters first, brothers shared
        n_primary = rng.randint(2, 5)  # daughters
        n_shared = rng.randint(1, 3)   # brothers (shared)
        answer = n_primary + n_shared
        puzzle = (
            f"A {parent_label} has {n_primary} {_plural('daughter', n_primary)}. "
            f"Each daughter has exactly {n_shared} {_plural('brother', n_shared)}. "
            f"How many children does the {parent_label} have?"
        )
        trap = "multiplying_instead_of_sharing"
    else:
        # sons first, sisters shared
        n_primary = rng.randint(2, 5)  # sons
        n_shared = rng.randint(1, 3)   # sisters (shared)
        answer = n_primary + n_shared
        puzzle = (
            f"A {parent_label} has {n_primary} {_plural('son', n_primary)}. "
            f"Each son has exactly {n_shared} {_plural('sister', n_shared)}. "
            f"How many children does the {parent_label} have?"
        )
        trap = "multiplying_instead_of_sharing"

    meta = {
        "template": "shared_children_basic",
        "parent_gender": parent_gender,
        "trap": trap,
    }
    return puzzle, answer, meta


def _shared_children_named(rng: random.Random) -> Tuple[str, int, Dict]:
    """Same logic as basic, but with a named parent."""
    parent_gender = rng.choice(["m", "f"])
    parent_name = _random_name(parent_gender, rng)
    parent_label = _PARENT_LABEL[parent_gender]

    n_daughters = rng.randint(2, 5)
    n_brothers = rng.randint(1, 2)
    answer = n_daughters + n_brothers

    puzzle = (
        f"{parent_name} is a {parent_label} with {n_daughters} "
        f"{_plural('daughter', n_daughters)}. "
        f"Each of {_PRONOUNS[parent_gender]['possessive']} daughters has exactly "
        f"{n_brothers} {_plural('brother', n_brothers)}. "
        f"How many children does {parent_name} have in total?"
    )
    meta = {
        "template": "shared_children_named",
        "parent_name": parent_name,
        "parent_gender": parent_gender,
        "trap": "multiplying_instead_of_sharing",
    }
    return puzzle, answer, meta


# ---- generational ---------------------------------------------------

def _generational_grandchildren(rng: random.Random) -> Tuple[str, int, Dict]:
    """'A grandmother has C children. Each child has G children.
    How many grandchildren does she have?'
    Answer: C × G.
    """
    gp_gender = rng.choice(["m", "f"])
    gp_label = "grandmother" if gp_gender == "f" else "grandfather"

    n_children = rng.randint(2, 5)
    n_grand_each = rng.randint(1, 4)
    answer = n_children * n_grand_each

    puzzle = (
        f"A {gp_label} has {n_children} children. "
        f"Each of {_PRONOUNS[gp_gender]['possessive']} children has "
        f"{n_grand_each} {_plural('child', n_grand_each, plural='children')}. "
        f"How many grandchildren does the {gp_label} have?"
    )
    meta = {
        "template": "generational_grandchildren",
        "gp_gender": gp_gender,
        "trap": "none",
    }
    return puzzle, answer, meta


def _generational_great_grandchildren(rng: random.Random) -> Tuple[str, int, Dict]:
    """Three levels: grandparent → children → grandchildren → great-grandchildren.
    Answer: C × G × GG.
    """
    gp_gender = rng.choice(["m", "f"])
    gp_label = "grandmother" if gp_gender == "f" else "grandfather"
    pron = _PRONOUNS[gp_gender]["possessive"]

    n_children = rng.randint(2, 4)
    n_grand_each = rng.randint(1, 3)
    n_great_each = rng.randint(1, 3)
    answer = n_children * n_grand_each * n_great_each

    puzzle = (
        f"A {gp_label} has {n_children} children. "
        f"Each of {pron} children has {n_grand_each} "
        f"{_plural('child', n_grand_each, plural='children')}. "
        f"Each grandchild has {n_great_each} "
        f"{_plural('child', n_great_each, plural='children')} of their own. "
        f"How many great-grandchildren does the {gp_label} have?"
    )
    meta = {
        "template": "generational_great_grandchildren",
        "gp_gender": gp_gender,
        "trap": "none",
    }
    return puzzle, answer, meta


def _generational_cousins(rng: random.Random) -> Tuple[str, int, Dict]:
    """'{Name} has N siblings.  {Name}'s parent has one sibling who has M children.
    How many cousins does {Name} have?'
    Answer: M  (cousins = aunt/uncle's children).
    """
    subject_gender = rng.choice(["m", "f"])
    name = _random_name(subject_gender, rng)
    pron = _PRONOUNS[subject_gender]

    # parent's sibling's children = cousins
    n_siblings = rng.randint(0, 3)
    n_cousins = rng.randint(1, 5)
    parent_gender = rng.choice(["m", "f"])
    aunt_uncle = "aunt" if parent_gender == "f" else "uncle"

    if n_siblings > 0:
        sibling_text = (
            f"{name} has {n_siblings} {_plural('sibling', n_siblings)}. "
        )
    else:
        sibling_text = f"{name} is an only child. "

    puzzle = (
        f"{sibling_text}"
        f"{pron['possessive'].capitalize()} {_PARENT_LABEL[parent_gender]} "
        f"has exactly one sibling — an {aunt_uncle} — who has "
        f"{n_cousins} {_plural('child', n_cousins, plural='children')}. "
        f"How many cousins does {name} have?"
    )
    answer = n_cousins
    meta = {
        "template": "generational_cousins",
        "subject_name": name,
        "subject_gender": subject_gender,
        "trap": "confusing_siblings_and_cousins",
    }
    return puzzle, answer, meta


# ---- perspective_shift -----------------------------------------------

def _perspective_equal_brothers_sisters(rng: random.Random) -> Tuple[str, int, Dict]:
    """'I have as many brothers as sisters.
     My sister has twice as many brothers as sisters.
     How many of us are there?'

    Let b = number of boys, g = number of girls in the family.
    "I" is male (one of the b boys):
      brothers = b-1, sisters = g   →  b-1 = g        … (1)
    "My sister" (one of the g girls):
      brothers = b, sisters = g-1   →  b = 2(g-1)     … (2)
    From (1): b = g+1.  Substitute into (2): g+1 = 2g-2  →  g = 3, b = 4.
    Answer: b + g = 7.

    We can parametrise by changing the multiplier in (2).
    Let the multiplier be k (integer ≥ 2):
      b-1 = g  →  b = g+1
      b = k(g-1) →  g+1 = k(g-1)  →  g+1 = kg - k  →  g(k-1) = k+1
      g = (k+1)/(k-1).  Integer only when (k-1) divides (k+1).
      k=2 → g=3, k=3 → g=2.  Those are the only small integer solutions.
    """
    k = rng.choice([2, 3])
    g = (k + 1) // (k - 1)
    b = g + 1
    answer = b + g

    if k == 2:
        multiplier_word = "twice"
    else:
        multiplier_word = "three times"

    names_list = _unique_names(["m", "f"], rng)
    narrator = names_list[0]
    sister = names_list[1]

    puzzle = (
        f"{narrator} says: \"I have as many brothers as sisters.\"\n"
        f"{sister}, {narrator}'s sister, says: \"I have {multiplier_word} "
        f"as many brothers as sisters.\"\n"
        f"How many children are there in this family?"
    )
    meta = {
        "template": "perspective_equal_brothers_sisters",
        "narrator": narrator,
        "sister": sister,
        "boys": b,
        "girls": g,
        "multiplier": k,
        "trap": "perspective_confusion",
    }
    return puzzle, answer, meta


def _perspective_brother_sister_difference(rng: random.Random) -> Tuple[str, int, Dict]:
    """'{Name} says: "I have N more brothers than sisters."
     {Name}'s brother says: "I have N more sisters than brothers."
     How many boys and girls are in the family?'

    Let {Name} be female.  b = boys, g = girls.
      sisters = g-1, brothers = b  →  b - (g-1) = N  →  b = g-1+N  … (1)
    Her brother:
      sisters = g, brothers = b-1  →  g - (b-1) = N  →  g = b-1+N  … (2)
    From (1): b = g+N-1.  Sub into (2): g = (g+N-1)-1+N = g+2N-2.
    → 0 = 2N-2 → N=1.  So this only works for difference=1.
      b = g.  Answer = 2g.  Pick g ∈ [2..5].
    """
    g = rng.randint(2, 5)
    b = g
    answer = b + g

    names_list = _unique_names(["f", "m"], rng)
    sister = names_list[0]
    brother = names_list[1]

    puzzle = (
        f"{sister} says: \"I have one more brother than I have sisters.\"\n"
        f"{brother}, {sister}'s brother, says: \"I have one more sister "
        f"than I have brothers.\"\n"
        f"How many children are there in the family?"
    )
    meta = {
        "template": "perspective_brother_sister_difference",
        "sister": sister,
        "brother": brother,
        "boys": b,
        "girls": g,
        "trap": "perspective_confusion",
    }
    return puzzle, answer, meta


def _perspective_parent_child_count(rng: random.Random) -> Tuple[str, int, Dict]:
    """'Each of my sons has the same number of brothers as sisters.
     Each of my daughters has twice as many brothers as sisters.
     How many children do I have?'

    Let b = boys, g = girls.
    Each son: brothers=b-1, sisters=g  →  b-1 = g      … (1)
    Each daughter: brothers=b, sisters=g-1 → b = 2(g-1) … (2)
    Same as _perspective_equal_brothers_sisters with k=2 but phrased
    from the parent's POV.
    From (1): b = g+1.  Sub (2): g+1 = 2g-2  →  g=3, b=4.  Answer: 7.

    Generalise with multiplier k:
      b-1=g, b=k(g-1) → g=(k+1)/(k-1).
    """
    k = rng.choice([2, 3])
    g = (k + 1) // (k - 1)
    b = g + 1
    answer = b + g

    if k == 2:
        multiplier_word = "twice"
    else:
        multiplier_word = "three times"

    parent_gender = rng.choice(["m", "f"])
    parent_name = _random_name(parent_gender, rng)

    puzzle = (
        f"{parent_name} says:\n"
        f"\"Each of my sons has as many brothers as sisters. "
        f"Each of my daughters has {multiplier_word} as many brothers "
        f"as sisters.\"\n"
        f"How many children does {parent_name} have?"
    )
    meta = {
        "template": "perspective_parent_child_count",
        "parent_name": parent_name,
        "parent_gender": parent_gender,
        "boys": b,
        "girls": g,
        "multiplier": k,
        "trap": "perspective_confusion",
    }
    return puzzle, answer, meta


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

_TEMPLATES_BY_SUBTYPE: Dict[str, List] = {
    "sibling_count": [
        _sibling_count_classic,
        _sibling_count_both_genders,
    ],
    "shared_children": [
        _shared_children_basic,
        _shared_children_named,
    ],
    "generational": [
        _generational_grandchildren,
        _generational_great_grandchildren,
        _generational_cousins,
    ],
    "perspective_shift": [
        _perspective_equal_brothers_sisters,
        _perspective_brother_sister_difference,
        _perspective_parent_child_count,
    ],
}

_SUBTYPE_DIFFICULTY = {
    "sibling_count": "easy",
    "shared_children": "easy",
    "generational": "medium",
    "perspective_shift": "hard",
}

ALL_SUBTYPES = list(_TEMPLATES_BY_SUBTYPE.keys())

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _plural(word: str, n: int, *, plural: str | None = None) -> str:
    """Super-simple English pluralisation."""
    if n == 1:
        return word
    if plural:
        return plural
    return word + "s"


# ===================================================================
# Generator
# ===================================================================

class FamilyRelationsGenerator(TestCaseGenerator):
    """Generates family-relations reasoning puzzles."""

    def __init__(self):
        pass  # base class helpers handle PromptEngine

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(
                name="sub_types",
                label="Puzzle sub-types",
                field_type="multi-select",
                default=ALL_SUBTYPES,
                options=ALL_SUBTYPES,
                group="basic",
                help="Which puzzle families to include",
            ),
            ConfigField(
                name="count",
                label="Number of puzzles",
                field_type="number",
                default=20,
                min_value=1,
                max_value=500,
                group="basic",
                help="Total puzzles to generate (distributed across sub-types)",
            ),
        ]

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, Any],
        count: int,
        seed: int,
    ) -> List[TestCase]:
        rng = random.Random(seed)

        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        language = prompt_config.get("language", "en")
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")

        sub_types = config.get("sub_types", ALL_SUBTYPES)
        if not sub_types:
            sub_types = ALL_SUBTYPES

        # Collect eligible template functions
        templates: List[Tuple[str, Any]] = []
        for st in sub_types:
            for fn in _TEMPLATES_BY_SUBTYPE.get(st, []):
                templates.append((st, fn))

        if not templates:
            templates = [(st, fn) for st in ALL_SUBTYPES
                         for fn in _TEMPLATES_BY_SUBTYPE[st]]

        test_cases: List[TestCase] = []
        for idx in range(count):
            sub_type, template_fn = rng.choice(templates)
            puzzle_text, answer, meta = template_fn(rng)

            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                language=language,
                puzzle_text=puzzle_text,
                answer=answer,
                sub_type=sub_type,
                meta=meta,
            )
            test_cases.append(tc)

        return test_cases

    # ------------------------------------------------------------------

    def _build_test_case(
        self,
        idx: int,
        seed: int,
        config_name: str,
        user_style: str,
        system_style: str,
        language: str,
        puzzle_text: str,
        answer: int,
        sub_type: str,
        meta: Dict[str, Any],
    ) -> TestCase:
        user_prompt, system_prompt, full_prompt = self._build_prompts(
            USER_PROMPT_TEMPLATES, language, user_style, system_style,
            puzzle=puzzle_text,
        )

        task_params = {
            "expected_answer": answer,
            "sub_type": sub_type,
            "template": meta.get("template", ""),
            "trap": meta.get("trap", ""),
            "difficulty": _SUBTYPE_DIFFICULTY.get(sub_type, "easy"),
            **{k: v for k, v in meta.items() if k not in ("template", "trap")},
        }

        return TestCase(
            test_id=f"family_relations_{seed}_{idx:04d}",
            task_type="family_relations",
            config_name=config_name,
            prompts={
                "system": system_prompt,
                "user": user_prompt,
                "full": full_prompt,
            },
            task_params=task_params,
            prompt_metadata={
                "user_style": user_style,
                "system_style": system_style,
                "language": language,
            },
            generation_metadata={
                "seed": seed,
                "index": idx,
                "sub_type": sub_type,
                "template": meta.get("template", ""),
            },
        )
