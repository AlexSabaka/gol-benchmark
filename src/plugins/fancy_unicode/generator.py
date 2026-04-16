"""Test-case generator for the fancy_unicode plugin.

Produces decode_only and decode_and_act test cases across 12 Unicode
encoding families in 3 tiers.  Unlike encoding_cipher, the encoding
family name is never revealed in the prompt — the model must recognise
the decorative Unicode style on its own.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import ConfigField, TestCase, TestCaseGenerator
from src.plugins.parse_utils import safe_enum
from src.core.PromptEngine import Language

from .families import (
    ALL_FAMILIES,
    TIER1_FAMILIES,
    encode_text,
    get_family_list,
    text_covered_by,
    word_covered_by,
    UPPERCASE_ONLY_FAMILIES,
)

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent / "data"
# Reuse encoding_cipher's curated word list for decode_and_act pool
_EC_DATA_DIR = Path(__file__).resolve().parent.parent / "encoding_cipher" / "data"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALL_TASK_MODES = ["decode_only", "decode_and_act"]

_LENGTH_RANGES: Dict[str, Tuple[int, int]] = {
    "short":  (3, 8),
    "medium": (8, 20),
    "long":   (20, 40),
}

# ---------------------------------------------------------------------------
# Sentence fragments for decode_only mode
# Deliberately varied length; many use only common letters to survive Tier 2
# coverage filters (subscript / superscript lose b,c,d,f,g,q,w,x,y,z).
# Coverage filtering is applied per-family at generation time.
# ---------------------------------------------------------------------------
_SENTENCE_FRAGMENTS: List[str] = [
    "The ancient lighthouse stood alone on the rocky shore",
    "A single lantern illuminated the stone hallway",
    "The navigator studied the stars to find the route home",
    "Tall pine trees lined the mountain trail",
    "The river ran silently past the old stone mill",
    "An explorer mapped the northern coastline in summer",
    "The astronomer noted a new star in the eastern horizon",
    "A lone sentinel kept watch over the iron gate",
    "The historian read the manuscript in silence",
    "Morning mist rose over the lake at sunrise",
    "The mason cut the granite into even slabs",
    "A thin line of smoke rose from the inn chimney",
    "The minister opened the letter and read it aloud",
    "Rain patterns on the tile roof created a gentle rhythm",
    "The lookout tower offered a panoramic view of the plains",
    "Moonlight filtered through the tall oaks and elms",
    "The archivist sorted letters in alphabetical order",
    "Sparrows nested in the eaves of the market hall",
    "The artist sketched the outline of the peaks in ink",
    "A patient tortoise sat motionless near the garden path",
    "The inlet was too shallow for the large sailing vessels",
    "Polished mirrors reflected the interior of the throne hall",
    "The sentinel remains at the post until noon",
    "Rose petals littered the stone steps in autumn",
    "The pilot noted the terrain markers on the eastern route",
    "Autumn leaves settled on the still surface of the pool",
    "The clerk tallied the totals in neat rows",
    "A passing traveller stopped at the milestone to rest",
    "The port master entered the arrival in the logroom register",
    "Snow melted slowly on the south-facing slopes",
    "The mason repaired the ornate stone railing at sunrise",
    "A rope net hung over the small pier to keep the nets",
    "The apprentice trimmed the lantern wick at noon",
    "Iron hooks lined the interior of the storage room",
    "The seasonal market opened on the first morning of spring",
    "Terns hovered near the pier in the late afternoon",
    "The innkeeper stoked the hearth as the storm approached",
    "Moonrise painted the hillside in a pale silver tone",
    "The lookout spotted the mast tip on the horizon at noon",
    "A line of travellers rested in the shade of an oak tree",
]

# ---------------------------------------------------------------------------
# Instruction templates for decode_and_act mode (EN only).
# Reused from the encoding_cipher plugin pattern.
# The model must decode the instruction AND follow it.
# ---------------------------------------------------------------------------
_ACT_INSTRUCTIONS: List[str] = [
    "The secret word is: {word}. Reply with only that word.",
    "Your task: respond with the single word '{word}' and nothing else.",
    "Please reply with exactly this word: {word}",
    "After decoding this message, say only the word '{word}' as your answer.",
    "Instruction: output the word '{word}' and nothing more.",
]

# ---------------------------------------------------------------------------
# Mode- and style-specific instruction text — injected as {instruction} in i18n.yaml.
# The family name is intentionally absent; the model must recognise the style.
# minimal: bare question  |  casual: conversational  |  linguistic: full context
# ---------------------------------------------------------------------------
_DECODE_INSTRUCTIONS: Dict[str, Dict[str, str]] = {
    "decode_only": {
        "minimal":    "What does it say:",
        "casual":     "got this funky text, what does it say?",
        "linguistic": (
            "The following text uses a decorative Unicode style. "
            "Decode it and return the original plain text."
        ),
    },
    "decode_and_act": {
        "minimal":    "Read and follow the instruction:",
        "casual":     "got this funky message. Decode it and do what it says.",
        "linguistic": (
            "The following text encodes an instruction using a decorative Unicode style. "
            "Decode it and carry out the instruction."
        ),
    },
}

# ---------------------------------------------------------------------------
# Coverage-filtered pool cache
# key: (family, pool_id)  — pool_id avoids false cache hits between pools
# ---------------------------------------------------------------------------
_POOL_CACHE: Dict[Tuple[str, int], List[str]] = {}


def _filter_pool(pool: List[str], family: str) -> List[str]:
    """Return *pool* entries that can be fully encoded by *family*."""
    key = (family, id(pool))
    if key not in _POOL_CACHE:
        _POOL_CACHE[key] = [s for s in pool if text_covered_by(s, family)]
    return _POOL_CACHE[key]


def _filter_words(words: List[str], family: str) -> List[str]:
    """Return words compatible with *family* (single-word coverage check)."""
    key = (family, id(words))
    if key not in _POOL_CACHE:
        _POOL_CACHE[key] = [w for w in words if word_covered_by(w, family)]
    return _POOL_CACHE[key]


# ---------------------------------------------------------------------------
# Word list loader (for decode_and_act pool)
# ---------------------------------------------------------------------------
_WORD_LIST_CACHE: Dict[str, List[str]] = {}


def _load_words() -> List[str]:
    """Load the decode_and_act word list.

    Uses encoding_cipher's curated word pool (as specified by the PRD).
    Falls back to an inline minimal list if the file is missing.
    """
    if "en" in _WORD_LIST_CACHE:
        return _WORD_LIST_CACHE["en"]

    words_path = _EC_DATA_DIR / "words_en.txt"
    if not words_path.exists():
        _log.warning(
            "encoding_cipher words_en.txt not found at %s; using fallback", words_path
        )
        fallback = [
            "alchemy", "anomaly", "aperture", "armistice", "aurora",
            "almanac", "arsenal", "sentinel", "terrain", "ornament",
            "lantern", "mineral", "pioneer", "serene", "mosaic",
        ]
        _WORD_LIST_CACHE["en"] = fallback
        return fallback

    words: List[str] = []
    with open(words_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.append(line.lower())

    _WORD_LIST_CACHE["en"] = words
    return words


# ---------------------------------------------------------------------------
# Plaintext composition
# ---------------------------------------------------------------------------

def _pick_weighted(options: List[str], weights: Dict[str, float], rng: random.Random) -> str:
    w = [weights.get(o, 1.0) for o in options]
    return rng.choices(options, weights=w, k=1)[0]


def _bucket_fragments(
    fragments: List[str],
    length_tier: str,
) -> List[str]:
    """Return fragments that fall within the word-count range for *length_tier*."""
    lo, hi = _LENGTH_RANGES.get(length_tier, _LENGTH_RANGES["medium"])
    return [f for f in fragments if lo <= len(f.split()) <= hi]


def _compose_plaintext(
    rng: random.Random,
    fragments: List[str],
    length_tier: str,
) -> str:
    """Select a single sentence fragment in the right length bucket.

    Falls back to any available fragment if the bucket is empty, then
    concatenates two fragments if none reach the minimum.
    """
    lo, hi = _LENGTH_RANGES.get(length_tier, _LENGTH_RANGES["medium"])
    bucketed = _bucket_fragments(fragments, length_tier)
    if bucketed:
        return rng.choice(bucketed)

    # Fallback: concatenate fragments until we hit the lower bound
    shuffled = list(fragments)
    rng.shuffle(shuffled)
    words: List[str] = []
    for frag in shuffled:
        words.extend(frag.split())
        if len(words) >= lo:
            break
    text = " ".join(words[:hi])
    if not text.endswith("."):
        text += "."
    return text


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class FancyUnicodeGenerator(TestCaseGenerator):
    """Generates fancy_unicode test cases across encoding families."""

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(
                name="count",
                label="Number of cases",
                field_type="number",
                default=30,
                min_value=5,
                max_value=200,
                help="Total number of test cases to generate",
            ),
            ConfigField(
                name="task_modes",
                label="Task modes",
                field_type="multi-select",
                default=ALL_TASK_MODES,
                options=ALL_TASK_MODES,
                help="Which task modes to include (decode_only, decode_and_act)",
            ),
            ConfigField(
                name="encoding_families",
                label="Encoding families",
                field_type="multi-select",
                default=["tier_1"],
                options=list(ALL_FAMILIES) + ["tier_1", "tier_2", "tier_3", "all"],
                help=(
                    "Unicode encoding families to use. Tier shortcuts: "
                    "tier_1 = full alphabet; tier_2 = partial coverage; "
                    "tier_3 = uppercase only + dotted"
                ),
            ),
            ConfigField(
                name="message_length",
                label="Message length (decode_only)",
                field_type="select",
                default="medium",
                options=["short", "medium", "long"],
                help="Length tier for decode_only plaintext (short 3–8, medium 8–20, long 20–40 words)",
            ),
            ConfigField(
                name="mode_weights",
                label="Mode weights",
                field_type="weight_map",
                default={m: 1.0 for m in ALL_TASK_MODES},
                weight_keys=ALL_TASK_MODES,
                group="advanced",
                help="Relative sampling weights for task modes",
            ),
        ]

    def get_default_config(self) -> Dict[str, Any]:
        return {f.name: f.default for f in self.get_config_schema()}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None,
    ) -> List[TestCase]:
        rng = random.Random(seed)

        # Config
        task_modes = config.get("task_modes", ALL_TASK_MODES)
        families_raw = config.get("encoding_families", ["tier_1"])
        if isinstance(families_raw, str):
            families_raw = [families_raw]
        families = get_family_list(families_raw)
        message_length = config.get("message_length", "medium")
        mode_weights = config.get("mode_weights", {m: 1.0 for m in ALL_TASK_MODES})

        # Prompt settings
        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", "default")
        # This plugin is EN-only
        language = safe_enum(Language, prompt_config.get("language", "en"), Language.EN).value

        # Preload word pool
        word_pool = _load_words()

        seed_label = seed if seed is not None else "noseed"
        cases: List[TestCase] = []

        for idx in range(count):
            # Pick mode and family (with retry on empty pool)
            mode = _pick_weighted(task_modes, mode_weights, rng)
            family = self._pick_valid_family(families, mode, message_length, word_pool, rng)

            task_params, plaintext = self._generate_content(
                mode, family, message_length, word_pool, rng
            )
            encoded = encode_text(plaintext, family)

            user_prompt, system_prompt, full_prompt = self._build_prompts_yaml(
                "fancy_unicode",
                "en",
                user_style,
                system_style,
                instruction=_DECODE_INSTRUCTIONS[mode].get(
                    user_style, _DECODE_INSTRUCTIONS[mode]["linguistic"]
                ),
                encoded_text=encoded,
            )

            task_params.update({
                "task_mode": mode,
                "encoding_family": family,
                "plaintext": plaintext,
                "message_length": message_length,
            })

            cases.append(TestCase(
                test_id=f"fancy_unicode_{seed_label}_{idx:04d}",
                task_type="fancy_unicode",
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
                    "language": "en",
                },
                generation_metadata={
                    "seed": seed,
                    "index": idx,
                    "task_mode": mode,
                    "encoding_family": family,
                },
            ))

        return cases

    # ------------------------------------------------------------------
    # Family selection with fallback
    # ------------------------------------------------------------------

    def _pick_valid_family(
        self,
        families: List[str],
        mode: str,
        message_length: str,
        word_pool: List[str],
        rng: random.Random,
        max_attempts: int = 20,
    ) -> str:
        """Pick a random family that has a non-empty filtered pool for *mode*."""
        shuffled = list(families)
        rng.shuffle(shuffled)
        for fam in shuffled * max(1, max_attempts // len(shuffled)):
            if mode == "decode_only":
                pool = _filter_pool(_SENTENCE_FRAGMENTS, fam)
                if pool:  # at least one fragment survives
                    return fam
            else:
                pool = _filter_words(word_pool, fam)
                if pool:
                    return fam
        _log.warning(
            "No family in %s has non-empty pool for mode=%s; defaulting to Tier 1",
            families, mode,
        )
        return TIER1_FAMILIES[0]

    # ------------------------------------------------------------------
    # Content generation per mode
    # ------------------------------------------------------------------

    def _generate_content(
        self,
        mode: str,
        family: str,
        message_length: str,
        word_pool: List[str],
        rng: random.Random,
    ) -> Tuple[Dict[str, Any], str]:
        if mode == "decode_and_act":
            return self._gen_decode_and_act(family, word_pool, rng)
        else:
            return self._gen_decode_only(family, message_length, rng)

    def _gen_decode_only(
        self,
        family: str,
        message_length: str,
        rng: random.Random,
    ) -> Tuple[Dict[str, Any], str]:
        # Filter sentence fragments by this family's coverage
        fragments = _filter_pool(_SENTENCE_FRAGMENTS, family)
        if not fragments:
            fragments = _SENTENCE_FRAGMENTS  # should not happen after _pick_valid_family

        # For uppercase-only families, fragments are uppercased during encoding
        # but the expected_answer (decoded plaintext) is the uppercased form
        plaintext = _compose_plaintext(rng, fragments, message_length)
        if family in UPPERCASE_ONLY_FAMILIES:
            plaintext = plaintext.upper()

        return (
            {"expected_answer": plaintext, "response_word": None},
            plaintext,
        )

    def _gen_decode_and_act(
        self,
        family: str,
        word_pool: List[str],
        rng: random.Random,
    ) -> Tuple[Dict[str, Any], str]:
        # Filter word pool by family coverage
        filtered_words = _filter_words(word_pool, family)
        if not filtered_words:
            filtered_words = word_pool  # fallback

        word = rng.choice(filtered_words)
        template = rng.choice(_ACT_INSTRUCTIONS)
        plaintext = template.format(word=word)

        # Uppercase-only families encode uppercase; the word response is still lowercase
        if family in UPPERCASE_ONLY_FAMILIES:
            plaintext = plaintext.upper()
            # expected_answer is the decoded response word (lowercase)
            # The model may output uppercase — evaluator normalises
            word = word.lower()

        return (
            {"expected_answer": word, "response_word": word},
            plaintext,
        )
