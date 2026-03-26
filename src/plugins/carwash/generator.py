"""
Carwash Paradox – Test Case Generator

Generates variations of the "should I walk or drive to the carwash" puzzle.

Parametrisation axes:
- distance_description: how far the carwash is expressed in words
- framing: how the need to clean the car is introduced
- weather: optional environmental context (no bearing on answer)
- urgency: how pressing the need is (no bearing on answer)
- transport_detail: optional extra info about where the car is
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.plugins.carwash.prompts import USER_PROMPT_TEMPLATES


# ---------------------------------------------------------------------------
# Scenario templates
# ---------------------------------------------------------------------------

DISTANCES = [
    {"label": "50m",          "desc": "just 50 metres away", "colloquial": "right around the corner"},
    {"label": "100m",         "desc": "only 100 metres away", "colloquial": "a stone's throw away"},
    {"label": "200m",         "desc": "barely 200 metres away", "colloquial": "a very short walk away"},
    {"label": "corner",       "desc": "literally around the corner", "colloquial": "just around the corner"},
    {"label": "2min_walk",    "desc": "only a two-minute walk away", "colloquial": "two minutes on foot"},
]

FRAMINGS = [
    "My car is quite dirty and I'd like to wash it.",
    "I need to get my car cleaned today.",
    "I want to take my car to the carwash.",
    "My car desperately needs a wash — it's covered in mud.",
    "I've been meaning to wash my car for weeks.",
    "I just noticed how dirty my car is.",
]

WEATHER_CONTEXTS = [
    "",                                          # no weather context
    "The weather is nice, perfect for a walk. ",
    "It's a sunny day outside. ",
    "It's a bit cold but dry. ",
]

URGENCY_PHRASES = [
    "",
    "I'm not in a rush. ",
    "I have some free time right now. ",
    "I want to do it as quickly as possible. ",
]

TRANSPORT_DETAILS = [
    "",                                          # nothing extra
    "My car is parked right outside my house. ",
    "My car is sitting in the driveway. ",
]

QUESTION_VARIANTS = [
    "Should I walk or drive to the carwash?",
    "Is it better to walk or drive there?",
    "What's the best way to get to the carwash — on foot or by car?",
    "Would you walk or drive in this situation?",
    "Walk or drive — what would you recommend?",
    "How should I travel to the carwash — walking or driving?",
]

# ---------------------------------------------------------------------------
# System-prompt / user-prompt templates
# ---------------------------------------------------------------------------


# Templates moved to prompts.py


class CarwashGenerator(TestCaseGenerator):
    """Generates Carwash Paradox test cases."""

    def __init__(self):
        pass  # base class helpers handle PromptEngine

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='distances', label='Distances', field_type='multi-select',
                        default=[d['label'] for d in DISTANCES],
                        options=[d['label'] for d in DISTANCES], group='advanced',
                        help='Distance descriptions to include in scenarios'),
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

        # Allowed distances (can be filtered via config)
        allowed_distances = config.get("distances", [d["label"] for d in DISTANCES])
        distances = [d for d in DISTANCES if d["label"] in allowed_distances]
        if not distances:
            distances = DISTANCES

        # Build the full combinatorial space and sample from it
        combinations = list(itertools.product(
            distances,
            FRAMINGS,
            WEATHER_CONTEXTS,
            URGENCY_PHRASES,
            TRANSPORT_DETAILS,
            QUESTION_VARIANTS,
        ))
        rng.shuffle(combinations)

        # Repeat the list if count > len(combinations) to guarantee diversity
        extended = (combinations * (count // len(combinations) + 2))[:count]

        test_cases: List[TestCase] = []
        for idx, (dist, framing, weather, urgency, transport, question) in enumerate(extended):
            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                language=language,
                dist=dist,
                framing=framing,
                weather=weather,
                urgency=urgency,
                transport=transport,
                question=question,
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
        dist: Dict,
        framing: str,
        weather: str,
        urgency: str,
        transport: str,
        question: str,
    ) -> TestCase:
        setup = framing
        distance_str = dist["desc"]

        user_prompt, system_prompt, full_prompt = self._build_prompts(
            USER_PROMPT_TEMPLATES, language, user_style, system_style,
            setup=setup, distance=distance_str, weather=weather,
            urgency=urgency, transport=transport, question=question,
        )

        task_params = {
            "expected_answer": "drive",
            "distance_label": dist["label"],
            "distance_desc": dist["desc"],
            "framing": framing,
            "weather": weather,
            "urgency": urgency,
            "transport": transport,
            "question": question,
            # Metadata for analysis
            "naive_trap": "walk",
        }

        return TestCase(
            test_id=f"carwash_{seed}_{idx:04d}",
            task_type="carwash",
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
                "distance_label": dist["label"],
            },
        )
