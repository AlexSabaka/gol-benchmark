#!/usr/bin/env python3

import gzip
import json
import glob
import os
import sys
from collections import defaultdict

# ── helpers ───────────────────────────────────────────────────────────────────

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

# ── scan results ─────────────────────────────────────────────────────────────

unique_prompts = set()

for fpath in sorted(glob.glob(os.path.join(RESULTS_DIR, "results_*.json*"))):
    try:
        opener = gzip.open if fpath.endswith(".gz") else open
        with opener(fpath, "rt", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        print(f"  [skip] {os.path.basename(fpath)}: {e}", file=sys.stderr)
        continue

    results = data.get("results", [])
    if len(results) != 1200:
        continue

    for r in results:
        if "carwash" not in r.get("test_id", ""):
            continue
        
        inp = r.get("input", {})
        up  = inp.get("user_prompt", "")
        us  = inp.get("prompt_metadata", {}).get("user_style", "?")

        language     = inp.get("prompt_metadata", {}).get("language", "?")
        if language != "zh":
            continue

        unique_prompts.add((us, up))

# ── report unique prompts (csv) ─────────────────────────────────────────────────
print(f"Unique user prompts for Chinese CarWash tests: {len(unique_prompts)}")
print()
print("user_style,user_prompt")
for us, up in sorted(unique_prompts):
    print(f"{us},\"{up.replace('\n', '\\n')}\"")
