# Prompt Studio — Versioned System Prompts

**Version 2.26.0** | Last updated: 2026-04-27

System prompts are no longer enum-only — they are versioned, user-managed entities stored in SQLite. Editing a prompt creates a new immutable version (v2, v3, …) and old result files pinned to `(prompt_id, version)` keep replaying forever. Built-ins (`builtin_analytical` / `builtin_casual` / `builtin_adversarial` / `builtin_none`) are seeded from `PromptEngine.SYSTEM_PROMPTS` at first boot and may be edited the same way.

This is the authoritative reference for the Prompt Studio subsystem (introduced in v2.13). For the legacy enum surface that still resolves as a fallback, see [SYSTEM_PROMPTS.md](SYSTEM_PROMPTS.md). The historical v2.8 user-prompt migration (user templates moved from `PromptEngine.py` into `src/plugins/<task>/prompts.py`) is archived at [_archive/MIGRATION_GUIDE.md](_archive/MIGRATION_GUIDE.md); plugin-local templates are now described in [PLUGIN_GUIDE.md § Prompt Template Architecture](PLUGIN_GUIDE.md#prompt-template-architecture).

---

## Why this exists

Pre-v2.13 the system-prompt surface was a fixed enum (`SystemPromptStyle.ANALYTICAL` / `CASUAL` / `ADVERSARIAL` / `NONE`) baked into `src/core/PromptEngine.py`. To experiment with a new system prompt, a developer had to (a) edit the enum source, (b) cut a release, (c) re-run benchmarks. Old result files referenced the enum by name, so any change retroactively reinterpreted historical runs.

Prompt Studio breaks both constraints:

- **Versioned** — every edit produces a new immutable version row. `(prompt_id, version)` is a stable, durable address.
- **User-managed** — non-developer users can create, edit, and tag prompts via the `/prompts` page (frontend integration in progress — see [TD-119 / TD-120](../TECHDEBT.md)).
- **Replay-safe** — historical result files carry `(prompt_id, prompt_version)` plus the resolved prompt **text** embedded at testset-generation time. Re-runs and replays read the text directly; the store is consulted only for new testsets.

---

## Storage schema

Two tables, defined in [src/web/db_migrations/003_prompts.sql](../src/web/db_migrations/003_prompts.sql):

### `prompts` (parent metadata)

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | e.g. `builtin_analytical`, `prompt_<uuid>` for user-created |
| `name` | TEXT | Display name |
| `slug` | TEXT UNIQUE | URL-friendly identifier; collision returns 409 |
| `description` | TEXT | Free-form description |
| `is_builtin` | INTEGER | 1 for the four seeded built-ins, 0 otherwise |
| `tags` | TEXT (JSON array) | User-supplied tags for filtering |
| `archived_at` | TIMESTAMP NULL | Soft-delete; archived prompts hide from default lists but remain resolvable |
| `created_at` / `updated_at` | TIMESTAMP | Standard audit columns |

### `prompt_versions` (immutable per-version)

| Column | Type | Notes |
|---|---|---|
| `prompt_id` | TEXT | FK to `prompts.id` |
| `version` | INTEGER | Monotonic per `prompt_id`; v1 created with the prompt |
| `content_json` | TEXT (JSON object) | **Single column keyed by language code**: `{"en": "...", "es": "..."}`. Missing languages fall back to English at resolve time. |
| `parent_version` | INTEGER NULL | The version this one was edited from (lineage) |
| `change_note` | TEXT | Optional commit-message-style annotation |
| `created_at` / `updated_at` | TIMESTAMP | |

Composite PK: `(prompt_id, version)`. **Never UPDATEd, only INSERTed** — that is the immutability guarantee.

---

## `PromptStore` API surface

Defined in [src/web/prompt_store.py](../src/web/prompt_store.py). Follows the same pattern as `JobStore` and `AnnotationStore`: pure persistence, no business logic. Module-level `set_store` / `get_store` singletons are wired by the FastAPI app lifespan.

| Method | Purpose |
|---|---|
| `list_prompts(include_archived=False, tag=None)` | List prompts, optionally filtered by tag and including archived |
| `get_prompt(prompt_id)` | Fetch parent metadata |
| `list_versions(prompt_id)` | List all versions in chronological order |
| `get_version(prompt_id, version=None)` | Fetch one version; `None` returns latest |
| `resolve_text(prompt_id, version, language="en")` | Return the resolved string for a `(prompt_id, version, language)` triple. Falls back to English if `language` is missing in `content_json`. **This is the hot path used at inference time.** |
| `create_prompt(name, slug, description, content, tags=[])` | Create a new prompt + version 1 atomically. Validates that `content` includes a non-empty `"en"` key. Returns `(prompt_id, version=1)`. |
| `create_version(prompt_id, content, parent_version=None, change_note=None)` | Append a new immutable version. Increments the version counter. |
| `update_metadata(prompt_id, ...)` | Update parent fields (name, description, tags) — does NOT modify versions |
| `archive(prompt_id)` / `restore(prompt_id)` | Toggle the `archived_at` soft-delete flag |
| `seed_builtins()` | Idempotent: ensures the four built-ins exist, no-op on re-boot |

---

## REST API

Routes registered under `/api/prompts` — see [src/web/api/prompts.py](../src/web/api/prompts.py).

| Endpoint | Purpose |
|---|---|
| `GET /api/prompts` | List prompts (`?include_archived=true`, `?tag=foo`) |
| `POST /api/prompts` | Create a prompt (body: name, slug, description, content, tags). Validates `"en"` non-empty. 409 on slug collision. |
| `GET /api/prompts/{id}` | Get parent metadata. 404 on unknown ID. |
| `PATCH /api/prompts/{id}` | Update metadata only. |
| `DELETE /api/prompts/{id}` | Archive (soft-delete). |
| `POST /api/prompts/{id}/restore` | Un-archive. |
| `GET /api/prompts/{id}/versions` | List versions. |
| `POST /api/prompts/{id}/versions` | Create a new version (body: content, parent_version, change_note). |
| `GET /api/prompts/{id}/versions/{version}` | Get a specific version. |

The `/api/metadata` endpoint also surfaces a `prompts: [...]` array so the matrix wizard populates the prompt-axis multi-select without an extra round-trip.

---

## Resolution chain

In [src/plugins/base.py](../src/plugins/base.py) `_get_system_prompt`:

1. **Explicit `custom_system_prompt`** (free-text override) — highest priority.
2. **Stashed `(prompt_id, prompt_version)`** → `PromptStore.resolve_text(prompt_id, prompt_version, language)`. Falls through to (3) only when the store is unavailable (CLI / pure tests with no app context).
3. **`system_style` enum** → `PromptEngine.get_system_prompt_by_enum(...)`. Legacy fallback path.

`_stash_prompt_config` extends to also stash `prompt_id` / `prompt_version` from the prompt config dict, so all 21 plugin generators automatically pick up Prompt Studio addressing without per-plugin edits.

---

## Pipeline threading

- **`PromptConfig`** Pydantic model in [src/web/api/testsets.py](../src/web/api/testsets.py) carries optional `prompt_id` + `prompt_version`.
- **`MatrixPromptAxes`** in [src/web/api/matrix.py](../src/web/api/matrix.py) carries a `prompt_ids: List[str]` field where each entry is `"<id>"` (latest) or `"<id>@<version>"` (pinned). The populated list multiplies the cartesian product.
- **[src/stages/generate_testset.py](../src/stages/generate_testset.py)** stamps `(prompt_id, prompt_version)` onto every test case's `prompt_metadata` so analytics + replay can group by them.
- **Analytics** — [src/web/api/analysis.py](../src/web/api/analysis.py) `dimension_breakdowns` extended with `prompt_id` + `prompt_version` keys. Cases lacking the new fields (legacy / unmigrated) are silently skipped by those dimensions but still contribute to the existing `system_style` breakdown.

---

## Replay safety

The resolved system-prompt **text** stays embedded in `TestCase['prompts']['system']` at testset-generation time. Re-runs and replays read the text directly from the testset/result file, never re-resolving from the store. The store lookup matters only for **new** testsets.

Implication: editing `builtin_analytical` v1 → v2 does NOT retroactively change the meaning of any historical result file that was generated against v1. The pinned `(prompt_id, version=1)` plus the embedded text are the canonical record.

---

## Legacy result migration

[scripts/migrate_legacy_prompt_metadata.py](../scripts/migrate_legacy_prompt_metadata.py) walks `results/**/*.json.gz` and stamps `prompt_id = "builtin_<system_style>"`, `prompt_version = 1` onto entries that lack the new addressing.

- Idempotent — safe to re-run.
- Preserves the legacy `system_style` field untouched (analytics still compute the legacy breakdown alongside the new one).
- **Back up first**: `cp -R results results.bak` before running.

```bash
python scripts/migrate_legacy_prompt_metadata.py --results-dir results/
```

After migration, every result entry carries both legacy `system_style` AND the new `(prompt_id, prompt_version)` addressing, and the analysis dashboard can group by either.

---

## Frontend integration

The `/prompts` page (list / detail / multi-language editor / version history), matrix-wizard prompt-axis chip, and chart grouping dropdown all consume the API surface above. Frontend UI for the editor and version history view is in progress — see [TD-119](../TECHDEBT.md) and [TD-120](../TECHDEBT.md).

---

## What this replaces

| Pre-v2.13 | Post-v2.13 |
|---|---|
| Edit `PromptEngine.SYSTEM_PROMPTS` enum source | Create / edit a prompt in Prompt Studio |
| Cut a release to ship the change | Live from the moment the editor saves |
| Old results retroactively reinterpreted | Old results pinned to `(prompt_id, version)` — replay returns identical text |
| Per-language coverage scattered across helpers | Single `content_json` keyed by language code |
| No audit trail | `parent_version` + `change_note` + `created_at` per version |

The `PromptEngine.SYSTEM_PROMPTS` enum still exists and resolves as the fallback path (step 3 of the resolution chain) — when a CLI run, a pure test, or a legacy result file references a `system_style` without a `prompt_id`, the enum is the safety net.

---

*See also: [README.md](README.md) for the doc index, [SYSTEM_PROMPTS.md](SYSTEM_PROMPTS.md) for the legacy enum, [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for plugin-local user templates.*
