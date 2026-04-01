"""
Multilingual smoke tests for all plugin generators.

Tests that every plugin × every language combination:
  - Generates at least 1 test case without crashing
  - Returns non-empty user and system prompts
  - Stores the correct language in task_params
  - Produces language-appropriate content (non-ASCII for zh/ua)
"""

import pytest
from src.plugins import PluginRegistry
from src.plugins.base import TestCase


# ── 6 supported languages ───────────────────────────────────────────────────
LANGUAGES = ["en", "es", "fr", "de", "zh", "ua"]

# ── smallest valid config per plugin (1 test case, deterministic) ────────────
MINIMAL_CONFIGS = {
    "game_of_life": {
        "difficulty_levels": ["EASY"],
        "grids_per_difficulty": 1,
        "density": 0.5,
        "cell_markers": "1,0",
    },
    "arithmetic": {
        "complexity": [2],
        "expressions_per_target": 1,
        "target_values": [5],
    },
    "linda_fallacy": {
        "num_options": 4,
        "personas_per_config": 1,
    },
    "cellular_automata_1d": {
        "rules": [110],
        "tests_per_rule": 1,
        "width": 8,
        "steps": 1,
    },
    "ascii_shapes": {
        "question_types": ["dimensions"],
    },
    "object_tracking": {
        "distractor_count": [0],
        "post_inversion_moves": [0],
    },
    "sally_anne": {
        "cases_per_config": 1,
    },
    "carwash": {},
    "inverted_cup": {},
    "strawberry": {
        "sub_types": ["count"],
    },
    "measure_comparison": {
        "comparison_type": "same_unit",
        "unit_categories": ["length"],
    },
    "grid_tasks": {
        "cases_per_config": 1,
        "min_rows": 2,
        "max_rows": 3,
        "min_cols": 2,
        "max_cols": 3,
    },
    "time_arithmetic": {
        "sub_types": ["interval"],
    },
    "misquote": {
        "count": 1,
    },
    "false_premise": {
        "count": 1,
        "domains": ["chemistry"],
    },
    "family_relations": {
        "sub_types": ["sibling_count"],
        "count": 1,
    },
    "encoding_cipher": {
        "count": 1,
        "encoding_types": ["base64"],
        "task_modes": ["decode_only"],
    },
    "symbol_arithmetic": {
        "count": 1,
        "set_size": 3,
    },
}

# Languages where user prompts are expected to have non-ASCII content
_NON_ASCII_LANGUAGES = {"zh", "ua"}

# Plugins where user prompt body/scenario is English-only by design
# (multilingual wrapping only — minimal style may be all-ASCII)
_EN_BODY_PLUGINS = {
    "ascii_shapes",    # Question text from _generate_question() is EN-only
    "false_premise",   # Chemistry/physics scenarios are EN-only
    "inverted_cup",    # Cup descriptions are EN-only
    "misquote",        # Quotes & framing templates are EN-only
    "family_relations", # Puzzle text is EN-only
}


def _all_plugin_names():
    """Return sorted list of all registered plugin task types."""
    return sorted(PluginRegistry.list_task_types())


def _make_prompt_config(language: str) -> dict:
    return {
        "user_style": "minimal",
        "system_style": "analytical",
        "name": f"smoke_{language}",
        "language": language,
    }


# Build parametrize matrix: (plugin_name, language)
_PARAMS = [
    (name, lang)
    for name in _all_plugin_names()
    for lang in LANGUAGES
]


@pytest.mark.parametrize("plugin_name,language", _PARAMS,
                         ids=[f"{n}-{l}" for n, l in _PARAMS])
class TestMultilingualGeneration:
    """Smoke-test every plugin × language combination for generation."""

    def test_generate_batch_smoke(self, plugin_name: str, language: str):
        """generate_batch returns ≥1 TestCase with correct metadata."""
        plugin = PluginRegistry.get(plugin_name)
        assert plugin is not None, f"Plugin '{plugin_name}' not in registry"

        generator = plugin.get_generator()
        config = MINIMAL_CONFIGS.get(plugin_name, {})
        prompt_config = _make_prompt_config(language)

        test_cases = generator.generate_batch(
            config=config,
            prompt_config=prompt_config,
            count=1,
            seed=42,
        )

        # ── basic structure ──────────────────────────────────────────────
        assert len(test_cases) >= 1, (
            f"{plugin_name}/{language}: generate_batch returned 0 cases"
        )
        tc = test_cases[0]
        assert isinstance(tc, TestCase)
        assert tc.task_type == plugin_name

        # ── prompts populated ────────────────────────────────────────────
        assert tc.prompts.get("user"), (
            f"{plugin_name}/{language}: empty user prompt"
        )
        assert tc.prompts.get("system") is not None, (
            f"{plugin_name}/{language}: missing system prompt key"
        )

        # ── language stored in task_params (not all plugins do this) ────
        stored_lang = tc.task_params.get("language", tc.task_params.get("lang"))
        if stored_lang is not None:
            assert stored_lang == language, (
                f"{plugin_name}/{language}: task_params language is "
                f"'{stored_lang}' instead of '{language}'"
            )

    def test_non_ascii_prompt_for_non_latin_languages(
        self, plugin_name: str, language: str,
    ):
        """For zh/ua, user prompt should contain non-ASCII characters."""
        if language not in _NON_ASCII_LANGUAGES:
            pytest.skip(f"ASCII-only check not applicable for '{language}'")
        if plugin_name in _EN_BODY_PLUGINS:
            pytest.skip(
                f"'{plugin_name}' has EN-only scenario body by design "
                "(multilingual wrapper only)"
            )

        plugin = PluginRegistry.get(plugin_name)
        generator = plugin.get_generator()
        config = MINIMAL_CONFIGS.get(plugin_name, {})
        prompt_config = _make_prompt_config(language)

        test_cases = generator.generate_batch(
            config=config,
            prompt_config=prompt_config,
            count=1,
            seed=42,
        )
        if not test_cases:
            pytest.skip("no test cases generated")

        user_prompt = test_cases[0].prompts.get("user", "")
        has_non_ascii = any(ord(c) > 127 for c in user_prompt)
        assert has_non_ascii, (
            f"{plugin_name}/{language}: user prompt appears to be ASCII-only, "
            f"expected non-ASCII characters for '{language}'. "
            f"Prompt snippet: {user_prompt[:120]!r}"
        )
