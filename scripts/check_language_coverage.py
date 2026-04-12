#!/usr/bin/env python3
"""
check_language_coverage.py — Language translation coverage report.

Usage:
    python scripts/check_language_coverage.py --lang pl
    python scripts/check_language_coverage.py --lang pl --require-full

Exit codes:
    0 — all infrastructure items present (and full coverage if --require-full)
    1 — infrastructure missing or --require-full with gaps

Examples:
    # Check readiness for adding Polish
    python scripts/check_language_coverage.py --lang pl

    # Verify existing Ukrainian coverage hasn't regressed
    python scripts/check_language_coverage.py --lang ua --require-full
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

# Ensure project root is on path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OK = "[✓]"
MISSING = "[✗]"
PARTIAL = "[~]"


def _check(condition: bool) -> str:
    return OK if condition else MISSING


def _import_mod(dotted: str):
    try:
        return importlib.import_module(dotted)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Infrastructure checks
# ---------------------------------------------------------------------------

def check_infrastructure(lang: str) -> tuple[list[tuple[str, bool]], bool]:
    """Return (items, all_ok)."""
    items: list[tuple[str, bool]] = []

    # 1. LanguageSpec registered
    from src.plugins import languages
    spec = languages.get(lang)
    items.append(("LanguageSpec registered in src/plugins/languages.py", spec is not None))

    # 2. Language enum entry
    from src.core.PromptEngine import Language
    has_enum = any(m.value == lang for m in Language)
    items.append((f"Language enum entry in src/core/PromptEngine.py", has_enum))

    # 3. System prompts
    from src.core.PROMPT_STYLES import SYSTEM_PROMPTS
    has_sys = lang in SYSTEM_PROMPTS
    items.append(("System prompts in src/core/PROMPT_STYLES.py", has_sys))

    # 4. parse_utils dicts
    from src.plugins.parse_utils import WORD_TO_INT, ANSWER_LABELS, YES_WORDS, NO_WORDS
    has_parse = all(
        lang in d or (spec is not None and bool(getattr(spec, attr, None)))
        for d, attr in [
            (WORD_TO_INT, "word_to_int"),
            (ANSWER_LABELS, "answer_labels"),
            (YES_WORDS, "yes_words"),
            (NO_WORDS, "no_words"),
        ]
    )
    items.append(("parse_utils vocab (word_to_int, answer_labels, yes/no words)", has_parse))

    # 5. Article tables (only relevant for gendered languages — not en, zh, ua)
    _no_articles_langs = {"en", "zh", "ua"}  # languages without definite/indefinite articles
    na = lang in _no_articles_langs
    has_articles = na or (spec is not None and spec.articles is not None)
    label = "Article tables in LanguageSpec.articles" + (" (N/A — no articles in this language)" if na else "")
    items.append((label, has_articles))

    all_ok = all(ok for _, ok in items)
    return items, all_ok


# ---------------------------------------------------------------------------
# Plugin prompts.py coverage
# ---------------------------------------------------------------------------

def check_plugin_prompts(lang: str) -> list[tuple[str, str]]:
    """Return list of (plugin_name, status) where status is 'full'/'missing'.

    Checks both YAML (``i18n.yaml``) and Python (``prompts.py``) sources.
    A plugin is 'full' if the language appears in either source.
    """
    from src.plugins import PluginRegistry

    results = []
    plugin_names = sorted(p["task_type"] for p in PluginRegistry.list_plugins())
    for name in plugin_names:
        plugin = PluginRegistry.get(name)
        if plugin is None:
            continue

        has_lang = False

        # Check YAML i18n.yaml first
        yaml_path = _ROOT / "src" / "plugins" / name / "i18n.yaml"
        if yaml_path.is_file():
            try:
                import yaml
                with open(yaml_path) as f:
                    data = yaml.safe_load(f)
                if data:
                    # Check body, templates, or overrides for the language
                    for key in ("body", "templates"):
                        section = data.get(key, {})
                        if lang in section:
                            has_lang = True
                            break
            except Exception:
                pass

        # Fall back to Python prompts.py
        if not has_lang:
            mod_path = f"src.plugins.{name}.prompts"
            mod = _import_mod(mod_path)
            if mod is None:
                results.append((name, "no_prompts" if not yaml_path.is_file() else "missing"))
                continue

            templates = getattr(mod, "USER_PROMPT_TEMPLATES", None) or getattr(mod, "TEMPLATES", None)
            if templates is None:
                for attr_name in dir(mod):
                    if attr_name.startswith("_"):
                        continue
                    val = getattr(mod, attr_name)
                    if isinstance(val, dict) and "en" in val:
                        templates = val
                        break

            if templates is not None:
                has_lang = lang in templates

        results.append((name, "full" if has_lang else "missing"))

    return results


# ---------------------------------------------------------------------------
# i18n file coverage
# ---------------------------------------------------------------------------

_I18N_FILES = [
    ("family_relations", "src/plugins/family_relations/i18n.py", ["RELATIONSHIP_LABELS", "NAMES", "PRONOUNS"]),
    ("false_premise", "src/plugins/false_premise/i18n.py", ["CHEM_QUESTION_TEMPLATES"]),
    ("linda_fallacy", "src/plugins/linda_fallacy/i18n.py", []),
    ("object_tracking", "src/plugins/object_tracking/step_i18n.py", ["OBJECTS", "CONTAINERS"]),
    ("sally_anne", "src/plugins/sally_anne/scenario_i18n.py", ["NARRATIVE_TEMPLATES"]),
    ("grid_tasks", "src/plugins/grid_tasks/data/grid_i18n.py", ["HEADERS"]),
]


def check_i18n(lang: str) -> list[tuple[str, str, str]]:
    """Return list of (plugin, file, status)."""
    results = []
    for plugin, rel_path, key_names in _I18N_FILES:
        path = _ROOT / rel_path
        if not path.exists():
            results.append((plugin, rel_path, "file_missing"))
            continue
        mod_name = rel_path.replace("/", ".").removesuffix(".py")
        mod = _import_mod(mod_name)
        if mod is None:
            results.append((plugin, rel_path, "import_error"))
            continue

        has_lang = False
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            val = getattr(mod, attr_name)
            if isinstance(val, dict) and lang in val:
                has_lang = True
                break

        if key_names:
            checked_keys = []
            for k in key_names:
                val = getattr(mod, k, None)
                if isinstance(val, dict):
                    checked_keys.append(lang in val)
            has_lang = any(checked_keys) if checked_keys else has_lang

        results.append((plugin, Path(rel_path).name, "full" if has_lang else "missing"))
    return results


# ---------------------------------------------------------------------------
# Data file coverage
# ---------------------------------------------------------------------------

_DATA_FILE_PATTERNS = [
    ("strawberry", "src/plugins/strawberry/data", ["words_{}.txt", "pangrams_{}.txt", "lipograms_{}.txt", "anagram_pairs_{}.txt"]),
    ("encoding_cipher", "src/plugins/encoding_cipher/data", ["words_{}.txt"]),
]


def check_data_files(lang: str) -> list[tuple[str, str, bool]]:
    """Return list of (plugin, filename, exists)."""
    results = []
    for plugin, rel_dir, patterns in _DATA_FILE_PATTERNS:
        data_dir = _ROOT / rel_dir
        for pat in patterns:
            fname = pat.format(lang)
            exists = (data_dir / fname).exists()
            results.append((plugin, fname, exists))
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Language translation coverage report")
    parser.add_argument("--lang", required=True, help="Language code to check (e.g. pl, ua, fr)")
    parser.add_argument("--require-full", action="store_true",
                        help="Exit 1 if any plugin prompts or i18n entries are missing")
    args = parser.parse_args()
    lang = args.lang

    print(f"\nLanguage coverage report for: '{lang}'\n{'=' * 50}")

    # ── Infrastructure ────────────────────────────────────────────────────
    print("\nInfrastructure:")
    infra_items, infra_ok = check_infrastructure(lang)
    for label, ok in infra_items:
        print(f"  {_check(ok)} {label}")

    # ── Plugin prompts.py ─────────────────────────────────────────────────
    print("\nPlugin prompts.py coverage:")
    prompt_results = check_plugin_prompts(lang)
    full_count = sum(1 for _, s in prompt_results if s == "full")
    total_plugins = len(prompt_results)
    print(f"  ({full_count}/{total_plugins} plugins have '{lang}' templates)\n")
    for name, status in prompt_results:
        if status == "full":
            sym = OK
        elif status in ("no_prompts_py", "no_template_dict"):
            sym = "[ ]"
        else:
            sym = MISSING
        print(f"  {sym} {name:30s}  {status}")

    # ── i18n files ────────────────────────────────────────────────────────
    print("\ni18n file coverage:")
    i18n_results = check_i18n(lang)
    i18n_full = sum(1 for _, _, s in i18n_results if s == "full")
    print(f"  ({i18n_full}/{len(i18n_results)} i18n files have '{lang}' entries)\n")
    for plugin, fname, status in i18n_results:
        sym = OK if status == "full" else MISSING
        print(f"  {sym} {plugin:25s}  {fname}  [{status}]")

    # ── Data files ────────────────────────────────────────────────────────
    print("\nData file coverage:")
    data_results = check_data_files(lang)
    data_found = sum(1 for _, _, exists in data_results if exists)
    print(f"  ({data_found}/{len(data_results)} language-specific data files present)\n")
    for plugin, fname, exists in data_results:
        sym = OK if exists else MISSING
        print(f"  {sym} {plugin:25s}  {fname}")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"Summary for '{lang}':")
    print(f"  Infrastructure:  {'OK' if infra_ok else 'INCOMPLETE'} "
          f"({sum(ok for _, ok in infra_items)}/{len(infra_items)} items)")
    print(f"  Plugin prompts:  {full_count}/{total_plugins}")
    print(f"  i18n files:      {i18n_full}/{len(i18n_results)}")
    print(f"  Data files:      {data_found}/{len(data_results)}")

    if not infra_ok:
        print("\n  ⚠ Infrastructure incomplete — language is not usable yet.")
        return 1

    if args.require_full:
        all_full = (full_count == total_plugins and i18n_full == len(i18n_results)
                    and data_found == len(data_results))
        if not all_full:
            print(f"\n  ⚠ --require-full: translation gaps detected.")
            return 1

    if full_count == total_plugins:
        print(f"\n  ✓ '{lang}' is fully supported.")
    else:
        print(f"\n  ⓘ '{lang}' infrastructure is ready; "
              f"{total_plugins - full_count} plugin(s) will fall back to English.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
