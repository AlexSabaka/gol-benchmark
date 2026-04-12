"""YAML loader for the declarative i18n system.

All public functions are cached with ``@lru_cache`` for performance.
Call ``invalidate_cache()`` to force reload (e.g. after editing via the
visual tool).
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

_log = logging.getLogger(__name__)
_I18N_DIR = Path(__file__).resolve().parent
_PLUGINS_DIR = _I18N_DIR.parent


# ---------------------------------------------------------------------------
# Core loading helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file, returning ``None`` on error."""
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Shared style wrappers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_styles() -> Dict[str, Dict[str, str]]:
    """Load shared style wrappers from ``styles.yaml``.

    Returns ``{style: {lang: template_with_{body}_placeholder}}``.
    """
    data = _load_yaml(_I18N_DIR / "styles.yaml")
    if data is None:
        _log.warning("styles.yaml not found — style composition unavailable")
        return {}
    return data


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_system_prompts() -> Dict[str, Dict[str, str]]:
    """Load system prompt translations from ``system_prompts.yaml``.

    Returns ``{lang: {style: prompt_text}}``.
    """
    data = _load_yaml(_I18N_DIR / "system_prompts.yaml")
    if data is None:
        return {}
    return data


# ---------------------------------------------------------------------------
# Per-language definitions
# ---------------------------------------------------------------------------

@lru_cache(maxsize=32)
def load_language(code: str) -> Optional[Dict[str, Any]]:
    """Load a language definition YAML.

    Returns the full dict (code, name, grammar, parse, system_prompts)
    or ``None`` if the file does not exist.
    """
    return _load_yaml(_I18N_DIR / "languages" / f"{code}.yaml")


def list_language_files() -> List[str]:
    """Return language codes for which YAML files exist."""
    lang_dir = _I18N_DIR / "languages"
    if not lang_dir.is_dir():
        return []
    return sorted(p.stem for p in lang_dir.glob("*.yaml"))


# ---------------------------------------------------------------------------
# Per-plugin i18n
# ---------------------------------------------------------------------------

@lru_cache(maxsize=64)
def load_plugin_i18n(plugin_name: str) -> Optional[Dict[str, Any]]:
    """Load a plugin's ``i18n.yaml``.

    Searches ``src/plugins/<plugin_name>/i18n.yaml``.
    Returns ``None`` if the file does not exist.
    """
    return _load_yaml(_PLUGINS_DIR / plugin_name / "i18n.yaml")


# ---------------------------------------------------------------------------
# Prompt composition
# ---------------------------------------------------------------------------

def compose_user_prompt(
    plugin_name: str,
    language: str,
    style: str,
    **variables: Any,
) -> str:
    """Build a user prompt by composing a shared style wrapper with a plugin body.

    Resolution order:
      1. Check plugin ``overrides.<style>.<language>`` — full override, skip wrapper
      2. Check plugin ``body.<language>`` — compose with shared wrapper
      3. Check plugin ``templates.<language>.<style>`` — legacy full-template mode
      4. Fall back to English for any missing language key

    Returns the rendered prompt string.

    Raises ``ValueError`` if no template source is found at all.
    """
    i18n = load_plugin_i18n(plugin_name)
    if i18n is None:
        raise ValueError(
            f"No i18n.yaml found for plugin {plugin_name!r}. "
            f"Expected at src/plugins/{plugin_name}/i18n.yaml"
        )

    # --- 1. Check for style override ---
    overrides = i18n.get("overrides", {})
    if style in overrides:
        style_overrides = overrides[style]
        template = style_overrides.get(language) or style_overrides.get("en")
        if template:
            return template.format(**variables).strip()

    # --- 2. Body + shared wrapper ---
    if "body" in i18n:
        bodies = i18n["body"]
        body_template = bodies.get(language) or bodies.get("en", "")
        body_rendered = body_template.format(**variables)

        styles = load_styles()
        style_wrappers = styles.get(style, styles.get("casual", {}))
        wrapper = style_wrappers.get(language) or style_wrappers.get("en", "{body}")
        return wrapper.format(body=body_rendered).strip()

    # --- 3. Full templates (legacy-compatible) ---
    if "templates" in i18n:
        templates = i18n["templates"]
        lang_templates = templates.get(language) or templates.get("en", {})
        template = lang_templates.get(style) or lang_templates.get("casual", "")
        return template.format(**variables).strip()

    raise ValueError(
        f"i18n.yaml for {plugin_name!r} has no 'body', 'overrides', or 'templates' key"
    )


# ---------------------------------------------------------------------------
# Vocabulary loading
# ---------------------------------------------------------------------------

def load_vocab(plugin_name: str) -> Dict[str, Any]:
    """Load the ``vocab`` section from a plugin's i18n.yaml.

    Returns an empty dict if no vocab section exists.
    """
    i18n = load_plugin_i18n(plugin_name)
    if i18n is None:
        return {}
    return i18n.get("vocab", {})


# ---------------------------------------------------------------------------
# Ordinal formatting from language YAML
# ---------------------------------------------------------------------------

def build_ordinal_fn(lang_data: Dict[str, Any]) -> Optional[Callable[[int], str]]:
    """Build an ordinal formatter from a language definition's ``grammar.ordinal``.

    Supports:
      - Simple format string: ``"{n}."`` → ``lambda n: f"{n}."``
      - Dict with specials: ``{default: "{n}e", special: {1: "1er"}}``

    Returns ``None`` if no ordinal config is present.
    """
    grammar = lang_data.get("grammar", {})
    ordinal = grammar.get("ordinal")
    if ordinal is None:
        return None

    if isinstance(ordinal, str):
        fmt = ordinal
        return lambda n, _fmt=fmt: _fmt.replace("{n}", str(n))

    if isinstance(ordinal, dict):
        default = ordinal.get("default", "{n}.")
        specials = {int(k): v for k, v in ordinal.get("special", {}).items()}
        def _ordinal(n: int) -> str:
            if n in specials:
                return specials[n]
            return default.replace("{n}", str(n))
        return _ordinal

    return None


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def invalidate_cache() -> None:
    """Clear all cached YAML data (call after editing YAML files)."""
    load_styles.cache_clear()
    load_system_prompts.cache_clear()
    load_language.cache_clear()
    load_plugin_i18n.cache_clear()
