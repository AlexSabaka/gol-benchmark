"""
Strawberry (Character-Level Reasoning) – Test Case Generator

A family of six character-level reasoning sub-types:

  count         — How many X's in Y?  (original strawberry task)
  reverse       — Reverse a word ("lemon" → "nomel")
  nth_letter    — What's the Nth letter of a word?
  anagram       — Are two words anagrams of each other?
  pangram       — Does a sentence use every letter a-z?
  lipogram      — Does a sentence avoid a specific letter?

The *count* sub-type retains all legacy modes (real / absent_letter /
random / mixed).  Other sub-types draw from curated data files under
``data/``.

Config keys (all optional, sensible defaults provided):
  sub_types         list  sub-types to generate (default ["count"])
  sub_type_weights  dict  relative weights when len(sub_types) > 1
  mode              str   count-mode: "real"|"absent_letter"|"random"|"mixed"
  mixed_weights     dict  weights for count mixed mode
  word_lengths      list  tier filters: ["short","medium","long","extra_long"]
  random_word_min   int   min length for random strings (default 4)
  random_word_max   int   max length for random strings (default 12)
  favor_repeated    bool  prefer letters that appear >1 time (default True)
  language          str   prompt language code (default "en")
"""
from __future__ import annotations

import random
import string
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.plugins.strawberry.prompts import (
    MINIMAL_TEMPLATE, CASUAL_TEMPLATE, LINGUISTIC_INTROS, ANSWER_CUES,
)

# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "strawberry"

# ---------------------------------------------------------------------------
# All six sub-types
# ---------------------------------------------------------------------------
ALL_SUB_TYPES = ["count", "reverse", "nth_letter", "anagram", "pangram", "lipogram"]

# ---------------------------------------------------------------------------
# Word list loader  (count / reverse / nth_letter)
# ---------------------------------------------------------------------------

_WORD_LIST_CACHE: Optional[Dict[str, List[str]]] = None

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

    words_path = _DATA_DIR / "strawberry_words.txt"
    if not words_path.exists():
        raise FileNotFoundError(f"Word list not found: {words_path}")

    all_words: List[str] = []
    with open(words_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            all_words.append(line.lower())

    seen: set[str] = set()
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
# Anagram pairs loader
# ---------------------------------------------------------------------------

_ANAGRAM_CACHE: Optional[List[Tuple[str, str, bool]]] = None


def _load_anagram_pairs() -> List[Tuple[str, str, bool]]:
    """Load curated anagram/non-anagram pairs."""
    global _ANAGRAM_CACHE
    if _ANAGRAM_CACHE is not None:
        return _ANAGRAM_CACHE

    path = _DATA_DIR / "strawberry_anagram_pairs.txt"
    if not path.exists():
        raise FileNotFoundError(f"Anagram pairs not found: {path}")

    pairs: List[Tuple[str, str, bool]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) != 3:
                continue
            w1, w2, label = parts[0].strip().lower(), parts[1].strip().lower(), parts[2].strip().lower()
            pairs.append((w1, w2, label == "true"))

    _ANAGRAM_CACHE = pairs
    return _ANAGRAM_CACHE


# ---------------------------------------------------------------------------
# Pangram loader
# ---------------------------------------------------------------------------

_PANGRAM_CACHE: Optional[List[Tuple[str, bool, str]]] = None


def _load_pangrams() -> List[Tuple[str, bool, str]]:
    """Load pangram / near-pangram sentences.

    Returns list of (sentence, is_pangram, missing_letters_csv).
    """
    global _PANGRAM_CACHE
    if _PANGRAM_CACHE is not None:
        return _PANGRAM_CACHE

    path = _DATA_DIR / "strawberry_pangrams.txt"
    if not path.exists():
        raise FileNotFoundError(f"Pangrams file not found: {path}")

    items: List[Tuple[str, bool, str]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 3:
                continue
            sentence = parts[0].strip()
            is_pangram = parts[1].strip().lower() == "true"
            missing = parts[2].strip()
            items.append((sentence, is_pangram, missing))

    _PANGRAM_CACHE = items
    return _PANGRAM_CACHE


# ---------------------------------------------------------------------------
# Lipogram loader
# ---------------------------------------------------------------------------

_LIPOGRAM_CACHE: Optional[List[Tuple[str, str, bool]]] = None


def _load_lipograms() -> List[Tuple[str, str, bool]]:
    """Load lipogram sentences.

    Returns list of (sentence, avoided_letter, is_lipogram).
    """
    global _LIPOGRAM_CACHE
    if _LIPOGRAM_CACHE is not None:
        return _LIPOGRAM_CACHE

    path = _DATA_DIR / "strawberry_lipograms.txt"
    if not path.exists():
        raise FileNotFoundError(f"Lipograms file not found: {path}")

    items: List[Tuple[str, str, bool]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 3:
                continue
            sentence = parts[0].strip()
            avoided = parts[1].strip().lower()
            is_lipogram = parts[2].strip().lower() == "true"
            items.append((sentence, avoided, is_lipogram))

    _LIPOGRAM_CACHE = items
    return _LIPOGRAM_CACHE


# ===================================================================
# Multilingual question templates — one dict per sub-type
# ===================================================================

# -- COUNT (original) --
QUESTION_TEMPLATES_COUNT: Dict[str, List[str]] = {
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

# -- REVERSE --
QUESTION_TEMPLATES_REVERSE: Dict[str, List[str]] = {
    "en": [
        "What is the word '{word}' spelled backwards?",
        "Reverse the word '{word}'.",
        "Spell the word '{word}' in reverse order.",
        "If you write '{word}' backwards, what do you get?",
    ],
    "es": [
        "¿Cuál es la palabra '{word}' escrita al revés?",
        "Invierte la palabra '{word}'.",
        "Escribe la palabra '{word}' en orden inverso.",
        "Si escribes '{word}' al revés, ¿qué obtienes?",
    ],
    "fr": [
        "Quel est le mot '{word}' épelé à l'envers ?",
        "Inversez le mot '{word}'.",
        "Épelez le mot '{word}' à l'envers.",
        "Si vous écrivez '{word}' à l'envers, qu'obtenez-vous ?",
    ],
    "de": [
        "Wie lautet das Wort '{word}' rückwärts buchstabiert?",
        "Kehre das Wort '{word}' um.",
        "Buchstabiere das Wort '{word}' rückwärts.",
        "Was ergibt sich, wenn man '{word}' rückwärts schreibt?",
    ],
    "zh": [
        "把单词'{word}'倒过来拼写是什么？",
        "请把'{word}'反转过来。",
        "如果把'{word}'倒着写，结果是什么？",
        "倒序拼写单词'{word}'。",
    ],
    "ua": [
        "Яке слово вийде, якщо написати '{word}' задом наперед?",
        "Переверніть слово '{word}'.",
        "Напишіть слово '{word}' у зворотному порядку.",
        "Що вийде, якщо написати '{word}' навпаки?",
    ],
}

# -- NTH LETTER --
QUESTION_TEMPLATES_NTH_LETTER: Dict[str, List[str]] = {
    "en": [
        "What is the {nth} letter of the word '{word}'?",
        "In the word '{word}', what letter is in position {n}?",
        "Tell me the {nth} letter of '{word}'.",
        "Which letter is at position {n} in the word '{word}'?",
    ],
    "es": [
        "¿Cuál es la {nth} letra de la palabra '{word}'?",
        "En la palabra '{word}', ¿qué letra está en la posición {n}?",
        "Dime la {nth} letra de '{word}'.",
        "¿Qué letra ocupa la posición {n} en la palabra '{word}'?",
    ],
    "fr": [
        "Quelle est la {nth} lettre du mot '{word}' ?",
        "Dans le mot '{word}', quelle lettre est en position {n} ?",
        "Dites-moi la {nth} lettre de '{word}'.",
        "Quelle lettre se trouve à la position {n} dans le mot '{word}' ?",
    ],
    "de": [
        "Was ist der {nth} Buchstabe des Wortes '{word}'?",
        "Im Wort '{word}', welcher Buchstabe steht an Position {n}?",
        "Nenne mir den {nth} Buchstaben von '{word}'.",
        "Welcher Buchstabe befindet sich an Position {n} im Wort '{word}'?",
    ],
    "zh": [
        "单词'{word}'的第{n}个字母是什么？",
        "在单词'{word}'中，第{n}个位置的字母是什么？",
        "告诉我'{word}'的第{n}个字母。",
        "'{word}'中第{n}个字母是哪个？",
    ],
    "ua": [
        "Яка {nth} літера у слові '{word}'?",
        "У слові '{word}', яка літера на позиції {n}?",
        "Назвіть {nth} літеру слова '{word}'.",
        "Яка літера стоїть на позиції {n} у слові '{word}'?",
    ],
}

# -- ANAGRAM --
QUESTION_TEMPLATES_ANAGRAM: Dict[str, List[str]] = {
    "en": [
        "Are '{word1}' and '{word2}' anagrams of each other?",
        "Is '{word1}' an anagram of '{word2}'? Answer yes or no.",
        "Can the letters of '{word1}' be rearranged to spell '{word2}'?",
        "Do '{word1}' and '{word2}' contain exactly the same letters?",
    ],
    "es": [
        "¿Son '{word1}' y '{word2}' anagramas entre sí?",
        "¿Es '{word1}' un anagrama de '{word2}'? Responde sí o no.",
        "¿Se pueden reordenar las letras de '{word1}' para formar '{word2}'?",
        "¿Contienen '{word1}' y '{word2}' exactamente las mismas letras?",
    ],
    "fr": [
        "'{word1}' et '{word2}' sont-ils des anagrammes l'un de l'autre ?",
        "'{word1}' est-il un anagramme de '{word2}' ? Répondez oui ou non.",
        "Peut-on réarranger les lettres de '{word1}' pour épeler '{word2}' ?",
        "'{word1}' et '{word2}' contiennent-ils exactement les mêmes lettres ?",
    ],
    "de": [
        "Sind '{word1}' und '{word2}' Anagramme voneinander?",
        "Ist '{word1}' ein Anagramm von '{word2}'? Antworte mit ja oder nein.",
        "Können die Buchstaben von '{word1}' zu '{word2}' umgestellt werden?",
        "Enthalten '{word1}' und '{word2}' genau die gleichen Buchstaben?",
    ],
    "zh": [
        "'{word1}'和'{word2}'是彼此的变位词吗？",
        "'{word1}'是'{word2}'的变位词吗？请回答是或否。",
        "'{word1}'的字母能重新排列成'{word2}'吗？",
        "'{word1}'和'{word2}'包含完全相同的字母吗？",
    ],
    "ua": [
        "Чи є '{word1}' і '{word2}' анаграмами одне одного?",
        "Чи є '{word1}' анаграмою '{word2}'? Відповідайте так або ні.",
        "Чи можна переставити літери '{word1}', щоб отримати '{word2}'?",
        "Чи містять '{word1}' і '{word2}' однакові літери?",
    ],
}

# -- PANGRAM --
QUESTION_TEMPLATES_PANGRAM: Dict[str, List[str]] = {
    "en": [
        "Is the following sentence a pangram (uses every letter of the alphabet at least once)?\n\n\"{sentence}\"",
        "Does this sentence contain all 26 letters of the English alphabet?\n\n\"{sentence}\"",
        "True or false: the sentence \"{sentence}\" is a pangram.",
        "Check whether the following sentence uses every letter from A to Z at least once:\n\n\"{sentence}\"",
    ],
    "es": [
        "¿Es la siguiente oración un pangrama (usa cada letra del alfabeto al menos una vez)?\n\n\"{sentence}\"",
        "¿Contiene esta oración todas las 26 letras del alfabeto inglés?\n\n\"{sentence}\"",
        "Verdadero o falso: la oración \"{sentence}\" es un pangrama.",
        "Comprueba si la siguiente oración usa todas las letras de la A a la Z al menos una vez:\n\n\"{sentence}\"",
    ],
    "fr": [
        "La phrase suivante est-elle un pangramme (utilise chaque lettre de l'alphabet au moins une fois) ?\n\n\"{sentence}\"",
        "Cette phrase contient-elle les 26 lettres de l'alphabet anglais ?\n\n\"{sentence}\"",
        "Vrai ou faux : la phrase \"{sentence}\" est un pangramme.",
        "Vérifiez si la phrase suivante utilise chaque lettre de A à Z au moins une fois :\n\n\"{sentence}\"",
    ],
    "de": [
        "Ist der folgende Satz ein Pangramm (verwendet jeden Buchstaben des Alphabets mindestens einmal)?\n\n\"{sentence}\"",
        "Enthält dieser Satz alle 26 Buchstaben des englischen Alphabets?\n\n\"{sentence}\"",
        "Richtig oder falsch: Der Satz \"{sentence}\" ist ein Pangramm.",
        "Prüfe, ob der folgende Satz jeden Buchstaben von A bis Z mindestens einmal verwendet:\n\n\"{sentence}\"",
    ],
    "zh": [
        "以下句子是否是全字母句（至少使用了字母表中的每个字母一次）？\n\n\"{sentence}\"",
        "这个句子是否包含英语字母表的全部26个字母？\n\n\"{sentence}\"",
        "判断：句子\"{sentence}\"是一个全字母句，对还是错？",
        "检查以下句子是否使用了从A到Z的每个字母至少一次：\n\n\"{sentence}\"",
    ],
    "ua": [
        "Чи є наступне речення панграмою (використовує кожну літеру алфавіту принаймні один раз)?\n\n\"{sentence}\"",
        "Чи містить це речення всі 26 літер англійського алфавіту?\n\n\"{sentence}\"",
        "Правда чи ні: речення \"{sentence}\" є панграмою.",
        "Перевірте, чи використовує наступне речення кожну літеру від A до Z принаймні один раз:\n\n\"{sentence}\"",
    ],
}

# -- LIPOGRAM --
QUESTION_TEMPLATES_LIPOGRAM: Dict[str, List[str]] = {
    "en": [
        "Does the following sentence avoid using the letter '{letter}'?\n\n\"{sentence}\"",
        "True or false: the sentence \"{sentence}\" does not contain the letter '{letter}'.",
        "Is the following sentence a lipogram that avoids the letter '{letter}'?\n\n\"{sentence}\"",
        "Check whether the letter '{letter}' appears anywhere in this sentence:\n\n\"{sentence}\"\n\nAnswer yes if it is absent, no if it is present.",
    ],
    "es": [
        "¿Evita la siguiente oración usar la letra '{letter}'?\n\n\"{sentence}\"",
        "Verdadero o falso: la oración \"{sentence}\" no contiene la letra '{letter}'.",
        "¿Es la siguiente oración un lipograma que evita la letra '{letter}'?\n\n\"{sentence}\"",
        "Comprueba si la letra '{letter}' aparece en esta oración:\n\n\"{sentence}\"\n\nResponde sí si está ausente, no si está presente.",
    ],
    "fr": [
        "La phrase suivante évite-t-elle la lettre '{letter}' ?\n\n\"{sentence}\"",
        "Vrai ou faux : la phrase \"{sentence}\" ne contient pas la lettre '{letter}'.",
        "La phrase suivante est-elle un lipogramme évitant la lettre '{letter}' ?\n\n\"{sentence}\"",
        "Vérifiez si la lettre '{letter}' apparaît dans cette phrase :\n\n\"{sentence}\"\n\nRépondez oui si elle est absente, non si elle est présente.",
    ],
    "de": [
        "Vermeidet der folgende Satz den Buchstaben '{letter}'?\n\n\"{sentence}\"",
        "Richtig oder falsch: Der Satz \"{sentence}\" enthält nicht den Buchstaben '{letter}'.",
        "Ist der folgende Satz ein Lipogramm, das den Buchstaben '{letter}' vermeidet?\n\n\"{sentence}\"",
        "Prüfe, ob der Buchstabe '{letter}' in diesem Satz vorkommt:\n\n\"{sentence}\"\n\nAntworte ja, wenn er fehlt, nein, wenn er vorhanden ist.",
    ],
    "zh": [
        "以下句子是否避免使用字母'{letter}'？\n\n\"{sentence}\"",
        "判断：句子\"{sentence}\"中不包含字母'{letter}'，对还是错？",
        "以下句子是否是避免使用字母'{letter}'的避字文？\n\n\"{sentence}\"",
        "检查字母'{letter}'是否出现在这个句子中：\n\n\"{sentence}\"\n\n如果不存在请回答是，如果存在请回答否。",
    ],
    "ua": [
        "Чи уникає наступне речення використання літери '{letter}'?\n\n\"{sentence}\"",
        "Правда чи ні: речення \"{sentence}\" не містить літери '{letter}'.",
        "Чи є наступне речення ліпограмою, що уникає літери '{letter}'?\n\n\"{sentence}\"",
        "Перевірте, чи з'являється літера '{letter}' у цьому реченні:\n\n\"{sentence}\"\n\nВідповідайте так, якщо її немає, ні, якщо вона є.",
    ],
}

# ===================================================================
# User prompt style templates
# ===================================================================
# The {question} placeholder is replaced with the task-specific question.
# The linguistic style intro varies by sub-type category.

# Templates moved to prompts.py

# Minimal / casual wrappers moved to prompts.py

# ===================================================================
# Ordinal helper for nth_letter templates
# ===================================================================

_ORDINALS_EN = {
    1: "1st", 2: "2nd", 3: "3rd",
}

def _ordinal(n: int, language: str = "en") -> str:
    """Return ordinal string for position *n* (1-based)."""
    if language == "en":
        if n in _ORDINALS_EN:
            return _ORDINALS_EN[n]
        return f"{n}th"
    # Other languages: just use the number with a marker
    return str(n)


# ===================================================================
# Generator
# ===================================================================

class StrawberryGenerator(TestCaseGenerator):
    """Generates character-level reasoning test cases across six sub-types."""

    def __init__(self):
        pass  # base class helpers handle PromptEngine

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='sub_types', label='Sub-types', field_type='multi-select',
                        default=['count'],
                        options=ALL_SUB_TYPES,
                        help='Character-level reasoning tasks to include'),
            ConfigField(name='sub_type_weights', label='Sub-type weights', field_type='weight_map',
                        default={st: 1.0 for st in ALL_SUB_TYPES},
                        weight_keys=ALL_SUB_TYPES, group='advanced',
                        help='Relative weights for sub-type selection'),
            ConfigField(name='mode', label='Count mode', field_type='select',
                        default='mixed', options=['real', 'absent_letter', 'random', 'mixed'],
                        help='Mode for the count sub-type only'),
            ConfigField(name='word_lengths', label='Word length tiers', field_type='multi-select',
                        default=['short', 'medium', 'long', 'extra_long'],
                        options=['short', 'medium', 'long', 'extra_long']),
            ConfigField(name='favor_repeated', label='Favor repeated letters', field_type='boolean',
                        default=True, group='advanced',
                        help='Prefer letters that appear more than once (count mode)'),
            ConfigField(name='random_word_min', label='Random word min length', field_type='number',
                        default=4, min_value=2, max_value=20, group='advanced'),
            ConfigField(name='random_word_max', label='Random word max length', field_type='number',
                        default=12, min_value=2, max_value=30, group='advanced'),
            ConfigField(name='mixed_weights', label='Count mixed-mode weights', field_type='weight_map',
                        default={"real": 0.6, "absent_letter": 0.2, "random": 0.2},
                        weight_keys=['real', 'absent_letter', 'random'], group='advanced',
                        help='Probability weights for count mixed mode'),
        ]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, Any],
        count: int,
        seed: int | None = None,
    ) -> List[TestCase]:
        rng = random.Random(seed)

        # Sub-type selection
        sub_types = config.get("sub_types", ["count"])
        sub_type_weights_raw = config.get("sub_type_weights", {st: 1.0 for st in ALL_SUB_TYPES})
        # Filter weights to selected sub-types only
        active_weights = {st: sub_type_weights_raw.get(st, 1.0) for st in sub_types}

        # Count-specific config
        mode = config.get("mode", "mixed")
        mixed_weights = config.get("mixed_weights", {"real": 0.6, "absent_letter": 0.2, "random": 0.2})
        allowed_tiers = config.get("word_lengths", list(_TIERS.keys()))
        rand_min = config.get("random_word_min", 4)
        rand_max = config.get("random_word_max", 12)
        favor_repeated = config.get("favor_repeated", True)
        language = config.get("language", "en")

        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", f"strawberry_{user_style}_{system_style}")

        # Load word pool
        buckets = _load_word_list()
        pool = []
        for tier in allowed_tiers:
            pool.extend(buckets.get(tier, []))
        if not pool:
            pool = sum(buckets.values(), [])

        test_cases: List[TestCase] = []
        for idx in range(count):
            # Pick sub-type
            sub_type = self._pick_weighted(active_weights, rng)

            # Generate case data + question
            task_params, question = self._dispatch_generate(
                sub_type, pool, rng, language,
                mode=mode, mixed_weights=mixed_weights,
                rand_min=rand_min, rand_max=rand_max,
                favor_repeated=favor_repeated,
            )

            tc = self._build_test_case(
                idx=idx, seed=seed, config_name=config_name,
                user_style=user_style, system_style=system_style,
                language=language, sub_type=sub_type,
                task_params=task_params, question=question,
            )
            test_cases.append(tc)

        return test_cases

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch_generate(
        self,
        sub_type: str,
        pool: List[str],
        rng: random.Random,
        language: str,
        *,
        mode: str,
        mixed_weights: Dict[str, float],
        rand_min: int,
        rand_max: int,
        favor_repeated: bool,
    ) -> Tuple[Dict[str, Any], str]:
        """Return (task_params, question) for a given sub_type."""
        if sub_type == "count":
            return self._gen_count(pool, rng, language, mode, mixed_weights,
                                   rand_min, rand_max, favor_repeated)
        elif sub_type == "reverse":
            return self._gen_reverse(pool, rng, language)
        elif sub_type == "nth_letter":
            return self._gen_nth_letter(pool, rng, language)
        elif sub_type == "anagram":
            return self._gen_anagram(rng, language)
        elif sub_type == "pangram":
            return self._gen_pangram(rng, language)
        elif sub_type == "lipogram":
            return self._gen_lipogram(rng, language)
        else:
            raise ValueError(f"Unknown sub_type: {sub_type}")

    # ------------------------------------------------------------------
    # COUNT (original strawberry logic, unchanged)
    # ------------------------------------------------------------------

    def _gen_count(
        self, pool, rng, language, mode, mixed_weights,
        rand_min, rand_max, favor_repeated,
    ) -> Tuple[Dict[str, Any], str]:
        case_mode = self._pick_mode(mode, mixed_weights, rng)
        word, letter, expected, positions = self._generate_count_case(
            case_mode, pool, rng, rand_min, rand_max, favor_repeated,
        )
        question = self._make_question(QUESTION_TEMPLATES_COUNT, word, language, rng,
                                       letter=letter)
        params: Dict[str, Any] = {
            "expected_answer": expected,
            "word": word,
            "letter": letter,
            "word_length": len(word),
            "mode": case_mode,
            "true_count": expected,
            "letter_positions": positions,
        }
        return params, question

    @staticmethod
    def _pick_mode(mode: str, mixed_weights: Dict[str, float], rng: random.Random) -> str:
        if mode != "mixed":
            return mode
        modes = list(mixed_weights.keys())
        weights = [mixed_weights[m] for m in modes]
        return rng.choices(modes, weights=weights, k=1)[0]

    @staticmethod
    def _generate_count_case(
        case_mode: str, pool: List[str], rng: random.Random,
        rand_min: int, rand_max: int, favor_repeated: bool,
    ) -> Tuple[str, str, int, List[int]]:
        if case_mode == "random":
            length = rng.randint(rand_min, rand_max)
            word = "".join(rng.choices(string.ascii_lowercase, k=length))
            letter = rng.choice(string.ascii_lowercase)
        elif case_mode == "absent_letter":
            word = rng.choice(pool)
            present = set(word)
            absent = [c for c in string.ascii_lowercase if c not in present]
            letter = rng.choice(absent) if absent else "z"
        else:  # "real"
            word = rng.choice(pool)
            letters_in_word = list(set(word))
            if favor_repeated:
                counted = [(ch, word.count(ch)) for ch in letters_in_word]
                repeated = [ch for ch, cnt in counted if cnt > 1]
                letter = rng.choice(repeated) if repeated else rng.choice(letters_in_word)
            else:
                letter = rng.choice(letters_in_word)

        expected = word.lower().count(letter.lower())
        positions = [i for i, c in enumerate(word.lower()) if c == letter.lower()]
        return word, letter, expected, positions

    # ------------------------------------------------------------------
    # REVERSE
    # ------------------------------------------------------------------

    def _gen_reverse(self, pool, rng, language) -> Tuple[Dict[str, Any], str]:
        word = rng.choice(pool)
        reversed_word = word[::-1]
        question = self._make_question(QUESTION_TEMPLATES_REVERSE, word, language, rng)
        params: Dict[str, Any] = {
            "expected_answer": reversed_word,
            "word": word,
            "word_length": len(word),
        }
        return params, question

    # ------------------------------------------------------------------
    # NTH LETTER
    # ------------------------------------------------------------------

    def _gen_nth_letter(self, pool, rng, language) -> Tuple[Dict[str, Any], str]:
        word = rng.choice(pool)
        n = rng.randint(1, len(word))  # 1-based
        expected_letter = word[n - 1]
        nth_str = _ordinal(n, language)
        templates = QUESTION_TEMPLATES_NTH_LETTER.get(language, QUESTION_TEMPLATES_NTH_LETTER["en"])
        template = rng.choice(templates)
        question = template.format(word=word, n=n, nth=nth_str)
        params: Dict[str, Any] = {
            "expected_answer": expected_letter,
            "word": word,
            "n": n,
            "word_length": len(word),
        }
        return params, question

    # ------------------------------------------------------------------
    # ANAGRAM
    # ------------------------------------------------------------------

    def _gen_anagram(self, rng, language) -> Tuple[Dict[str, Any], str]:
        pairs = _load_anagram_pairs()
        w1, w2, is_anagram = rng.choice(pairs)
        templates = QUESTION_TEMPLATES_ANAGRAM.get(language, QUESTION_TEMPLATES_ANAGRAM["en"])
        template = rng.choice(templates)
        question = template.format(word1=w1, word2=w2)
        params: Dict[str, Any] = {
            "expected_answer": is_anagram,
            "word1": w1,
            "word2": w2,
            "is_anagram": is_anagram,
        }
        return params, question

    # ------------------------------------------------------------------
    # PANGRAM
    # ------------------------------------------------------------------

    def _gen_pangram(self, rng, language) -> Tuple[Dict[str, Any], str]:
        items = _load_pangrams()
        sentence, is_pangram, missing = rng.choice(items)
        templates = QUESTION_TEMPLATES_PANGRAM.get(language, QUESTION_TEMPLATES_PANGRAM["en"])
        template = rng.choice(templates)
        question = template.format(sentence=sentence)
        params: Dict[str, Any] = {
            "expected_answer": is_pangram,
            "sentence": sentence,
            "is_pangram": is_pangram,
            "missing_letters": missing,
        }
        return params, question

    # ------------------------------------------------------------------
    # LIPOGRAM
    # ------------------------------------------------------------------

    def _gen_lipogram(self, rng, language) -> Tuple[Dict[str, Any], str]:
        items = _load_lipograms()
        sentence, avoided_letter, is_lipogram = rng.choice(items)
        templates = QUESTION_TEMPLATES_LIPOGRAM.get(language, QUESTION_TEMPLATES_LIPOGRAM["en"])
        template = rng.choice(templates)
        question = template.format(sentence=sentence, letter=avoided_letter)
        params: Dict[str, Any] = {
            "expected_answer": is_lipogram,
            "sentence": sentence,
            "avoided_letter": avoided_letter,
            "is_lipogram": is_lipogram,
        }
        return params, question

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_weighted(weights: Dict[str, float], rng: random.Random) -> str:
        keys = list(weights.keys())
        vals = [weights[k] for k in keys]
        return rng.choices(keys, weights=vals, k=1)[0]

    @staticmethod
    def _make_question(
        templates_dict: Dict[str, List[str]],
        word: str,
        language: str,
        rng: random.Random,
        **kwargs: Any,
    ) -> str:
        templates = templates_dict.get(language, list(templates_dict.values())[0])
        template = rng.choice(templates)
        return template.format(word=word, **kwargs)

    def _build_test_case(
        self,
        idx: int,
        seed: int | None,
        config_name: str,
        user_style: str,
        system_style: str,
        language: str,
        sub_type: str,
        task_params: Dict[str, Any],
        question: str,
    ) -> TestCase:
        # Build user prompt from style
        user_prompt = self._format_user_prompt(
            question, user_style, language, sub_type)

        system_prompt = self._get_system_prompt(system_style, language)

        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

        seed_label = seed if seed is not None else 0

        # Inject sub_type into task_params
        task_params["sub_type"] = sub_type

        return TestCase(
            test_id=f"strawberry_{seed_label}_{idx:04d}",
            task_type="strawberry",
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
            },
        )

    @staticmethod
    def _format_user_prompt(
        question: str, user_style: str, language: str, sub_type: str,
    ) -> str:
        if user_style == "minimal":
            tmpl = MINIMAL_TEMPLATE.get(language, MINIMAL_TEMPLATE["en"])
            return tmpl.format(question=question).strip()
        elif user_style == "linguistic":
            intros = LINGUISTIC_INTROS.get(language, LINGUISTIC_INTROS["en"])
            intro = intros.get(sub_type, intros["count"])
            cues = ANSWER_CUES.get(language, ANSWER_CUES["en"])
            cue = cues.get(sub_type, cues["count"])
            return f"{intro}\n\n{question}\n\n{cue}".strip()
        else:  # casual (default)
            tmpl = CASUAL_TEMPLATE.get(language, CASUAL_TEMPLATE["en"])
            return tmpl.format(question=question).strip()
