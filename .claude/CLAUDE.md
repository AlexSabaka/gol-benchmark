# CLAUDE.md — GoL Benchmark Agent Index

> **Version 2.26.0** | This is a slim index. Domain knowledge lives in `docs/`; task recipes live in `.claude/skills/`. See pointers below.

GoL Benchmark is a procedural benchmark suite for testing LLM reasoning across **21 cognitive-task plugins** (canonical: `PluginRegistry.list_task_types()` in [src/plugins/__init__.py](src/plugins/__init__.py)). Multilingual (6 languages), multi-provider (Ollama / HuggingFace / OpenAI-compatible), seeded for reproducibility.

---

## Where to find things

| If you need… | Read |
|---|---|
| Project mission, design principles, CLI/difficulty reference | [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) |
| Plugin architecture, **end-first parsing convention (Phases 1–8)**, per-plugin reference, scaffold | [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md) |
| Human review workflow, annotation schema (v4), Improvement Report contract (v2.7), Known Issues #1–#10 | [docs/HUMAN_REVIEW_GUIDE.md](docs/HUMAN_REVIEW_GUIDE.md) |
| Prompt Studio (versioned system prompts, replay safety, `PromptStore`) | [docs/PROMPT_STUDIO.md](docs/PROMPT_STUDIO.md) |
| Pre-release checklist (versions, plugin counts, footers, CI) | [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) |
| Doc index, plugin enumeration table | [docs/README.md](docs/README.md) |
| Per-release "what changed" | [CHANGELOG.md](CHANGELOG.md) — single source of truth, do NOT duplicate here |
| Incomplete refactors / postponed decisions | [TECHDEBT.md](TECHDEBT.md) |
| Task recipes (load on demand) | `.claude/skills/{add-plugin,add-model-provider,debug-zero-accuracy,parser-refactor-from-annotations}` |

---

## Quick commands

```bash
# Web UI (recommended)
python -m src.web                    # http://127.0.0.1:8000/
python -m src.web --host 0.0.0.0     # LAN-accessible

# Frontend dev (hot-reload, proxies /api → :8000)
cd frontend && npm run dev           # http://localhost:5173/

# CLI 3-stage pipeline
python src/stages/generate_testset.py configs/my_config.yaml
python src/stages/run_testset.py testsets/testset_*.json.gz \
    --model qwen3:0.6b --provider ollama --no-think
python src/stages/analyze_results.py results/

# Tests
pytest tests/                        # full suite
pytest tests/plugins/ -v             # plugin-specific
```

---

## Project shape (top level)

```
src/plugins/  21 task plugins + base.py + parse_utils.py + grammar_utils.py
src/stages/   3-stage pipeline (generate → run → analyze)
src/web/      FastAPI + JobStore + PromptStore + AnnotationStore + judge
src/core/     types, PromptEngine (legacy enums)
src/models/   Ollama / HuggingFace / OpenAI-compatible interfaces
frontend/     React 19 + Vite 6 + Tailwind v4 + shadcn/ui SPA
docs/         documentation (this is where you should add reference content)
tests/        pytest suite
```

Full annotated layout: [docs/PROJECT_OVERVIEW.md § Project Layout](docs/PROJECT_OVERVIEW.md#project-layout-orientation-only).

---

## Architecture invariants

These are the rules every agent turn must respect. Detailed explanations live in the linked docs.

1. **Plugin auto-discovery** — `PluginRegistry` ([src/plugins/__init__.py](src/plugins/__init__.py)) scans `src/plugins/*/` for a module-level `plugin = PluginPlugin()` instance. **Do not maintain hardcoded plugin lists** — `_KNOWN_TASK_TYPES` in `src/stages/analyze_results.py` and `_TASK_TYPE_SUFFIXES` in `src/web/reanalyze.py` derive from the registry at import time. `_LEGACY_TASK_TYPES` is the manual exception list for removed plugins.
2. **End-first parsing** — every parser searches from the END of the response toward the start. Use `re_search_last`, not `re.search`. Shared helpers in [src/plugins/parse_utils.py](src/plugins/parse_utils.py); convention + Phase 1–8 details in [PLUGIN_GUIDE.md § End-First Parsing Convention](docs/PLUGIN_GUIDE.md#end-first-parsing-convention).
3. **`prompt_metadata` must be merged into `task_params`** before calling plugin parsers/evaluators. `run_testset.py` and `src/web/jobs.py` do this; if you add a new entry point, replicate the merge or parsers will default to English keywords on multilingual responses.
4. **Replay safety** — Prompt Studio resolves `(prompt_id, version)` at testset-generation time and embeds the resolved TEXT in `TestCase['prompts']['system']`. Re-runs read text directly from the result file; never re-resolve from the store. See [PROMPT_STUDIO.md § Replay safety](docs/PROMPT_STUDIO.md#replay-safety).
5. **Annotation sidecar key is `case_id::response_hash`** — `response_hash` is the first 16 hex chars of SHA256 over the first 128 chars of `raw_response`. A single result file routinely contains 54 entries sharing one `test_id` (6 langs × 3 user × 3 system); shorter keys overwrite. See [HUMAN_REVIEW_GUIDE.md § 2.2](docs/HUMAN_REVIEW_GUIDE.md#22-the-canonical-key).
6. **Translation panels must be `select-none`** — annotation char offsets refer to the original response, not the translation. Enforced in `frontend/src/components/review/translation-panel.tsx`. See [HUMAN_REVIEW_GUIDE.md § 2.10 #2](docs/HUMAN_REVIEW_GUIDE.md#210-known-issues--gotchas).
7. **FastAPI route ordering** — specific routes (e.g. `/judge-results`, `/reports`) must be declared BEFORE `/{filename}` catch-alls in `src/web/api/*.py`, otherwise the catch-all swallows them.
8. **Job persistence is confined to `src/web/job_store.py`** — that's the only file to touch when migrating to Redis/Postgres. Credentials Fernet-encrypted at rest under `data/jobs/` via `src/web/crypto.py`. Back up `data/.secret_key` (path: `GOL_SECRET_KEY` env override) — losing it makes existing encrypted credentials unrecoverable.
9. **Version bumps touch multiple files** — see [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md). Single SSOT: `src/__init__.py.__version__`. Doc footers and `frontend/package.json` mirror it.

---

## Top runtime gotchas (curated 8 of the historical 18)

The full Known Issues catalogue moved into the relevant doc (HUMAN_REVIEW_GUIDE § 2.10 owns annotation/report invariants; CHANGELOG owns "this was a bug fixed in vX.Y.Z"). Keep these eight in the agent's hot context:

1. **`--no-think` is critical for structured tasks** (GoL, Arithmetic, C14). Chain-of-thought hurts rule-application; pass `--no-think` for those benchmarks.
2. **Cell markers**: emoji work since v2.10.1+, but models still perform best with numeric `"1,0"`. Emoji is a robustness test, not a default.
3. **Ollama must be running** (`ollama serve`) before any benchmark.
4. **First Ollama query is slow** (~3–5 s model load). Subsequent queries are fast.
5. **Multilingual evaluators check `expected_answer_localized`** — Object Tracking and Sally-Anne store both English `expected_answer` and `expected_answer_localized` in `task_params`. A Ukrainian "тумбочці" matches localized "тумбочці" via `match_type = "localized_match"`.
6. **Long testset filenames** — `path_manager.py` truncates the task list at >120 chars and caps the total at 240, since some filesystems reject longer paths.
7. **Annotation invariant is relaxed (v2.20.0+)**: at least one of `spans` / `response_classes` must be populated — both may coexist (e.g. `false_positive` carries both the evidence span and the diagnosis class). Pre-v2.20 was `XOR`; do not regress.
8. **Translation panels must be `select-none`** (Architecture invariant #6). Repeated here because it is the easiest invariant to break by accident when adding to the review UI.

---

## Common imports

```python
# Plugins
from src.plugins import PluginRegistry, ConfigField
from src.plugins.base import (
    BenchmarkPlugin, TestCaseGenerator, ResponseParser, ResultEvaluator,
    TestCase, ParsedAnswer, EvaluationResult,
)
from src.plugins.parse_utils import (
    safe_enum, re_search_last, strip_verification_tail, normalize_unicode,
    merge_keywords, get_language, build_word_to_int, build_answer_label_re,
)
from src.plugins.grammar_utils import article, resolve_vocab, pick_templates, vocab_gender

# Core (PromptEngine system prompts + enums; user templates are deprecated → plugins)
from src.core.types import GameOfLifeTestConfig, DifficultyLevel
from src.core.PromptEngine import Language, PromptStyle, SystemPromptStyle

# Models
from src.models import create_model_interface, ModelInterface

# Web (when adding API surface — DO NOT import these from CLI code)
from src.web.prompt_store import get_store as get_prompt_store
from src.web.annotation_store import get_store as get_annotation_store
from src.web.job_store import JobStore
```

---

## Common troubleshooting

| Symptom | Likely fix |
|---|---|
| `ModuleNotFoundError: No module named 'src.types'` | Use `from src.core.types import ...` (post-reorg path) |
| `connection refused` on Ollama | `ollama serve` in another shell |
| 0% accuracy on a structured task | Check `--no-think` and `--live-dead-cell-markers "1,0"`; see `debug-zero-accuracy` skill |
| Parser returns English keywords on Ukrainian response | `prompt_metadata` not merged into `task_params` (invariant #3) |
| Annotation appears to overwrite a sibling case | Sidecar key is `case_id::response_hash`, not `case_id` (invariant #5) |
| FastAPI catch-all swallowing a specific route | Re-order route declarations (invariant #7) |

---

## Self-discipline reminders

- **CHANGELOG owns version history.** Do not paste release notes into this file.
- **TECHDEBT owns incomplete refactors.** Phase 3b grid plugins, TD-109 (label-regex consolidation), TD-112 (normalize_unicode placement), TD-113 (`strategy_breakdown.parser_ok=0` aggregator bug), TD-114 (extrapolated multilingual anchors awaiting validation), TD-115 (`negative_keywords` column cleanup), TD-118 (doc-freshness CI), TD-119 / TD-120 (Prompt Studio frontend) — all live in TECHDEBT, not here.
- **Per-plugin parser refactor narratives** belong in PLUGIN_GUIDE § End-First Parsing Convention (architectural reference) or TECHDEBT (if incomplete). Not in this index.
- **The `add-plugin`, `add-model-provider`, `debug-zero-accuracy`, and `parser-refactor-from-annotations` skills** carry the full code-template recipes. When the user asks "how do I add a new plugin?" invoke the skill rather than answering from memory.

---

*Last updated: 2026-04-27 · See [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) for the bump procedure.*
