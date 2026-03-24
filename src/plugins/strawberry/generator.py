"""
Strawberry (Letter Counting) – Test Case Generator

Generates "How many X's in Y?" test cases with four modes:
  real          — word from curated list, letter present in the word
  absent_letter — word from curated list, letter NOT in the word (answer = 0)
  random        — random character sequence, any letter query
  mixed         — weighted blend of all three (default)

Config keys (all optional, sensible defaults provided):
  mode              str   "real"|"absent_letter"|"random"|"mixed"  (default "mixed")
  mixed_weights     dict  e.g. {"real": 0.6, "absent_letter": 0.2, "random": 0.2}
  word_lengths      list  tier filters: ["short","medium","long","extra_long"]
  random_word_min   int   min length for random strings (default 4)
  random_word_max   int   max length for random strings (default 12)
  count             int   number of test cases to generate
  language          str   prompt language code (default "en")
  favor_repeated    bool  prefer letters that appear >1 time (default True)
"""
from __future__ import annotations

import os
import random
import string
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.plugins.parse_utils import safe_enum
from src.core.PromptEngine import PromptEngine, SystemPromptStyle, Language

# ---------------------------------------------------------------------------
# Word list loader
# ---------------------------------------------------------------------------

_WORD_LIST_CACHE: Optional[Dict[str, List[str]]] = None

# Length tier boundaries
_TIERS = {
    "short": (3, 5),
    "medium": (6, 9),
    "long": (10, 15),
    "extra_long": (16, 999),
}


def _load_word_list() -> Dict[str, List[str]]:
    """Load and cache the word list, bucketed by length tier."""
    global _WORD_LIST_CACHE
    if _WORD_LIST_CACHE is not None:
        return _WORD_LIST_CACHE

    words_path = Path(__file__).resolve().parents[3] / "data" / "strawberry_words.txt"
    if not words_path.exists():
        raise FileNotFoundError(f"Word list not found: {words_path}")

    all_words: List[str] = []
    with open(words_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            all_words.append(line.lower())

    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for w in all_words:
        if w not in seen:
            seen.add(w)
            unique.append(w)

    buckets: Dict[str, List[str]] = {tier: [] for tier in _TIERS}
    for w in unique:
        for tier, (lo, hi) in _TIERS.items():
            if lo <= len(w) <= hi:
                buckets[tier].append(w)
                break

    _WORD_LIST_CACHE = buckets
    return _WORD_LIST_CACHE


# ---------------------------------------------------------------------------
# Multilingual question templates
# ---------------------------------------------------------------------------
# Each language maps to a list of template strings with {letter} and {word}.

QUESTION_TEMPLATES: Dict[str, List[str]] = {
    "en": [
        "How many times does the letter '{letter}' appear in the word '{word}'?",
        "Count the number of '{letter}' letters in '{word}'.",
        "How many '{letter}'s are in the word '{word}'?",
        "What is the count of the letter '{letter}' in '{word}'?",
        "In the word '{word}', how many times does '{letter}' occur?",
    ],
    "es": [
        "¿Cuántas veces aparece la letra '{letter}' en la palabra '{word}'?",
        "Cuenta el número de letras '{letter}' en '{word}'.",
        "¿Cuántas '{letter}' hay en la palabra '{word}'?",
        "En la palabra '{word}', ¿cuántas veces aparece '{letter}'?",
    ],
    "fr": [
        "Combien de fois la lettre '{letter}' apparaît-elle dans le mot '{word}' ?",
        "Comptez le nombre de '{letter}' dans '{word}'.",
        "Combien de '{letter}' y a-t-il dans le mot '{word}' ?",
        "Dans le mot '{word}', combien de fois la lettre '{letter}' apparaît-elle ?",
    ],
    "de": [
        "Wie oft kommt der Buchstabe '{letter}' im Wort '{word}' vor?",
        "Zähle die Anzahl der '{letter}' in '{word}'.",
        "Wie viele '{letter}' gibt es im Wort '{word}'?",
        "Im Wort '{word}', wie oft kommt '{letter}' vor?",
    ],
    "zh": [
        "字母'{letter}'在单词'{word}'中出现了多少次？",
        "请计算'{word}'中字母'{letter}'的数量。",
        "单词'{word}'中有多少个'{letter}'？",
        "在'{word}'这个词中，'{letter}'出现了几次？",
    ],
    "ua": [
        "Скільки разів літера '{letter}' зустрічається у слові '{word}'?",
        "Порахуйте кількість літер '{letter}' у '{word}'.",
        "Скільки '{letter}' є у слові '{word}'?",
        "У слові '{word}', скільки разів зустрічається '{letter}'?",
    ],
}

# ---------------------------------------------------------------------------
# User prompt templates (per style)
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "minimal": "{question}\n\nAnswer: ",
        "casual": "Hey, quick question — {question}",
        "linguistic": (
            "I have a letter-counting question for you.\n\n"
            "{question}\n\nPlease provide the numerical answer."
        ),
    },
    "es": {
        "minimal": "{question}\n\nRespuesta: ",
        "casual": "Oye, pregunta rápida — {question}",
        "linguistic": (
            "Tengo una pregunta sobre el conteo de letras.\n\n"
            "{question}\n\nPor favor, proporciona la respuesta numérica."
        ),
    },
    "fr": {
        "minimal": "{question}\n\nRéponse : ",
        "casual": "Salut, petite question — {question}",
        "linguistic": (
            "J'ai une question de comptage de lettres pour vous.\n\n"
            "{question}\n\nVeuillez fournir la réponse numérique."
        ),
    },
    "de": {
        "minimal": "{question}\n\nAntwort: ",
        "casual": "Hey, kurze Frage — {question}",
        "linguistic": (
            "Ich habe eine Frage zum Buchstabenzählen.\n\n"
            "{question}\n\nBitte geben Sie die numerische Antwort an."
        ),
    },
    "zh": {
        "minimal": "{question}\n\n答案：",
        "casual": "嘿，快问一下——{question}",
        "linguistic": (
            "我有一个关于字母计数的问题。\n\n"
            "{question}\n\n请提供数字答案。"
        ),
    },
    "ua": {
        "minimal": "{question}\n\nВідповідь: ",
        "casual": "Привіт, швидке питання — {question}",
        "linguistic": (
            "У мене є питання про підрахунок літер.\n\n"
            "{question}\n\nБудь ласка, надайте числову відповідь."
        ),
    },
}


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class StrawberryGenerator(TestCaseGenerator):
    """Generates letter-counting test cases."""

    def __init__(self):
        self._prompt_engine = PromptEngine()

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='mode', label='Mode', field_type='select',
                        default='mixed', options=['real', 'absent_letter', 'random', 'mixed']),
            ConfigField(name='word_lengths', label='Word length tiers', field_type='multi-select',
                        default=['short', 'medium', 'long', 'extra_long'],
                        options=['short', 'medium', 'long', 'extra_long']),
            ConfigField(name='favor_repeated', label='Favor repeated letters', field_type='boolean',
                        default=True, group='advanced',
                        help='Prefer letters that appear more than once'),
            ConfigField(name='random_word_min', label='Random word min length', field_type='number',
                        default=4, min_value=2, max_value=20, group='advanced'),
            ConfigField(name='random_word_max', label='Random word max length', field_type='number',
                        default=12, min_value=2, max_value=30, group='advanced'),
            ConfigField(name='mixed_weights', label='Mixed mode weights', field_type='weight_map',
                        default={"real": 0.6, "absent_letter": 0.2, "random": 0.2},
                        weight_keys=['real', 'absent_letter', 'random'], group='advanced',
                        help='Probability weights for mixed mode'),
        ]

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, Any],
        count: int,
        seed: int | None = None,
    ) -> List[TestCase]:
        rng = random.Random(seed)

        mode = config.get("mode", "mixed")
        mixed_weights = config.get("mixed_weights", {
            "real": 0.6,
            "absent_letter": 0.2,
            "random": 0.2,
        })
        allowed_tiers = config.get("word_lengths", list(_TIERS.keys()))
        rand_min = config.get("random_word_min", 4)
        rand_max = config.get("random_word_max", 12)
        favor_repeated = config.get("favor_repeated", True)
        language = config.get("language", "en")

        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", f"strawberry_{user_style}_{system_style}")

        # Load words
        buckets = _load_word_list()
        pool = []
        for tier in allowed_tiers:
            pool.extend(buckets.get(tier, []))
        if not pool:
            pool = sum(buckets.values(), [])

        test_cases: List[TestCase] = []
        for idx in range(count):
            # Pick mode for this case
            case_mode = self._pick_mode(mode, mixed_weights, rng)

            word, letter, expected, positions = self._generate_case(
                case_mode, pool, rng, rand_min, rand_max, favor_repeated,
            )

            question = self._make_question(word, letter, language, rng)
            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                language=language,
                word=word,
                letter=letter,
                expected=expected,
                positions=positions,
                case_mode=case_mode,
                question=question,
            )
            test_cases.append(tc)

        return test_cases

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_mode(
        mode: str,
        mixed_weights: Dict[str, float],
        rng: random.Random,
    ) -> str:
        if mode != "mixed":
            return mode
        modes = list(mixed_weights.keys())
        weights = [mixed_weights[m] for m in modes]
        return rng.choices(modes, weights=weights, k=1)[0]

    @staticmethod
    def _generate_case(
        case_mode: str,
        pool: List[str],
        rng: random.Random,
        rand_min: int,
        rand_max: int,
        favor_repeated: bool,
    ) -> Tuple[str, str, int, List[int]]:
        """Return (word, letter, expected_count, positions)."""
        if case_mode == "random":
            length = rng.randint(rand_min, rand_max)
            word = "".join(rng.choices(string.ascii_lowercase, k=length))
            letter = rng.choice(string.ascii_lowercase)
        elif case_mode == "absent_letter":
            word = rng.choice(pool)
            present = set(word)
            absent = [c for c in string.ascii_lowercase if c not in present]
            if not absent:
                # Extremely unlikely — fallback to 'z' or first missing
                letter = "z"
            else:
                letter = rng.choice(absent)
        else:  # "real"
            word = rng.choice(pool)
            letters_in_word = list(set(word))
            if favor_repeated:
                counted = [(ch, word.count(ch)) for ch in letters_in_word]
                repeated = [ch for ch, cnt in counted if cnt > 1]
                if repeated:
                    letter = rng.choice(repeated)
                else:
                    letter = rng.choice(letters_in_word)
            else:
                letter = rng.choice(letters_in_word)

        expected = word.lower().count(letter.lower())
        positions = [i for i, c in enumerate(word.lower()) if c == letter.lower()]
        return word, letter, expected, positions

    @staticmethod
    def _make_question(
        word: str,
        letter: str,
        language: str,
        rng: random.Random,
    ) -> str:
        templates = QUESTION_TEMPLATES.get(language, QUESTION_TEMPLATES["en"])
        template = rng.choice(templates)
        return template.format(word=word, letter=letter)

    def _build_test_case(
        self,
        idx: int,
        seed: int | None,
        config_name: str,
        user_style: str,
        system_style: str,
        language: str,
        word: str,
        letter: str,
        expected: int,
        positions: List[int],
        case_mode: str,
        question: str,
    ) -> TestCase:
        user_templates = USER_PROMPT_TEMPLATES.get(language, USER_PROMPT_TEMPLATES["en"])
        user_template = user_templates.get(user_style, user_templates["casual"])
        user_prompt = user_template.format(question=question).strip()

        sys_enum = safe_enum(SystemPromptStyle, system_style, SystemPromptStyle.ANALYTICAL)
        lang_enum = safe_enum(Language, language, Language.EN)
        system_prompt = self._prompt_engine.get_system_prompt_by_enum(sys_enum, lang_enum)

        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

        seed_label = seed if seed is not None else 0

        return TestCase(
            test_id=f"strawberry_{seed_label}_{idx:04d}",
            task_type="strawberry",
            config_name=config_name,
            prompts={
                "system": system_prompt,
                "user": user_prompt,
                "full": full_prompt,
            },
            task_params={
                "expected_answer": expected,
                "word": word,
                "letter": letter,
                "word_length": len(word),
                "mode": case_mode,
                "true_count": expected,
                "letter_positions": positions,
            },
            prompt_metadata={
                "user_style": user_style,
                "system_style": system_style,
                "language": language,
            },
            generation_metadata={
                "seed": seed,
                "index": idx,
                "mode": case_mode,
            },
        )
