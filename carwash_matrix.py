#!/usr/bin/env python3
"""
carwash_matrix.py — Show which (model × config) combinations have been run for the carwash task.

Axes:
  Rows    → model name
  Columns → config key: (user_style, system_style, language)

Cell values:
  acc%   — ran, shows mean accuracy
  ·      — not run yet
"""

import gzip
import json
import glob
import os
import sys
from collections import defaultdict

# ── helpers ───────────────────────────────────────────────────────────────────

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

STYLE_ABBR = {"minimal": "min", "casual": "cas", "linguistic": "lin",
               "analytical": "ana", "adversarial": "adv"}
LANG_ORDER  = ["en", "de", "es", "fr", "uk", "zh"]
USR_ORDER   = ["minimal", "casual", "linguistic"]
SYS_ORDER   = ["analytical", "casual", "adversarial"]

# ── Model alias table ─────────────────────────────────────────────────────────
# Maps any provider-specific tag → canonical model name.
# Add new aliases here as new providers/tags appear.
MODEL_ALIASES: dict[str, str] = {
    # Gemma 3
    "gemma3:1b":                        "gemma3-1b",
    "gemma3:4b":                        "gemma3-4b",
    "gemma3:4b-cloud":                  "gemma3-4b",
    "google/gemma-3-4b-it":             "gemma3-4b",
    "gemma3:12b":                       "gemma3-12b",
    "gemma3:12b-cloud":                 "gemma3-12b",
    "google/gemma-3-12b-it":            "gemma3-12b",
    "gemma3:27b":                       "gemma3-27b",
    "gemma3:27b-cloud":                 "gemma3-27b",
    "google/gemma-3-27b-it":            "gemma3-27b",
    # Gemma 4
    "gemma4:e2b":                       "gemma4-e2b",
    "gemma4:e4b":                       "gemma4-e4b",
    "google/gemma-4-26b-a4b-it":        "gemma4-26b-a4b",
    "google/gemma-4-31b-it":            "gemma4-31b",
    # GPT-OSS
    "gpt-oss:20b-cloud":                "gpt-oss-20b",
    "openai/gpt-oss-20b":               "gpt-oss-20b",
    "gpt-oss:120b-cloud":               "gpt-oss-120b",
    "openai/gpt-oss-120b":              "gpt-oss-120b",
    # GPT-5 family (5.4 series = same models as 5 series)
    "openai/gpt-5-mini":                "gpt-5-mini",
    "openai/gpt-5.4-mini":              "gpt-5-mini",
    "openai/gpt-5-nano":                "gpt-5-nano",
    "openai/gpt-5.4-nano":              "gpt-5-nano",
    "openai/gpt-5.4":                   "gpt-5",
    # GPT-4.1
    "openai/gpt-4.1-mini":              "gpt-4.1-mini",
    "openai/gpt-4.1-nano":              "gpt-4.1-nano",
    # Qwen 3
    "qwen3:0.6b":                       "qwen3-0.6b",
    "qwen3:1.7b":                       "qwen3-1.7b",
    "qwen3:4b":                         "qwen3-4b",
    "qwen3:8b":                         "qwen3-8b",   # same model
    "qwen/qwen3-8b":                    "qwen3-8b",
    "qwen3:14b":                        "qwen3-14b",
    "qwen/qwen3-14b":                   "qwen3-14b",
    "qwen/qwen3-30b-a3b":               "qwen3-30b-a3b",
    "qwen/qwen3-30b-a3b-instruct-2507": "qwen3-30b-a3b",
    "qwen3-next:80b-cloud":             "qwen3-next-80b",
    "qwen/qwen3-next-80b-a3b-instruct": "qwen3-next-80b",
    # Qwen 3 VL
    "qwen3-vl:2b":                      "qwen3-vl-2b",
    "qwen/qwen3-vl-8b-instruct":        "qwen3-vl-8b",
    # Qwen 3.5
    "qwen3.5:0.8b":                     "qwen3.5-0.8b",
    "qwen3.5:2b":                       "qwen3.5-2b",
    "qwen3.5:9b":                       "qwen3.5-9b",
    "qwen/qwen3.5-9b":                  "qwen3.5-9b",
    "qwen/qwen3.5-27b":                 "qwen3.5-27b",
    "qwen/qwen3.5-35b-a3b":             "qwen3.5-35b-a3b",
    "qwen/qwen3.5-122b-a10b":           "qwen3.5-122b-a10b",
    # Qwen 2.5
    "qwen2.5:1.5b":                     "qwen2.5-1.5b",
    "qwen2.5:3b":                       "qwen2.5-3b",
    "qwen/qwen-2.5-72b-instruct":       "qwen2.5-72b",
    "qwen/qwen2.5-vl-72b-instruct":     "qwen2.5-vl-72b",
    # Anthropic
    "anthropic/claude-3-haiku":         "claude-3-haiku",
    "anthropic/claude-3.5-haiku":       "claude-3.5-haiku",
    "anthropic/claude-haiku-4.5":       "claude-haiku-4.5",
    "anthropic/claude-sonnet-4.5":      "claude-sonnet-4.5",
    "anthropic/claude-sonnet-4.6":      "claude-sonnet-4.6",
    # xAI Grok
    "x-ai/grok-4.1-fast":              "grok-4.1-fast",
    "x-ai/grok-4.20":                  "grok-4.20",
    "x-ai/grok-4.20-beta":             "grok-4.20-beta",
    # Moonshot Kimi
    "moonshotai/kimi-k2":               "kimi-k2",
    "moonshotai/kimi-k2.5":             "kimi-k2.5",
    # AllenAI
    "allenai/olmo-3-32b-think":         "olmo-3-32b-think",
    # Google Gemini
    "google/gemini-3.1-flash-lite-preview": "gemini-3.1-flash-lite",
    "google/gemma-2-27b-it":            "gemma2-27b",
    # Z-AI
    "z-ai/glm-4.6":                     "glm-4.6",
    "z-ai/glm-5":                       "glm-5",
    # HuggingFace SmolLM
    "HuggingFaceTB/SmolLM-135M-Instruct":  "smollm-135m",
    "HuggingFaceTB/SmolLM2-135M-Instruct": "smollm2-135m",
    "HuggingFaceTB/SmolLM2-360M-Instruct": "smollm2-360m",
}

def canonical_model(raw: str) -> str:
    """Return canonical model name, merging aliases for the same underlying model."""
    if raw in MODEL_ALIASES:
        return MODEL_ALIASES[raw]
    # Generic fallback: strip provider prefix and colon-variant suffixes
    name = raw
    for prefix in ("anthropic/", "openai/", "google/", "meta-llama/",
                   "allenai/", "x-ai/", "qwen/", "moonshotai/",
                   "z-ai/", "HuggingFaceTB/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    # ollama-style "model:tag" → "model-tag"
    name = name.replace(":", "-")
    return name

# ── scan results ─────────────────────────────────────────────────────────────

# cell_data[model][config_key] = [accuracy, ...]
cell_data: dict[str, dict[tuple, list[float]]] = defaultdict(lambda: defaultdict(list))
all_config_keys: set[tuple] = set()

for fpath in sorted(glob.glob(os.path.join(RESULTS_DIR, "results_*.json*"))):
    try:
        opener = gzip.open if fpath.endswith(".gz") else open
        with opener(fpath, "rt", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        print(f"  [skip] {os.path.basename(fpath)}: {e}", file=sys.stderr)
        continue

    raw_model = (
        data.get("model_info", {}).get("model_name")
        or data.get("metadata", {}).get("model")
        or "unknown"
    )
    model = canonical_model(raw_model)

    results = data.get("results", [])
    if len(results) != 1200:
        continue

    for r in results:
        if "carwash" not in r.get("test_id", ""):
            continue

        inp = r.get("input", {})
        pm  = inp.get("prompt_metadata", {})
        tp  = inp.get("task_params", {})

        user_style   = pm.get("user_style", "?")
        system_style = pm.get("system_style", "?")
        language     = pm.get("language", "?")

        acc = r.get("evaluation", {}).get("accuracy")
        if acc is None:
            acc = 1.0 if r.get("evaluation", {}).get("correct") else 0.0

        key = (user_style, system_style, language)
        cell_data[model][key].append(acc)
        all_config_keys.add(key)

if not cell_data:
    print("No carwash results found in", RESULTS_DIR)
    sys.exit(0)

# ── build ordered axes ────────────────────────────────────────────────────────

def key_order(k):
    u, s, l = k
    u_i = USR_ORDER.index(u)   if u in USR_ORDER   else 99
    s_i = SYS_ORDER.index(s)   if s in SYS_ORDER   else 99
    l_i = LANG_ORDER.index(l)  if l in LANG_ORDER  else 99
    return (u_i, s_i, l_i)

ordered_keys   = sorted(all_config_keys, key=key_order)
ordered_models = sorted(cell_data.keys())

# ── render helpers ────────────────────────────────────────────────────────────

def col_label(key):
    u, s, l = key
    return f"{STYLE_ABBR.get(u,u)}_{STYLE_ABBR.get(s,s)}/{l}"

MODEL_W = max(len(m) for m in ordered_models)

# ── Group by (user_style, system_style) for a cleaner multi-section display ──
from itertools import groupby

def prompt_group(k):
    return (k[0], k[1])   # (user_style, system_style)

# ── Print section-per-prompt-style ───────────────────────────────────────────

def print_table(keys, title=""):
    if not keys:
        return
    c_labels = [col_label(k) for k in keys]
    c_w = max(len(c) for c in c_labels)

    if title:
        print(f"\n{'═'*(MODEL_W + 2 + (c_w + 3)*len(keys))}")
        print(f"  {title}")
        print(f"{'═'*(MODEL_W + 2 + (c_w + 3)*len(keys))}")

    # Header
    header = f"{'Model':<{MODEL_W}} │ " + " │ ".join(f"{c:^{c_w}}" for c in c_labels)
    sep    = "─" * MODEL_W + "─┼─" + "─┼─".join("─" * c_w for _ in c_labels)
    print(header)
    print(sep)

    # Rows
    for model in ordered_models:
        cells = []
        for k in keys:
            vals = cell_data[model].get(k)
            if vals:
                pct = sum(vals) / len(vals) * 100
                cells.append(f"{pct:>{c_w-1}.0f}%")
            else:
                cells.append(f"{'·':^{c_w}}")
        print(f"{model:<{MODEL_W}} │ " + " │ ".join(cells))

    print(sep)

    # Coverage footer
    total_cells   = len(ordered_models) * len(keys)
    covered_cells = sum(
        1 for m in ordered_models for k in keys if cell_data[m].get(k)
    )
    missing = total_cells - covered_cells
    print(f"  coverage: {covered_cells}/{total_cells}  missing: {missing}")


# ── Main output ───────────────────────────────────────────────────────────────

print()
print("CARWASH BENCHMARK — (model × config) coverage matrix")
print("Cells show mean accuracy%; · = not run yet")
print()

# Group columns by (user_style, system_style)
prev_group = None
group_keys = []
for k in ordered_keys:
    g = prompt_group(k)
    if g != prev_group:
        if group_keys and prev_group:
            u, s = prev_group
            print_table(group_keys, title=f"user={u}  system={s}")
        group_keys = [k]
        prev_group = g
    else:
        group_keys.append(k)

# last group
if group_keys and prev_group:
    u, s = prev_group
    print_table(group_keys, title=f"user={u}  system={s}")

# ── Global missing list ────────────────────────────────────────────────────────
print()
print("═" * 60)
print("MISSING COMBINATIONS (model × config not yet run)")
print("═" * 60)
found_missing = False
for model in ordered_models:
    missing_keys = [k for k in ordered_keys if not cell_data[model].get(k)]
    if missing_keys:
        found_missing = True
        print(f"\n  {model}")
        for k in missing_keys:
            u, s, l = k
            print(f"    user={u:<10} sys={s:<11} lang={l}")

if not found_missing:
    print("  All combinations covered — nothing missing!")

print()
