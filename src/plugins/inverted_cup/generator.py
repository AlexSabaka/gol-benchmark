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
from src.plugins.i18n.loader import load_plugin_i18n

# ---------------------------------------------------------------------------
# Scenario building blocks (loaded from i18n.yaml)
# ---------------------------------------------------------------------------

_i18n = load_plugin_i18n("inverted_cup")
SOURCES = _i18n.get("sources", {})
DESCRIPTION_STYLES = _i18n.get("description_styles", {})
ACTION_QUESTIONS = _i18n.get("action_questions", {})
EXTRA_CONTEXTS = _i18n.get("extra_contexts", {})

# Tags are [text, tag_id] pairs in YAML — convert to tuples for compat
for _lang, _entries in DESCRIPTION_STYLES.items():
    if isinstance(_entries, list) and _entries and isinstance(_entries[0], list):
        DESCRIPTION_STYLES[_lang] = [tuple(e) for e in _entries]


class InvertedCupGenerator(TestCaseGenerator):
    """Generates Inverted Cup test cases."""

    def __init__(self):
        pass  # base class helpers handle PromptEngine

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='count', label='Number of cases', field_type='number',
                        default=100, min_value=1, max_value=500,
                        help='Cases to generate per prompt configuration'),
            ConfigField(name='description_styles', label='Description styles', field_type='multi-select',
                        default=[d[1] for d in DESCRIPTION_STYLES["en"]],
                        options=[d[1] for d in DESCRIPTION_STYLES["en"]], group='advanced',
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
        language = prompt_config.get("language", "en")
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")

        # Select language-specific content
        lang_sources_raw = SOURCES.get(language, SOURCES["en"])
        lang_descs = DESCRIPTION_STYLES.get(language, DESCRIPTION_STYLES["en"])
        lang_questions = ACTION_QUESTIONS.get(language, ACTION_QUESTIONS["en"])
        lang_extras = EXTRA_CONTEXTS.get(language, EXTRA_CONTEXTS["en"])

        # Filter descriptions if config restricts them
        allowed_desc = config.get("description_styles", None)
        descriptions = (
            [d for d in lang_descs if d[1] in allowed_desc]
            if allowed_desc
            else lang_descs
        ) or lang_descs

        # If sources is gender-split (dict with m/f), use the "m" list for
        # combination building; actual gender selection happens per test case.
        is_gendered_sources = isinstance(lang_sources_raw, dict) and "m" in lang_sources_raw
        lang_sources = lang_sources_raw["m"] if is_gendered_sources else lang_sources_raw

        combinations = list(itertools.product(
            range(len(lang_sources)),  # source indices
            descriptions,
            lang_questions,
            lang_extras,
        ))
        rng.shuffle(combinations)

        extended = (combinations * (count // len(combinations) + 2))[:count]

        test_cases: List[TestCase] = []
        for idx, (src_idx, (desc, desc_tag), question, extra) in enumerate(extended):
            # Random subject gender per test case
            subject_gender = rng.choice(["m", "f"])

            # Select source by gender
            if is_gendered_sources:
                source = lang_sources_raw[subject_gender][src_idx % len(lang_sources_raw[subject_gender])]
            else:
                source = lang_sources[src_idx % len(lang_sources)]

            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                language=language,
                source=source,
                desc=desc,
                desc_tag=desc_tag,
                question=question,
                extra=extra,
                subject_gender=subject_gender,
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
        source: str,
        desc: str,
        desc_tag: str,
        question: str,
        extra: str,
        subject_gender: str = "m",
    ) -> TestCase:
        user_prompt, system_prompt, full_prompt = self._build_prompts_yaml(
            "inverted_cup", language, user_style, system_style,
            source=source, description=desc, extra=extra, question=question,
        )

        task_params = {
            "expected_answer": "flip",
            "source": source,
            "description": desc,
            "description_tag": desc_tag,
            "question": question,
            "extra": extra,
            "subject_gender": subject_gender,
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
                "language": language,
            },
            generation_metadata={
                "seed": seed,
                "index": idx,
                "description_tag": desc_tag,
            },
        )
