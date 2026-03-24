"""
Inverted Cup – Test Case Generator

Generates variations of the "sealed top / open bottom cup" puzzle.

Parametrisation axes:
- source: how the person came to have the cup (gift, found, bought, etc.)
- description_style: how the unusual orientation is described
- action_question: what the person wants to do with it
- extra_context: optional extra detail (unusual material, purpose)
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.core.PromptEngine import PromptEngine, SystemPromptStyle, Language


# ---------------------------------------------------------------------------
# Scenario building blocks
# ---------------------------------------------------------------------------

SOURCES = [
    "My friend gifted me this unusual cup.",
    "I bought this novelty cup online.",
    "I found this strange cup at a garage sale.",
    "Someone left this cup on my desk as a joke.",
    "I received this cup as a birthday present.",
    "I picked up this curious cup at a souvenir shop.",
    "I won this cup in a competition.",
]

DESCRIPTION_STYLES = [
    # (description, tag)
    ("The top is completely sealed and the bottom is open.",              "sealed_top_open_bottom"),
    ("It has a solid, sealed lid on top and an open hole at the bottom.", "lid_top_hole_bottom"),
    ("The cup is upside-down: the opening faces down and the base is at the top.", "upside_down_explicit"),
    ("The rim (opening) is at the bottom, and the solid closed end is at the top.", "rim_at_bottom"),
    ("It looks like a normal cup but inverted: closed on top, open on the bottom.", "inverted_normal"),
    ("The cup's mouth points downward and the sealed end is on top.",    "mouth_down"),
    ("When placed on a table, the closed end sits on top and the opening faces the table.", "closed_on_top"),
]

ACTION_QUESTIONS = [
    "How should I use this cup to drink from it?",
    "What's the correct way to use this cup?",
    "How do I drink from this cup?",
    "What should I do to be able to use this cup normally?",
    "How do I use this cup to hold a liquid?",
    "What do I need to do first before I can drink from this cup?",
    "I want to fill it with water — what should I do?",
]

EXTRA_CONTEXTS = [
    "",                                                    # no extra
    "It's made of a transparent material so I can see it clearly. ",
    "It's a sturdy plastic cup. ",
    "The seal on the top is permanent and cannot be removed. ",
    "The cup is otherwise identical to a normal cup. ",
]

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


USER_PROMPT_TEMPLATES = {
    "minimal": "{source} {description} {extra}{question}",
    "casual": "Hey, I have a funny situation. {source} {description} {extra}{question}",
    "linguistic": (
        "I have a practical question about an unusual object I own.\n\n"
        "{source} {description} {extra}\n\n{question}"
    ),
}


class InvertedCupGenerator(TestCaseGenerator):
    """Generates Inverted Cup test cases."""

    def __init__(self):
        self._prompt_engine = PromptEngine()

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='description_styles', label='Description styles', field_type='multi-select',
                        default=[d[1] for d in DESCRIPTION_STYLES],
                        options=[d[1] for d in DESCRIPTION_STYLES], group='advanced',
                        help='Which cup description styles to include'),
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
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")

        # Filter descriptions if config restricts them
        allowed_desc = config.get("description_styles", None)
        descriptions = (
            [d for d in DESCRIPTION_STYLES if d[1] in allowed_desc]
            if allowed_desc
            else DESCRIPTION_STYLES
        ) or DESCRIPTION_STYLES

        combinations = list(itertools.product(
            SOURCES,
            descriptions,
            ACTION_QUESTIONS,
            EXTRA_CONTEXTS,
        ))
        rng.shuffle(combinations)

        extended = (combinations * (count // len(combinations) + 2))[:count]

        test_cases: List[TestCase] = []
        for idx, (source, (desc, desc_tag), question, extra) in enumerate(extended):
            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                source=source,
                desc=desc,
                desc_tag=desc_tag,
                question=question,
                extra=extra,
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
        source: str,
        desc: str,
        desc_tag: str,
        question: str,
        extra: str,
    ) -> TestCase:
        user_template = USER_PROMPT_TEMPLATES.get(user_style, USER_PROMPT_TEMPLATES["casual"])
        user_prompt = user_template.format(
            source=source,
            description=desc,
            extra=extra,
            question=question,
        ).strip()

        try:
            sys_enum = SystemPromptStyle(system_style)
        except ValueError:
            sys_enum = SystemPromptStyle.ANALYTICAL
        system_prompt = self._prompt_engine.get_system_prompt_by_enum(sys_enum)
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

        task_params = {
            "expected_answer": "flip",
            "source": source,
            "description": desc,
            "description_tag": desc_tag,
            "question": question,
            "extra": extra,
        }

        return TestCase(
            test_id=f"inverted_cup_{seed}_{idx:04d}",
            task_type="inverted_cup",
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
            },
            generation_metadata={
                "seed": seed,
                "index": idx,
                "description_tag": desc_tag,
            },
        )
