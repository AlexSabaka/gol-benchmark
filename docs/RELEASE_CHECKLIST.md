# Release Checklist

**Version 2.26.0** | Last updated: 2026-04-27

Pre-release checklist for cutting a new GoL Benchmark version. Run through this before tagging and pushing — the goal is that documentation and CLAUDE.md stop drifting between releases.

---

## Why this exists

Documentation lived 7 minor versions out of date by the time the diet was performed (v2.19 footers in v2.26 codebase). The root cause was that no single place said "when you bump the version, also update these files." This checklist is that place.

CLAUDE.md is now a slim index — most domain knowledge lives in `docs/`. That moves the staleness risk OUT of the agent's context window, but it also means the docs are now part of the release surface and have to be kept current.

---

## Pre-release sequence

### 1. Bump version sources of truth

- [ ] `src/__init__.py` — `__version__ = "X.Y.Z"`
- [ ] `frontend/package.json` — `"version": "X.Y.Z"`
- [ ] `frontend/package-lock.json` — re-sync via `cd frontend && npm install`

### 2. Bump version footers in docs

Each footer is in the format `**Version X.Y.Z** | Last updated: YYYY-MM-DD`. Update both fields:

- [ ] `docs/README.md`
- [ ] `docs/PROJECT_OVERVIEW.md`
- [ ] `docs/PLUGIN_GUIDE.md`
- [ ] `docs/HUMAN_REVIEW_GUIDE.md`
- [ ] `docs/FRONTEND_GUIDE.md`
- [ ] `docs/PROMPT_STUDIO.md`
- [ ] `docs/MODEL_PROVIDERS.md`
- [ ] `docs/SYSTEM_PROMPTS.md`
- [ ] `docs/RELEASE_CHECKLIST.md` (this file)
- [ ] `.claude/CLAUDE.md` (footer + the `*Version: X.Y.Z*` line)
- [ ] `frontend/CLAUDE.md` (sub-CLAUDE pilot — currently has no version footer; add one if you bump it)

### 3. Verify plugin-count consistency

Plugin counts drift as new tasks land. The canonical source is `PluginRegistry.list_task_types()`.

```bash
python3 -c "from src.plugins import PluginRegistry; print(len(PluginRegistry.list_task_types()))"
```

Then sanity-check every doc that names a plugin total:

```bash
grep -rE '\b(19|20|21|22|23)\s+plugins?\b' docs/ .claude/CLAUDE.md README.md
```

The grep should return only the actual current count. Files to update if mismatched:

- [ ] `docs/README.md` — header + `## Benchmark Tasks (N plugins)` heading + table
- [ ] `docs/PROJECT_OVERVIEW.md` — header (where applicable)
- [ ] `docs/PLUGIN_GUIDE.md` — header
- [ ] `.claude/CLAUDE.md` — Quick Index section (if it cites a count)
- [ ] Top-level `README.md` (if it cites a count)

### 4. Update `CHANGELOG.md`

`CHANGELOG.md` is the single source of truth for "what changed." Do NOT duplicate this content into CLAUDE.md or the doc footers.

- [ ] Add a new section for `[X.Y.Z] - YYYY-MM-DD`
- [ ] Group changes under `Added` / `Changed` / `Fixed` / `Removed` / `Deprecated`
- [ ] Reference issue / TD numbers where applicable

### 5. Update `TECHDEBT.md` (if the release resolves any TD items)

- [ ] Move resolved TD entries to a `## Resolved` section with the resolving version
- [ ] Add any new TD items uncovered during this release
- [ ] Cross-check that TD references in PLUGIN_GUIDE / HUMAN_REVIEW_GUIDE match (e.g. `TD-114` mentioned in `PLUGIN_GUIDE.md` should still exist in `TECHDEBT.md`, or both should be removed)

### 6. Verify the doc set is internally consistent

```bash
# Pointer integrity — every (path.md) link from CLAUDE.md actually resolves
for f in $(grep -oE '\(([^)]+\.md[^)]*)\)' .claude/CLAUDE.md | tr -d '()'); do
  test -e "$f" && echo "OK $f" || echo "MISSING $f"
done

# CLAUDE.md size budget
wc -l .claude/CLAUDE.md  # target: ≤ 200

# Doc freshness — no stale version footers
grep -rE 'Version[: ][0-9]+\.[0-9]+\.[0-9]+' docs/ .claude/CLAUDE.md
```

All footers should report the new version. CLAUDE.md should fit on roughly one screen.

### 7. Tests + frontend gates

Backend:
- [ ] `pytest tests/ -q` — full suite green

Frontend (full sequence — all three must pass):
- [ ] `cd frontend && npm run lint` — ESLint clean (TypeScript strict + react-hooks rules)
- [ ] `cd frontend && npm run build` — `tsc -b && vite build` produces `frontend/dist/` without errors
- [ ] `cd frontend && npm install` if `package.json` changed (re-syncs `package-lock.json`)
- [ ] If a backend Pydantic model changed this release, verify frontend types mirrored — `grep -rn "<RenamedField>" frontend/src/` should return zero hits for any old names. See [FRONTEND_GUIDE.md § Backend ↔ frontend type sync](FRONTEND_GUIDE.md#backend--frontend-type-sync) and the `sync-types-with-backend` skill.

Manual smoke-test:
- [ ] `python -m src.web` — backend serves `frontend/dist/` at `/`
- [ ] Click through every major page (Dashboard, Configure, Test Sets, Execute, Jobs, Results, Charts, Reports, Judge, Review, Prompt Studio)
- [ ] Toggle dark mode — no unreadable text or surfaces (catches missing `.dark { ... }` overrides for new design tokens; see `frontend-design-tokens` skill)

### 8. Git hygiene

- [ ] Commit doc updates separately from code changes (easier to review)
- [ ] Tag with `git tag vX.Y.Z`
- [ ] Push with `git push --follow-tags`

---

## Post-release

- [ ] Verify the GitHub release page renders the CHANGELOG section correctly
- [ ] If a new plugin landed, add a per-plugin reference section to `docs/PLUGIN_GUIDE.md` (currently #20 / #21 are stub entries — bring them to full per-plugin write-ups when time allows)
- [ ] If a new doc was added under `docs/`, add a one-line entry to `docs/README.md` index AND a one-line pointer in `.claude/CLAUDE.md`'s "Where to find" section

---

## Doc-staleness early warning

After every release, run:

```bash
# Check that no doc claims an outdated version
expected=$(python3 -c "from src import __version__; print(__version__)")
grep -rE "Version[: ]$expected" docs/ .claude/CLAUDE.md | wc -l
```

The count should equal the number of docs in the index above (currently 7). If it's lower, somebody skipped step 2. Add this to a CI check eventually — see [TD-118](../TECHDEBT.md) (placeholder; create the TD if it doesn't exist).

---

*See [README.md](README.md) for the full doc index, [CHANGELOG.md](../CHANGELOG.md) for version history, [TECHDEBT.md](../TECHDEBT.md) for outstanding refactors.*
