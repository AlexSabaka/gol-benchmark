"""Shared grammar utilities for multilingual test generation.

Handles article resolution, case-form lookup, and gender-aware template
selection for languages with grammatical gender (ES, FR, DE, UA).
"""
from __future__ import annotations
from typing import Any, Dict, List, Union


# ── Article tables ───────────────────────────────────────────────────────

_ARTICLES = {
    "es": {
        "def":   {"m": "el",  "f": "la"},
        "indef": {"m": "un",  "f": "una"},
    },
    "fr": {
        "def":   {"m": "le",  "f": "la"},
        "indef": {"m": "un",  "f": "une"},
    },
    "de": {
        # nom / acc / dat for each gender
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
}


def article(lang: str, gender: str, definite: bool = True, case: str = "nom") -> str:
    """Return the correct article for *lang*, *gender*, *case*.

    Checks the built-in ``_ARTICLES`` table first, then falls back to the
    ``LanguageSpec.articles`` entry in the language registry so new languages
    only need to be registered in ``src/plugins/languages.py``.

    >>> article("es", "f", definite=True)
    'la'
    >>> article("de", "m", definite=False, case="acc")
    'einen'
    """
    kind = "def" if definite else "indef"
    lang_arts = _ARTICLES.get(lang)
    if lang_arts is None:
        from src.plugins import languages as _langs  # late import avoids circular
        spec = _langs.get(lang)
        if spec is None or spec.articles is None:
            return ""
        lang_arts = spec.articles
    art = lang_arts.get(kind, {})
    entry = art.get(gender, art.get("m"))
    if entry is None:
        return ""
    if isinstance(entry, dict):
        return entry.get(case, entry.get("nom", ""))
    return entry


# ── Template selection ───────────────────────────────────────────────────

TemplateDict = Dict[str, Any]  # lang -> list | {gender -> list}


def pick_templates(template_dict: TemplateDict, lang: str, gender: str = "m") -> list:
    """Select templates for *lang*, resolving gender sub-dicts if present."""
    lang_data = template_dict.get(lang, template_dict.get("en", []))
    if isinstance(lang_data, dict) and gender in lang_data:
        return lang_data[gender]
    if isinstance(lang_data, list):
        return lang_data
    # Fallback: try English
    return template_dict.get("en", [])


# ── Vocabulary resolution ────────────────────────────────────────────────

VocabDict = Dict[str, Dict[str, Any]]  # lang -> {en_key -> str | {nom/acc/...}}


def resolve_vocab(en_key: str, vocab_dict: VocabDict, lang: str, case: str = "nom") -> str:
    """Look up a localized word, with case form if available.

    Vocabulary entries can be:
    - str: plain word (no case system)
    - dict with "word" key: ``{"word": "uva", "gender": "f"}``
    - dict with case keys: ``{"nom": "виноградина", "acc": "виноградину", ...}``
    """
    lang_vocab = vocab_dict.get(lang, vocab_dict.get("en", {}))
    entry = lang_vocab.get(en_key, en_key)
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        # Try requested case, then "nom", then "word", then en_key
        return entry.get(case, entry.get("nom", entry.get("word", en_key)))
    return str(entry)


def vocab_gender(en_key: str, vocab_dict: VocabDict, lang: str) -> str:
    """Return the grammatical gender of a vocabulary entry ('m', 'f', or 'n')."""
    lang_vocab = vocab_dict.get(lang, vocab_dict.get("en", {}))
    entry = lang_vocab.get(en_key, {})
    if isinstance(entry, dict):
        return entry.get("gender", "m")
    return "m"
