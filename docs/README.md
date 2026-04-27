# GoL Benchmark Documentation

**Version 2.26.0** | Last updated: 2026-04-27

Documentation for the GoL Benchmark Suite — a procedural benchmark for testing LLM reasoning across **21 structured cognitive tasks**.

> Plugin counts shift as new tasks land. The canonical enumeration is `PluginRegistry.list_task_types()` ([src/plugins/__init__.py](../src/plugins/__init__.py)) — every doc count below is a snapshot of that, not a separate source of truth.

---

## Documentation map

The set is **flat** — every doc lives at `docs/<NAME>.md`. Pick where to start by what you're doing:

| If you're… | Read |
|---|---|
| **New to the project** — orient yourself | [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) |
| **Adding a benchmark plugin** or **fixing a parser** | [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) |
| **Working on the React SPA** | [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) |
| **Annotating responses** or **building from the Improvement Report** | [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md) |
| **Wiring a new model provider** | [MODEL_PROVIDERS.md](MODEL_PROVIDERS.md) |
| **Editing or creating versioned system prompts** | [PROMPT_STUDIO.md](PROMPT_STUDIO.md) |
| **Looking up the four built-in system-prompt texts** | [SYSTEM_PROMPTS.md](SYSTEM_PROMPTS.md) |
| **Cutting a release** | [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) |

External SSOT docs:

| Doc | Owns |
|---|---|
| [`../CHANGELOG.md`](../CHANGELOG.md) | Per-release "what changed" history |
| [`../TECHDEBT.md`](../TECHDEBT.md) | Incomplete refactors and postponed decisions |
| [`../.claude/CLAUDE.md`](../.claude/CLAUDE.md) | Agent index — slim pointers, always loaded |

---

## Benchmark Tasks (21 plugins)

| Task | Plugin | Answer Type |
|---|---|---|
| Conway's Game of Life | `game_of_life` | 2D grid |
| Arithmetic Expressions | `arithmetic` | Number |
| Linda Conjunction Fallacy | `linda_fallacy` | Probability ranking |
| 1D Cellular Automata | `cellular_automata_1d` | 1D binary array |
| ASCII Shapes | `ascii_shapes` | Dimensions / count / boolean |
| Object Tracking (Grape Test) | `object_tracking` | Location name |
| Sally-Anne (Theory of Mind) | `sally_anne` | Container name |
| Carwash Paradox | `carwash` | Always "drive" |
| Inverted Cup | `inverted_cup` | "flip" |
| Strawberry (Character Reasoning) | `strawberry` | Integer / String / Boolean |
| Measure Comparison | `measure_comparison` | Measurement / "equal" / "incomparable" / decimal framing |
| Grid Tasks (Table Reasoning) | `grid_tasks` | Varies |
| Time Arithmetic | `time_arithmetic` | Time / Day / Duration / "impossible" |
| Misquote Attribution | `misquote` | Yes/No (two-part) |
| False Premise | `false_premise` | Refusal / Compliance / Hedge |
| Family Relations | `family_relations` | Integer (person count) |
| Encoding & Cipher Decoding | `encoding_cipher` | Decoded text / response word |
| Symbol Arithmetic | `symbol_arithmetic` | Symbol from operation table |
| Picross (Nonogram) | `picross` | 2D binary grid |
| Fancy Unicode | `fancy_unicode` | Normalized text |
| Picture Algebra | `picture_algebra` | Integer (system-of-equations solution) |

See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for per-plugin documentation.

> **In-flight plugins** not in the table: `mathbot` (K1–K12 word problems, currently uncommitted) and `crossword_puzzle` (empty stub). Update this table when they ship — see [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

---

## Directory layout

```
docs/
├── README.md              # This file (index)
├── PROJECT_OVERVIEW.md    # Mission, architecture, design principles
├── PLUGIN_GUIDE.md        # Plugin system + end-first parsing convention
├── HUMAN_REVIEW_GUIDE.md  # Annotation workflow + Improvement Report
├── FRONTEND_GUIDE.md      # React SPA conventions
├── MODEL_PROVIDERS.md     # Ollama / HuggingFace / OpenAI-compatible
├── PROMPT_STUDIO.md       # Versioned system prompts (v2.13+)
├── SYSTEM_PROMPTS.md      # Frozen reference for the four built-in prompts
├── RELEASE_CHECKLIST.md   # Pre-release sync checklist
└── _archive/              # Superseded historical documents
```

The set was flattened in v2.26: previous `architecture/` and `prompt-engine/` subdirectories collapsed into the root, and the old `research/` + `images/` trees were retired (their content lived in `_archive/` or was never load-bearing).

---

## What lives where (cross-doc topic map)

Some topics span multiple docs. The **authoritative** doc for each is:

| Topic | Authoritative source | Cross-references |
|---|---|---|
| End-first parsing convention + Phase 1–8 alignment | [PLUGIN_GUIDE.md § End-First Parsing Convention](PLUGIN_GUIDE.md#end-first-parsing-convention) | [src/plugins/CLAUDE.md](../src/plugins/CLAUDE.md) (slim agent reminder) |
| Annotation v4 mark types + Improvement Report v2.7 schema | [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md) | [.claude/CLAUDE.md](../.claude/CLAUDE.md) invariants #5–6 |
| Prompt Studio (versioned system prompts) | [PROMPT_STUDIO.md](PROMPT_STUDIO.md) | [SYSTEM_PROMPTS.md](SYSTEM_PROMPTS.md) (legacy enum), [PROJECT_OVERVIEW.md § Prompt Engineering System](PROJECT_OVERVIEW.md#prompt-engineering-system) |
| React Query staleTime / invalidation conventions | [FRONTEND_GUIDE.md § React Query conventions](FRONTEND_GUIDE.md#react-query-conventions) | [frontend/CLAUDE.md](../frontend/CLAUDE.md), [`frontend-react-query-recipes` skill](../.claude/skills/frontend-react-query-recipes/SKILL.md) |
| Tailwind v4 design tokens (`@theme` in `index.css`, no config file) | [FRONTEND_GUIDE.md § Design tokens](FRONTEND_GUIDE.md#design-tokens-tailwind-v4) | [`frontend-design-tokens` skill](../.claude/skills/frontend-design-tokens/SKILL.md) |
| Three-place page-add workflow (page file + App.tsx + NAV_ITEMS) | [FRONTEND_GUIDE.md § Adding a new page](FRONTEND_GUIDE.md#adding-a-new-page) | [`add-frontend-page` skill](../.claude/skills/add-frontend-page/SKILL.md) + hook H3 |
| Backend ↔ frontend type sync (no codegen) | [FRONTEND_GUIDE.md § Backend ↔ frontend type sync](FRONTEND_GUIDE.md#backend--frontend-type-sync) | [`sync-types-with-backend` skill](../.claude/skills/sync-types-with-backend/SKILL.md) + hook H4 |
| Plugin / model-provider scaffolds | [PLUGIN_GUIDE.md § Adding a New Plugin](PLUGIN_GUIDE.md#adding-a-new-plugin) | [`add-plugin` skill](../.claude/skills/add-plugin/SKILL.md), [`add-model-provider` skill](../.claude/skills/add-model-provider/SKILL.md) |

---

## Related resources

- [Main README](../README.md) — project overview and quick start
- [`.claude/skills/`](../.claude/skills/) — task-specific recipes loaded on demand
- [`.claude/hooks/`](../.claude/hooks/) — advisory PostToolUse scripts (lint, sync nudges)

---

*See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the version-bump procedure that keeps this index in sync with the codebase.*
