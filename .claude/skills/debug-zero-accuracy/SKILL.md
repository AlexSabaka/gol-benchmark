---
name: debug-zero-accuracy
description: Diagnose why a model is scoring 0% (or near-zero) on a benchmark task. Use when the user reports "model X is at 0%", "this task collapsed to zero", "my parser broke", or shares a results file with no correct answers. Walks through the standard triage order — runtime config, prompt language merging, parser strategy attribution, and the human-review feedback loop.
tools: Read, Bash, Grep, Glob, Edit
---

# Debug Zero-Accuracy Runs

A 0% (or near-zero) score on a previously working task almost always falls into one of five buckets. Triage them in order — most are fast to check.

---

## Bucket 1 — Was the run misconfigured? (fastest)

Check the actual command the user ran. Most "broken" results trace to one of these:

| Misconfiguration | Symptom | Fix |
|---|---|---|
| **Missing `--no-think`** on a structured task (GoL, Arithmetic, C14) | Model writes paragraphs of reasoning then guesses; parsed answer is intermediate value | Re-run with `--no-think` |
| **Cell markers other than `"1,0"`** for GoL/C14 | Accuracy drops 30–50% even on small grids | Re-run with `--live-dead-cell-markers "1,0"`; emoji markers are a robustness test, not a default |
| **Temperature too high** | Random-looking outputs, no consistent pattern | Drop to `--temperature 0.1` |
| **Wrong language prompt** | Model responds in language A, expected language B; parser misses entirely | Verify `--prompt-language` matches the testset's intended language |
| **Ollama daemon down** | All `response: ""` in the result file | `ollama serve` in another shell |

Look at the result file directly:

```bash
zcat results/<file>.json.gz | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data['results'] if isinstance(data, dict) else data
print(f'total: {len(results)}')
print(f'empty responses: {sum(1 for r in results if not r.get(\"output\", {}).get(\"response\"))}')
print(f'sample response (first non-empty):')
for r in results:
    if r.get('output', {}).get('response'):
        print(repr(r['output']['response'])[:300])
        break
"
```

If the responses look reasonable but the parsed answer is wrong/empty, move to Bucket 2.

---

## Bucket 2 — Did `prompt_metadata` get merged into `task_params`?

This is CLAUDE.md invariant #3 and the single most common cross-language regression. The parser uses `task_params['language']` to pick its keyword set — if that key isn't present, it defaults to English. A French/Spanish/Ukrainian response then fails to match.

```bash
# Check that task_params actually carries language for a result entry
zcat results/<file>.json.gz | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data['results'] if isinstance(data, dict) else data
for r in results[:3]:
    print('language present in task_params:', 'language' in r.get('task_params', {}))
    print('  prompt_metadata:', r.get('input', {}).get('prompt_metadata'))
    print('  task_params:', r.get('task_params'))
    print()
"
```

If `language` is missing from `task_params` but present in `input.prompt_metadata`, the merge step was skipped. Look at:

- [src/stages/run_testset.py](../../../src/stages/run_testset.py) — should merge before parsing
- [src/web/jobs.py](../../../src/web/jobs.py) — should merge before parsing
- [src/web/reanalyze.py](../../../src/web/reanalyze.py) — same merge logic

If the user ran reanalysis after upgrading from a pre-v2.16.1 version where reanalyze didn't merge, the fix is to re-run reanalysis on the current code.

---

## Bucket 3 — What does the parser say it's doing?

Every parsed answer carries `parse_strategy`. Aggregate them:

```bash
zcat results/<file>.json.gz | python3 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
results = data['results'] if isinstance(data, dict) else data
strategies = Counter(r.get('parsed', {}).get('parse_strategy') for r in results)
correct_by_strategy = Counter()
for r in results:
    if r.get('evaluation', {}).get('correct'):
        correct_by_strategy[r.get('parsed', {}).get('parse_strategy')] += 1
print('strategy → total / correct')
for strat, total in strategies.most_common():
    print(f'  {strat:25s} {total:5d} / {correct_by_strategy[strat]:5d}')
"
```

Read this carefully:

- **Mostly `empty`** — the model returned no output. Bucket 1 (Ollama down, model load failed, OOM).
- **Mostly `fallback`** — the parser ran every strategy and found nothing. Either the model output format changed, or the parser's expected patterns are missing a case. Read 5–10 raw responses to spot the new pattern.
- **One strategy fires often but never correct** — the strategy is matching the wrong region. Classic case: end-first regex hits a verification-tail value. Check whether the parser applies `strip_verification_tail()` on this strategy.
- **Spread across many strategies, mostly wrong** — the model is producing answers in a NEW format the parser doesn't know. Move to Bucket 5 (annotation feedback loop).

---

## Bucket 4 — Did a recent parser change regress?

Check git log on the parser file:

```bash
git log --oneline -10 -- src/plugins/<task>/parser.py
```

If a recent commit touched the parser, diff against the previous version and look for:

- **Strategy ordering changes** — high-confidence strategies (`boxed`, `bold`, `label_line`) should run BEFORE low-confidence ones (`pattern_scan`, `last_number`).
- **`strip_verification_tail` applied to a high-confidence strategy** — that helper should ONLY run on weaker strategies. Stripping the tail on a `bold` strategy can delete legitimate `**Answer:**` trailers.
- **`re_search` instead of `re_search_last`** — silent regression of CLAUDE.md invariant #2.
- **Missing `normalize_unicode` at parse entry** — smart quotes / primes will not match ASCII patterns.

Run the cross-plugin tests:

```bash
pytest tests/test_parser_end_first.py -v
pytest tests/plugins/test_<task>.py -v
```

If both pass but live results are still wrong, the parser's test coverage is missing the failing pattern — that's Bucket 5.

---

## Bucket 5 — Use the human-review feedback loop

When the parser is genuinely wrong-format on real responses, the next step is the annotation workflow described in [docs/HUMAN_REVIEW_GUIDE.md](../../../docs/HUMAN_REVIEW_GUIDE.md):

1. Open the Web UI: `python -m src.web` → `/review`.
2. Filter to the failing result file.
3. Annotate 30–100 cases with the v4 mark types (Answer span / Context anchor / Answer keyword / Negative span).
4. Generate the Improvement Report (`POST /api/human-review/report`).
5. Hand the JSON to the `parser-refactor-from-annotations` skill, which walks through identifying failure modes and implementing scoped fixes.

Even 30 annotated cases give the Improvement Report enough signal to surface the most common parser miss. Don't aim for full coverage on the first pass — annotate the most-failing language first, find one failure mode, fix it, re-run, repeat.

---

## When 0% is the EXPECTED answer

Two cases where 0% is correct and the parser is fine:

- **Carwash with a model that always recommends walking** — the test answer is always "drive"; a model that always says "walk" is correctly scored 0% on every case. The fix is "use a better model," not "fix the parser."
- **Adversarial system prompt + small model on hard difficulty** — some configurations genuinely break models. The accuracy ceiling on Linda Fallacy with `--system-prompt-style adversarial` on a 0.6B model is near zero by design.

Before changing parser code, check whether the same model on the same testset with a different prompt style is also at 0%. If yes, the model is the bottleneck, not the parser.

---

## Quick reference — common pitfalls

```
# This produces 0% reliably:
--prompt-language uk --temperature 0.7 --no-no-think     # cof, the negation is wrong

# Should be:
--prompt-language uk --temperature 0.1 --no-think
```

```
# Reanalysis without merging prompt_metadata:
old: parser.parse(response, task_params)              # task_params lacks language → English keywords
new: parser.parse(response, {**prompt_metadata, **task_params})
```

```
# Strategy attribution sanity:
parsed.parse_strategy == "fallback" everywhere   →  parser is missing a case (Bucket 5)
parsed.parse_strategy == "empty" everywhere      →  upstream is broken (Bucket 1)
parsed.parse_strategy varies but evaluation is 0 →  evaluator mismatch (check expected_answer_localized for multilingual)
```
