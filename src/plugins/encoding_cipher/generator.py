"""Test-case generator for the encoding_cipher plugin.

Produces decode_only and decode_and_act test cases across
Base64, Caesar/ROT-N, and Morse code encoding schemes.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.plugins.base import ConfigField, TestCase, TestCaseGenerator
from src.plugins.parse_utils import safe_enum
from src.core.PromptEngine import Language, SystemPromptStyle

from .encoding import encode_base64, encode_caesar, encode_morse
from .prompts import TEMPLATES

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALL_TASK_MODES = ["decode_only", "decode_and_act"]
ALL_ENCODING_TYPES = ["base64", "caesar", "morse"]
ALL_CAESAR_SHIFTS = [3, 7, 13]

ENCODING_DISPLAY_NAMES = {
    "base64": "Base64",
    "caesar": "Caesar cipher",
    "morse": "Morse code",
}

# Message length buckets (word counts)
_LENGTH_RANGES = {
    "short": (3, 8),
    "medium": (8, 20),
    "long": (20, 40),
}

# ---------------------------------------------------------------------------
# Template sentence bank for decode_only plaintext generation
# ---------------------------------------------------------------------------
_SENTENCE_FRAGMENTS = [
    "The ancient lighthouse stood alone on the rocky cliff",
    "A caravan of merchants crossed the sunlit desert",
    "The clockmaker repaired the old grandfather clock carefully",
    "Dense fog rolled in from the harbour at dusk",
    "A single candle illuminated the dusty manuscript",
    "The astronomer charted a previously unknown constellation",
    "Waves crashed against the crumbling stone seawall",
    "The blacksmith forged a blade of exceptional quality",
    "A thunderstorm gathered strength over the northern mountains",
    "The cartographer drew detailed maps of the coastline",
    "An expedition set out to explore the volcanic island",
    "The librarian catalogued every manuscript in the archive",
    "Fireflies drifted lazily through the summer meadow",
    "The glassblower shaped a delicate crystal vessel",
    "A procession of lanterns wound through the narrow streets",
    "The navigator relied on the stars to find the way home",
    "Frost covered the orchard in a thin white veil",
    "The watchmaker assembled tiny gears with steady hands",
    "A falcon circled high above the open grassland",
    "The stonecutter carved an inscription into the marble slab",
]

# Instruction templates for decode_and_act mode.
# Each template embeds {word} — the model should reply with that word only.
_ACT_INSTRUCTIONS = [
    "The secret word is: {word}. Reply with only that word.",
    "Your task: respond with the single word '{word}' and nothing else.",
    "Please reply with exactly this word: {word}",
    "After decoding this message, say only the word '{word}' as your answer.",
    "Instruction: output the word '{word}' and nothing more.",
]

# Mode-specific instruction text inserted into the user prompt
_MODE_INSTRUCTIONS = {
    "en": {
        "decode_only": "Decode the following {encoding_name}-encoded message and provide the plaintext.",
        "decode_and_act": (
            "The following message is encoded in {encoding_name}. "
            "Decode it and follow the instruction inside."
        ),
    },
    "es": {
        "decode_only": "Decodifica el siguiente mensaje codificado en {encoding_name} y proporciona el texto original.",
        "decode_and_act": (
            "El siguiente mensaje está codificado en {encoding_name}. "
            "Decodifícalo y sigue la instrucción que contiene."
        ),
    },
    "fr": {
        "decode_only": "Décodez le message suivant encodé en {encoding_name} et fournissez le texte en clair.",
        "decode_and_act": (
            "Le message suivant est encodé en {encoding_name}. "
            "Décodez-le et suivez l'instruction qu'il contient."
        ),
    },
    "de": {
        "decode_only": "Dekodiere die folgende {encoding_name}-kodierte Nachricht und gib den Klartext an.",
        "decode_and_act": (
            "Die folgende Nachricht ist in {encoding_name} kodiert. "
            "Dekodiere sie und befolge die darin enthaltene Anweisung."
        ),
    },
    "zh": {
        "decode_only": "解码以下 {encoding_name} 编码的消息并提供明文。",
        "decode_and_act": (
            "以下消息使用 {encoding_name} 编码。"
            "请解码并按照其中的指示操作。"
        ),
    },
    "ua": {
        "decode_only": "Декодуйте наступне повідомлення, закодоване у {encoding_name}, та надайте відкритий текст.",
        "decode_and_act": (
            "Наступне повідомлення закодовано у {encoding_name}. "
            "Декодуйте його та виконайте інструкцію всередині."
        ),
    },
}

# ---------------------------------------------------------------------------
# Word list loader
# ---------------------------------------------------------------------------
_WORD_LIST_CACHE: Dict[str, List[str]] = {}


def _load_words(language: str = "en") -> List[str]:
    if language in _WORD_LIST_CACHE:
        return _WORD_LIST_CACHE[language]

    # Try language-specific file first, fall back to English
    words_path = _DATA_DIR / f"words_{language}.txt"
    if not words_path.exists():
        words_path = _DATA_DIR / "words_en.txt"

    words: List[str] = []
    with open(words_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.append(line.lower())

    _WORD_LIST_CACHE[language] = words
    return words


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_weighted(options: List[str], weights: Dict[str, float], rng: random.Random) -> str:
    """Weighted random selection from *options* using *weights* dict."""
    w = [weights.get(o, 1.0) for o in options]
    return rng.choices(options, weights=w, k=1)[0]


def _compose_plaintext(rng: random.Random, length_tier: str) -> str:
    """Build a plaintext string for decode_only by concatenating sentence fragments."""
    lo, hi = _LENGTH_RANGES.get(length_tier, _LENGTH_RANGES["medium"])
    target_words = rng.randint(lo, hi)
    # Shuffle and concatenate fragments until we hit the target word count
    frags = list(_SENTENCE_FRAGMENTS)
    rng.shuffle(frags)
    words: List[str] = []
    for frag in frags:
        words.extend(frag.split())
        if len(words) >= target_words:
            break
    text = " ".join(words[:target_words])
    # Ensure it ends with a period
    if not text.endswith("."):
        text += "."
    return text


def _encode(plaintext: str, encoding_type: str, shift: Optional[int]) -> str:
    """Encode plaintext with the selected scheme."""
    if encoding_type == "base64":
        return encode_base64(plaintext)
    elif encoding_type == "caesar":
        return encode_caesar(plaintext, shift or 13)
    elif encoding_type == "morse":
        return encode_morse(plaintext)
    raise ValueError(f"Unknown encoding type: {encoding_type}")


def _encoding_display(encoding_type: str, shift: Optional[int]) -> str:
    """Human-readable encoding name for use in prompts."""
    name = ENCODING_DISPLAY_NAMES[encoding_type]
    if encoding_type == "caesar" and shift is not None:
        name += f" (shift {shift})"
    return name


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class EncodingCipherGenerator(TestCaseGenerator):
    """Generates encoding/cipher decoding test cases."""

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(
                name="count", label="Number of cases", field_type="number",
                default=30, min_value=5, max_value=200,
                help="Total number of test cases to generate",
            ),
            ConfigField(
                name="task_modes", label="Task modes", field_type="multi-select",
                default=ALL_TASK_MODES, options=ALL_TASK_MODES,
                help="Which task modes to include (decode_only, decode_and_act)",
            ),
            ConfigField(
                name="encoding_types", label="Encoding types", field_type="multi-select",
                default=ALL_ENCODING_TYPES, options=ALL_ENCODING_TYPES,
                help="Which encoding schemes to use",
            ),
            ConfigField(
                name="caesar_shifts", label="Caesar shifts", field_type="multi-select",
                default=[3, 7, 13], options=[3, 7, 13],
                help="Shift values for Caesar cipher",
            ),
            ConfigField(
                name="message_length", label="Message length", field_type="select",
                default="medium", options=["short", "medium", "long"],
                help="Length tier for decode_only plaintext messages",
            ),
            ConfigField(
                name="mode_weights", label="Mode weights", field_type="weight_map",
                default={m: 1.0 for m in ALL_TASK_MODES},
                weight_keys=ALL_TASK_MODES, group="advanced",
                help="Relative weights for task mode selection",
            ),
            ConfigField(
                name="encoding_weights", label="Encoding weights", field_type="weight_map",
                default={e: 1.0 for e in ALL_ENCODING_TYPES},
                weight_keys=ALL_ENCODING_TYPES, group="advanced",
                help="Relative weights for encoding type selection",
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

        # Unpack config
        task_modes = config.get("task_modes", ALL_TASK_MODES)
        encoding_types = config.get("encoding_types", ALL_ENCODING_TYPES)
        caesar_shifts = config.get("caesar_shifts", ALL_CAESAR_SHIFTS)
        message_length = config.get("message_length", "medium")
        mode_weights = config.get("mode_weights", {m: 1.0 for m in ALL_TASK_MODES})
        encoding_weights = config.get("encoding_weights", {e: 1.0 for e in ALL_ENCODING_TYPES})

        # Prompt settings
        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", "default")
        language_str = prompt_config.get("language", config.get("language", "en"))
        language = safe_enum(Language, language_str, Language.EN)

        words = _load_words(language_str)

        seed_label = seed if seed is not None else "noseed"
        cases: List[TestCase] = []

        for idx in range(count):
            # Pick mode and encoding
            mode = _pick_weighted(task_modes, mode_weights, rng)
            enc_type = _pick_weighted(encoding_types, encoding_weights, rng)
            shift: Optional[int] = None
            if enc_type == "caesar":
                shift = rng.choice(caesar_shifts)

            # ROT/Morse only supported for EN and UA
            if language_str not in ("en", "ua") and enc_type in ("caesar", "morse"):
                enc_type = "base64"
                shift = None

            # Generate plaintext + expected answer
            task_params, plaintext = self._generate_content(
                mode, rng, words, message_length, shift,
            )

            # Encode
            encoded_text = _encode(plaintext, enc_type, shift)

            # Build instruction string
            enc_display = _encoding_display(enc_type, shift)
            lang_instructions = _MODE_INSTRUCTIONS.get(language_str, _MODE_INSTRUCTIONS["en"])
            instruction = lang_instructions[mode].format(encoding_name=enc_display)

            # Build prompts
            user_prompt, system_prompt, full_prompt = self._build_prompts(
                TEMPLATES, language_str, user_style, system_style,
                instruction=instruction, encoded=encoded_text,
            )

            # Populate task_params
            task_params.update({
                "task_mode": mode,
                "encoding_type": enc_type,
                "caesar_shift": shift,
                "plaintext": plaintext,
                "encoded_text": encoded_text,
                "message_length": message_length,
            })

            cases.append(TestCase(
                test_id=f"encoding_cipher_{seed_label}_{idx:04d}",
                task_type="encoding_cipher",
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
                    "language": language_str,
                },
                generation_metadata={
                    "seed": seed,
                    "index": idx,
                    "task_mode": mode,
                    "encoding_type": enc_type,
                },
            ))

        return cases

    # ------------------------------------------------------------------
    # Content generation per mode
    # ------------------------------------------------------------------

    def _generate_content(
        self,
        mode: str,
        rng: random.Random,
        words: List[str],
        message_length: str,
        shift: Optional[int],
    ) -> Tuple[Dict[str, Any], str]:
        """Return (task_params_fragment, plaintext) for the given mode."""
        if mode == "decode_and_act":
            return self._gen_decode_and_act(rng, words)
        else:
            return self._gen_decode_only(rng, message_length)

    def _gen_decode_only(
        self, rng: random.Random, message_length: str,
    ) -> Tuple[Dict[str, Any], str]:
        plaintext = _compose_plaintext(rng, message_length)
        params = {
            "expected_answer": plaintext,
            "response_word": None,
        }
        return params, plaintext

    def _gen_decode_and_act(
        self, rng: random.Random, words: List[str],
    ) -> Tuple[Dict[str, Any], str]:
        word = rng.choice(words)
        template = rng.choice(_ACT_INSTRUCTIONS)
        plaintext = template.format(word=word)
        params = {
            "expected_answer": word,
            "response_word": word,
        }
        return params, plaintext
