"""Central language registry for the benchmark suite.

This is the single source of truth for supported languages and their metadata.

**Adding a new language (e.g. Polish):**
  1. Create ``src/plugins/i18n/languages/pl.yaml``  ← all metadata goes here
  2. Add ``PL = "pl"`` to the ``Language`` enum in ``src/core/PromptEngine.py``
  3. Add ``pl:`` entries to ``src/plugins/i18n/styles.yaml`` (3 lines)
  4. Add plugin translations incrementally — missing languages fall back to English

The registry auto-loads from YAML files in ``i18n/languages/``.  Hardcoded
``register()`` calls below serve as fallback if YAML files are unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class LanguageSpec:
    """Metadata for a single supported language."""

    code: str
    """ISO 639-1 code, e.g. ``"pl"``."""

    name: str
    """Human-readable name, e.g. ``"Polish"``."""

    # ── parse_utils data ──────────────────────────────────────────────────
    word_to_int: Dict[str, int] = field(default_factory=dict)
    """Map of number words to integers (e.g. ``{"jeden": 1, "dwa": 2}``)."""

    answer_labels: List[str] = field(default_factory=list)
    """Localized answer-label keywords (e.g. ``["odpowiedź", "wynik"]``)."""

    yes_words: List[str] = field(default_factory=list)
    """Localized affirmative keywords."""

    no_words: List[str] = field(default_factory=list)
    """Localized negative keywords."""

    # ── grammar_utils data ────────────────────────────────────────────────
    articles: Optional[Dict] = None
    """Article tables using the same schema as ``grammar_utils._ARTICLES``.

    Structure for simple languages (ES/FR)::

        {"def": {"m": "el", "f": "la"}, "indef": {"m": "un", "f": "una"}}

    For case-inflected languages (DE)::

        {"def": {"m": {"nom": "der", "acc": "den", ...}, ...}, ...}
    """

    ordinal_fmt: Optional[Callable[[int], str]] = None
    """Callable that formats an ordinal number (e.g. ``lambda n: f"{n}."``).

    ``None`` means use the English default in the caller.
    """


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, LanguageSpec] = {}


def register(spec: LanguageSpec) -> None:
    """Register a language spec. Called at module load for built-in languages."""
    _REGISTRY[spec.code] = spec


def get(code: str) -> Optional[LanguageSpec]:
    """Return the ``LanguageSpec`` for *code*, or ``None`` if not registered."""
    return _REGISTRY.get(code)


def all_codes() -> List[str]:
    """Return all registered language codes in registration order."""
    return list(_REGISTRY.keys())


# ---------------------------------------------------------------------------
# YAML auto-loading
# ---------------------------------------------------------------------------

def _load_from_yaml() -> bool:
    """Populate the registry from ``i18n/languages/*.yaml`` files.

    Returns ``True`` if at least one language was loaded.
    """
    try:
        from src.plugins.i18n.loader import load_language, list_language_files, build_ordinal_fn
    except ImportError:
        return False

    loaded = False
    for code in list_language_files():
        if code in _REGISTRY:
            continue  # don't overwrite already-registered specs
        data = load_language(code)
        if data is None:
            continue
        grammar = data.get("grammar", {})
        parse = data.get("parse", {})
        spec = LanguageSpec(
            code=data.get("code", code),
            name=data.get("name", code),
            word_to_int=parse.get("word_to_int", {}),
            answer_labels=parse.get("answer_labels", []),
            yes_words=parse.get("yes_words", []),
            no_words=parse.get("no_words", []),
            articles=grammar.get("articles"),
            ordinal_fmt=build_ordinal_fn(data),
        )
        register(spec)
        loaded = True
    return loaded


# ---------------------------------------------------------------------------
# Built-in language registrations (fallback if YAML unavailable)
# ---------------------------------------------------------------------------

register(LanguageSpec(
    code="en",
    name="English",
    word_to_int={
        "zero": 0, "no": 0, "none": 0,
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    },
    answer_labels=["answer", "result", "final answer", "solution", "response"],
    yes_words=["yes", "true", "correct", "right"],
    no_words=["no", "false", "incorrect", "wrong"],
))

register(LanguageSpec(
    code="es",
    name="Spanish",
    word_to_int={
        "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
        "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
        "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
        "veinte": 20,
    },
    answer_labels=["respuesta", "resultado", "respuesta final", "solución"],
    yes_words=["sí", "si", "verdadero", "correcto"],
    no_words=["no", "falso", "incorrecto"],
    articles={
        "def":   {"m": "el",  "f": "la"},
        "indef": {"m": "un",  "f": "una"},
    },
    ordinal_fmt=lambda n: f"{n}.º",
))

register(LanguageSpec(
    code="fr",
    name="French",
    word_to_int={
        "zéro": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4,
        "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
        "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
        "seize": 16, "dix-sept": 17, "dix-huit": 18, "dix-neuf": 19,
        "vingt": 20,
    },
    answer_labels=["réponse", "résultat", "réponse finale", "solution"],
    yes_words=["oui", "vrai", "correct", "exacte"],
    no_words=["non", "faux", "incorrect"],
    articles={
        "def":   {"m": "le",  "f": "la"},
        "indef": {"m": "un",  "f": "une"},
    },
    ordinal_fmt=lambda n: "1er" if n == 1 else f"{n}e",
))

register(LanguageSpec(
    code="de",
    name="German",
    word_to_int={
        "null": 0, "eins": 1, "ein": 1, "eine": 1, "zwei": 2, "drei": 3,
        "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8,
        "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13,
        "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17,
        "achtzehn": 18, "neunzehn": 19, "zwanzig": 20,
    },
    answer_labels=["antwort", "ergebnis", "endgültige antwort", "lösung"],
    yes_words=["ja", "richtig", "korrekt", "wahr"],
    no_words=["nein", "falsch", "inkorrekt", "unwahr"],
    articles={
        "def": {
            "m": {"nom": "der", "acc": "den", "dat": "dem"},
            "f": {"nom": "die", "acc": "die", "dat": "der"},
            "n": {"nom": "das", "acc": "das", "dat": "dem"},
        },
        "indef": {
            "m": {"nom": "ein", "acc": "einen", "dat": "einem"},
            "f": {"nom": "eine", "acc": "eine", "dat": "einer"},
            "n": {"nom": "ein", "acc": "ein", "dat": "einem"},
        },
    },
    ordinal_fmt=lambda n: f"{n}.",
))

register(LanguageSpec(
    code="zh",
    name="Chinese",
    word_to_int={
        "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    },
    answer_labels=["答案", "结果", "最终答案", "解答"],
    yes_words=["是", "对", "正确", "是的"],
    no_words=["不", "否", "错", "不是", "错误"],
    ordinal_fmt=lambda n: f"第{n}",
))

register(LanguageSpec(
    code="ua",
    name="Ukrainian",
    word_to_int={
        "нуль": 0, "один": 1, "одна": 1, "два": 2, "дві": 2, "три": 3,
        "чотири": 4, "п'ять": 5, "шість": 6, "сім": 7, "вісім": 8,
        "дев'ять": 9, "десять": 10, "одинадцять": 11, "дванадцять": 12,
        "тринадцять": 13, "чотирнадцять": 14, "п'ятнадцять": 15,
        "шістнадцять": 16, "сімнадцять": 17, "вісімнадцять": 18,
        "дев'ятнадцять": 19, "двадцять": 20,
    },
    answer_labels=["відповідь", "результат", "остаточна відповідь", "рішення"],
    yes_words=["так", "правда", "правильно", "вірно"],
    no_words=["ні", "неправда", "невірно", "неправильно"],
    ordinal_fmt=lambda n: f"{n}-й",
))

# Try loading additional languages from YAML (e.g. Polish)
_load_from_yaml()
