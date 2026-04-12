"""
Family Relations -- Test Case Generator

Generates procedural family-counting puzzles across four sub-types:

  sibling_count      -- how many sisters / brothers does X have?
  shared_children    -- all daughters share one brother; how many children?
  generational       -- grandchildren / great-grandchildren counting
  perspective_shift  -- constraint-based puzzles from different viewpoints

Every answer is a non-negative integer computed deterministically at
generation time.
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.plugins.family_relations import i18n


# ===================================================================
# Helpers for article-prepended labels
# ===================================================================

def _art_label(label: str, gender: str, lang: str,
               definite: bool = True, case: str = "nom",
               capitalize: bool = False) -> str:
    """Shorthand for ``i18n.label_with_article``."""
    return i18n.label_with_article(label, gender, lang,
                                   definite=definite, case=case,
                                   capitalize=capitalize)


# ===================================================================
# Puzzle template functions
#
# Each returns (question_text: str, expected_answer: int, metadata: dict)
# ===================================================================

# ---- sibling_count ------------------------------------------------

def _sibling_count_classic(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """'{Name} has N brothers. Each brother has M sisters. How many sisters does {Name} have?'
    Answer: M - 1  (subtract self -- the brothers' sister count *includes* {Name}).
    Wait -- actually: the brothers' M sisters include {Name}, so {Name} has M-1 other sisters.
    But we need M >= 1 for the puzzle to make sense ({Name} herself is one of the sisters).
    """
    subject_gender = rng.choice(["f", "m"])
    name = i18n.get_name(subject_gender, rng, language)

    if subject_gender == "f":
        # "{Name} has N brothers.  Each brother has M sisters."
        n_brothers = rng.randint(1, 5)
        total_sisters_per_brother = rng.randint(1, 4)  # includes subject
        answer = total_sisters_per_brother - 1  # subtract subject

        brothers_word = i18n.rel("brother", language, n_brothers)
        sisters_word = i18n.rel("sister", language, total_sisters_per_brother)
        brother_singular = i18n.rel("brother", language, 1)

        puzzle = (
            i18n.narr("has_n_rel", language, name=name, n=n_brothers, relation=brothers_word) + " "
            + i18n.narr("each_has_n", language, rel_type=brother_singular, n=total_sisters_per_brother, relation=sisters_word) + " "
            + i18n.question("how_many_sisters", language, name=name)
        )
    else:
        # "{Name} has N sisters.  Each sister has M brothers."
        n_sisters = rng.randint(1, 5)
        total_brothers_per_sister = rng.randint(1, 4)
        answer = total_brothers_per_sister - 1

        sisters_word = i18n.rel("sister", language, n_sisters)
        brothers_word = i18n.rel("brother", language, total_brothers_per_sister)
        sister_singular = i18n.rel("sister", language, 1)

        puzzle = (
            i18n.narr("has_n_rel", language, name=name, n=n_sisters, relation=sisters_word) + " "
            + i18n.narr("each_has_n", language, rel_type=sister_singular, n=total_brothers_per_sister, relation=brothers_word) + " "
            + i18n.question("how_many_brothers", language, name=name)
        )

    meta = {
        "template": "sibling_count_classic",
        "subject_name": name,
        "subject_gender": subject_gender,
        "trap": "counting_self_as_sibling",
    }
    return puzzle, answer, meta


def _sibling_count_both_genders(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """{Name} has N brothers and M sisters.  How many children do {Name}'s parents have?
    Answer: N + M + 1 (include {Name}).
    """
    name_gender = rng.choice(["f", "m"])
    name = i18n.get_name(name_gender, rng, language)
    n_brothers = rng.randint(1, 4)
    n_sisters = rng.randint(1, 4)
    answer = n_brothers + n_sisters + 1

    brothers_word = i18n.rel("brother", language, n_brothers)
    sisters_word = i18n.rel("sister", language, n_sisters)

    puzzle = (
        i18n.narr("has_n_and_m", language, name=name, n=n_brothers, rel_a=brothers_word, m=n_sisters, rel_b=sisters_word) + " "
        + i18n.question("total_children_parents", language, name=name)
    )
    meta = {
        "template": "sibling_count_both_genders",
        "subject_name": name,
        "subject_gender": name_gender,
        "trap": "forgetting_subject",
    }
    return puzzle, answer, meta


# ---- shared_children -----------------------------------------------

def _shared_children_basic(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """'A parent has D daughters. Each daughter has exactly B brother(s).
    How many children does the parent have?'
    Answer: D + B  (all daughters share the same B brothers).
    """
    parent_gender = rng.choice(["m", "f"])
    p_label = i18n.parent_label(parent_gender, language)
    # Article-prefixed labels for gendered languages (ES/FR/DE)
    p_label_indef = _art_label(p_label, parent_gender, language, definite=False, capitalize=True)
    p_label_def = _art_label(p_label, parent_gender, language, definite=True)
    p_pronoun = i18n.fr_pronoun(parent_gender)

    # which group is stated first, which is the "shared" sibling
    if rng.choice([True, False]):
        # daughters first, brothers shared
        n_primary = rng.randint(2, 5)  # daughters
        n_shared = rng.randint(1, 3)   # brothers (shared)
        answer = n_primary + n_shared

        daughters_word = i18n.rel("daughter", language, n_primary)
        brothers_word = i18n.rel("brother", language, n_shared)
        daughter_singular = i18n.rel("daughter", language, 1)

        puzzle = (
            i18n.narr("has_n_children", language, gp_label=p_label_indef, n=n_primary, relation=daughters_word) + " "
            + i18n.narr("each_has_n", language, rel_type=daughter_singular, n=n_shared, relation=brothers_word) + " "
            + i18n.question("how_many_children_parent", language, parent=p_label_def, pronoun=p_pronoun)
        )
        trap = "multiplying_instead_of_sharing"
    else:
        # sons first, sisters shared
        n_primary = rng.randint(2, 5)  # sons
        n_shared = rng.randint(1, 3)   # sisters (shared)
        answer = n_primary + n_shared

        sons_word = i18n.rel("son", language, n_primary)
        sisters_word = i18n.rel("sister", language, n_shared)
        son_singular = i18n.rel("son", language, 1)

        puzzle = (
            i18n.narr("has_n_children", language, gp_label=p_label_indef, n=n_primary, relation=sons_word) + " "
            + i18n.narr("each_has_n", language, rel_type=son_singular, n=n_shared, relation=sisters_word) + " "
            + i18n.question("how_many_children_parent", language, parent=p_label_def, pronoun=p_pronoun)
        )
        trap = "multiplying_instead_of_sharing"

    meta = {
        "template": "shared_children_basic",
        "parent_gender": parent_gender,
        "trap": trap,
    }
    return puzzle, answer, meta


def _shared_children_named(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """Same logic as basic, but with a named parent."""
    parent_gender = rng.choice(["m", "f"])
    parent_name = i18n.get_name(parent_gender, rng, language)
    p_label = i18n.parent_label(parent_gender, language)
    possessive = i18n.pron(parent_gender, "possessive", language)
    p_pronoun = i18n.fr_pronoun(parent_gender)

    n_daughters = rng.randint(2, 5)
    n_brothers = rng.randint(1, 2)
    answer = n_daughters + n_brothers

    daughters_word = i18n.rel("daughter", language, n_daughters)
    brothers_word = i18n.rel("brother", language, n_brothers)
    daughter_singular = i18n.rel("daughter", language, 1)

    puzzle = (
        i18n.narr("is_parent_with_n", language, name=parent_name, parent_label=p_label, n=n_daughters, relation=daughters_word) + " "
        + i18n.narr("each_has_exactly_n", language, possessive=possessive, rel_type=daughters_word, n=n_brothers, relation=brothers_word) + " "
        + i18n.question("how_many_children_named", language, name=parent_name, pronoun=p_pronoun)
    )
    meta = {
        "template": "shared_children_named",
        "parent_name": parent_name,
        "parent_gender": parent_gender,
        "trap": "multiplying_instead_of_sharing",
    }
    return puzzle, answer, meta


# ---- generational ---------------------------------------------------

def _generational_grandchildren(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """'A grandmother has C children. Each child has G children.
    How many grandchildren does she have?'
    Answer: C x G.
    """
    gp_gender = rng.choice(["m", "f"])
    gp_label = i18n.grandparent_label(gp_gender, language)
    possessive = i18n.pron(gp_gender, "possessive", language)
    # Article-prefixed labels for gendered languages
    gp_label_indef = _art_label(gp_label, gp_gender, language, definite=False, capitalize=True)
    gp_label_def = _art_label(gp_label, gp_gender, language, definite=True)
    gp_pronoun = i18n.fr_pronoun(gp_gender)

    n_children = rng.randint(2, 5)
    n_grand_each = rng.randint(1, 4)
    answer = n_children * n_grand_each

    children_word = i18n.rel("child", language, n_children)
    grandchildren_word = i18n.rel("child", language, n_grand_each)
    child_type = i18n.rel("child", language, n_children)

    puzzle = (
        i18n.narr("has_n_children", language, gp_label=gp_label_indef, n=n_children, relation=children_word) + " "
        + i18n.narr("each_child_has_n", language, possessive=possessive, rel_type=children_word, n=n_grand_each, relation=grandchildren_word) + " "
        + i18n.question("how_many_grandchildren", language, grandparent=gp_label_def, pronoun=gp_pronoun)
    )
    meta = {
        "template": "generational_grandchildren",
        "gp_gender": gp_gender,
        "trap": "none",
    }
    return puzzle, answer, meta


def _generational_great_grandchildren(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """Three levels: grandparent -> children -> grandchildren -> great-grandchildren.
    Answer: C x G x GG.
    """
    gp_gender = rng.choice(["m", "f"])
    gp_label = i18n.grandparent_label(gp_gender, language)
    possessive = i18n.pron(gp_gender, "possessive", language)
    # Article-prefixed labels for gendered languages
    gp_label_indef = _art_label(gp_label, gp_gender, language, definite=False, capitalize=True)
    gp_label_def = _art_label(gp_label, gp_gender, language, definite=True)
    gp_pronoun = i18n.fr_pronoun(gp_gender)

    n_children = rng.randint(2, 4)
    n_grand_each = rng.randint(1, 3)
    n_great_each = rng.randint(1, 3)
    answer = n_children * n_grand_each * n_great_each

    children_word = i18n.rel("child", language, n_children)
    grandchildren_word = i18n.rel("child", language, n_grand_each)
    great_gc_word = i18n.rel("child", language, n_great_each)

    puzzle = (
        i18n.narr("has_n_children", language, gp_label=gp_label_indef, n=n_children, relation=children_word) + " "
        + i18n.narr("each_child_has_n", language, possessive=possessive, rel_type=children_word, n=n_grand_each, relation=grandchildren_word) + " "
        + i18n.narr("each_grandchild_has_n", language, n=n_great_each, relation=great_gc_word) + " "
        + i18n.question("how_many_great_grandchildren", language, grandparent=gp_label_def, pronoun=gp_pronoun)
    )
    meta = {
        "template": "generational_great_grandchildren",
        "gp_gender": gp_gender,
        "trap": "none",
    }
    return puzzle, answer, meta


def _generational_cousins(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """'{Name} has N siblings.  {Name}'s parent has one sibling who has M children.
    How many cousins does {Name} have?'
    Answer: M  (cousins = aunt/uncle's children).
    """
    subject_gender = rng.choice(["m", "f"])
    name = i18n.get_name(subject_gender, rng, language)

    # parent's sibling's children = cousins
    n_siblings = rng.randint(0, 3)
    n_cousins = rng.randint(1, 5)
    parent_gender = rng.choice(["m", "f"])
    au_label = i18n.aunt_uncle_label(parent_gender, language)
    p_label = i18n.parent_label(parent_gender, language)
    possessive = i18n.pron(subject_gender, "possessive", language)

    # Article-prefixed labels for gendered languages
    p_label_def = _art_label(p_label, parent_gender, language, definite=True, capitalize=True)
    au_label_indef = _art_label(au_label, parent_gender, language, definite=False)
    # German relative pronoun for "das/die" after aunt/uncle
    de_rel_pron = i18n.de_rel_pronoun(parent_gender)

    sibling_word = i18n.rel("sibling", language, n_siblings)
    children_word = i18n.rel("child", language, n_cousins)

    if n_siblings > 0:
        sibling_text = i18n.narr("sibling_text", language, name=name, n=n_siblings, relation=sibling_word)
    else:
        # Spanish needs gendered "only child" variant
        only_key = f"is_only_child_{subject_gender}" if language == "es" else "is_only_child"
        sibling_text = i18n.narr(only_key, language, name=name) + " "

    # Build the parent-has-one-sibling sentence
    # Different languages need different kwargs:
    #   parent_label     — bare label (EN/DE/ZH/UA use it with possessive/name)
    #   parent_label_art — article-prefixed label (ES/FR use it sentence-initially)
    parent_sibling_text = i18n.narr(
        "parent_has_one_sibling", language,
        possessive=possessive.capitalize(),
        possessive_cap=possessive.capitalize(),
        parent_label=p_label,
        parent_label_art=p_label_def,
        aunt_uncle=au_label_indef,
        n=n_cousins,
        relation=children_word,
        name=name,
        name_ref=name,
        rel_pronoun=de_rel_pron,
    )

    puzzle = sibling_text + parent_sibling_text + " " + i18n.question("how_many_cousins", language, name=name)
    answer = n_cousins
    meta = {
        "template": "generational_cousins",
        "subject_name": name,
        "subject_gender": subject_gender,
        "trap": "confusing_siblings_and_cousins",
    }
    return puzzle, answer, meta


# ---- perspective_shift -----------------------------------------------

def _perspective_equal_brothers_sisters(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """'I have as many brothers as sisters.
     My sister has twice as many brothers as sisters.
     How many of us are there?'
    """
    k = rng.choice([2, 3])
    g = (k + 1) // (k - 1)
    b = g + 1
    answer = b + g

    mult = i18n.multiplier_word(k, language)

    brothers_word = i18n.rel("brother", language, 2)  # plural
    sisters_word = i18n.rel("sister", language, 2)    # plural

    names_list = i18n.get_unique_names(["m", "f"], rng, language)
    narrator = names_list[0]
    sister = names_list[1]
    sibling_label = i18n.rel("sister", language, 1)

    puzzle = (
        i18n.narr("says_equal", language, name=narrator, rel_a=brothers_word, rel_b=sisters_word) + "\n"
        + i18n.narr("says_multiplier", language, name=sister, narrator=narrator, sibling_label=sibling_label, multiplier=mult, rel_a=brothers_word, rel_b=sisters_word) + "\n"
        + i18n.question("how_many_family", language)
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


def _perspective_brother_sister_difference(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """'{Name} says: "I have N more brothers than sisters."
     {Name}'s brother says: "I have N more sisters than brothers."
     How many boys and girls are in the family?'
    """
    g = rng.randint(2, 5)
    b = g
    answer = b + g

    names_list = i18n.get_unique_names(["f", "m"], rng, language)
    sister_name = names_list[0]
    brother_name = names_list[1]

    puzzle = (
        i18n.narr("says_one_more_m", language, name=sister_name) + "\n"
        + i18n.narr("says_one_more_f", language, name=brother_name, sibling_name=sister_name) + "\n"
        + i18n.question("how_many_family", language)
    )
    meta = {
        "template": "perspective_brother_sister_difference",
        "sister": sister_name,
        "brother": brother_name,
        "boys": b,
        "girls": g,
        "trap": "perspective_confusion",
    }
    return puzzle, answer, meta


def _perspective_parent_child_count(rng: random.Random, language: str = "en") -> Tuple[str, int, Dict]:
    """'Each of my sons has the same number of brothers as sisters.
     Each of my daughters has twice as many brothers as sisters.
     How many children do I have?'
    """
    k = rng.choice([2, 3])
    g = (k + 1) // (k - 1)
    b = g + 1
    answer = b + g

    mult = i18n.multiplier_word(k, language)

    parent_gender = rng.choice(["m", "f"])
    parent_name = i18n.get_name(parent_gender, rng, language)

    puzzle = (
        i18n.narr("parent_says_sons", language, name=parent_name, multiplier=mult) + "\n"
        + i18n.question("how_many_children_named_parent", language, name=parent_name)
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
            puzzle_text, answer, meta = template_fn(rng, language=language)

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
        user_prompt, system_prompt, full_prompt = self._build_prompts_yaml(
            "family_relations", language, user_style, system_style,
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
