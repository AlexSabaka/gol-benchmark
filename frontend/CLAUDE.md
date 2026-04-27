# `frontend/` Local Agent Notes

> **Pilot file** for testing whether Claude Code's subdirectory CLAUDE.md lazy-loading works reliably. Verify with `/context`. If this file ends up loaded on every turn (eager-load), delete it and move content to `docs/FRONTEND_GUIDE.md`.
> **Note for the Coding Agent**: if you notice this file being loaded on unrelated tasks or requests — flag it to the user.

This file scopes **frontend-specific** rules that don't matter outside `frontend/`. The root [CLAUDE.md](../.claude/CLAUDE.md) carries cross-cutting invariants; this file carries frontend-internal ones.

For full reference see [docs/FRONTEND_GUIDE.md](../docs/FRONTEND_GUIDE.md). For task recipes load the relevant skill from `.claude/skills/`.

---

## Stack reminder (one-line)

React 19 + Vite 6 + Tailwind CSS v4 (`@theme` in `index.css`, **no `tailwind.config.ts`**) + shadcn/ui (new-york style, neutral base) + Radix + TanStack Query 5 + TanStack Table 8 + React Router 7. TypeScript fully strict. No form library, no test runner.

---

## Conventions every turn must respect

1. **Path alias `@/` → `frontend/src/`.** Always use it; don't write relative imports across folders.
2. **`cn(...inputs)` from [`@/lib/utils`](src/lib/utils.ts) for all class composition.** Never hand-concatenate class strings — `tailwind-merge` resolves conflicts that string concat misses.
3. **shadcn primitives are named-exported.** `import { Button } from "@/components/ui/button"`. Do not introduce default exports for primitives.
4. **TS strict + `noUnusedLocals` + `noUnusedParameters` + `noUncheckedSideEffectImports`** are on. Imports you "might use later" fail the lint hook (H2). Delete them.
5. **No form library.** Raw `useState` + `onChange`. Don't reach for react-hook-form / Zod without proposing it via TECHDEBT.
6. **No `tailwind.config.ts`.** Design tokens live in [`src/index.css`](src/index.css) `@theme { ... }` block as OKLCH variables. Never inline OKLCH in component classes — extend `@theme` so the token is theme-shiftable.

---

## Adding a new page — three places to edit (skill: `add-frontend-page`)

1. `frontend/src/pages/<route>/index.tsx` — the page component
2. `frontend/src/App.tsx` — lazy-load + add route entry
3. `frontend/src/components/layout/app-shell.tsx` — add `NAV_ITEMS` entry (no auto-discovery!)

Hook H3 prints a reminder on new page files. The skill at [`add-frontend-page`](../.claude/skills/add-frontend-page/SKILL.md) walks all three.

---

## React Query — the load-bearing rules (skill: `frontend-react-query-recipes`)

| Data shape | `staleTime` |
|---|---|
| Immutable / versioned snapshot | `Infinity` (review cases, prompt versions, plugins, metadata) |
| Slow-changing metadata | `30_000`–`60_000` |
| Expensive aggregations | `5_000` (charts) |
| Live state | `0` (default) |

**Cache invalidation is order-sensitive**:
- Exact match: `invalidateQueries({ queryKey: ["jobs", filename] })` — one entry
- **Prefix match**: `invalidateQueries({ queryKey: ["review-cases"] })` — busts ALL `["review-cases", ...]` keys regardless of trailing args. Used by `useDeleteAnnotations` (CRITICAL — multi-file sessions break without it).

**Polling**: `useJobs(true)` enables `refetchInterval: 3000`. `useJobStatus` stops polling when state hits `completed` / `failed` / `cancelled`.

**`useMetadata()` has `staleTime: Infinity`** — after Prompt Studio archive/restore mutations, MANUALLY invalidate `["metadata"]` or the picker shows stale entries.

---

## Human review workspace — gotchas

Full reference: [docs/HUMAN_REVIEW_GUIDE.md](../docs/HUMAN_REVIEW_GUIDE.md). The five frontend-specific landmines:

1. **`help-dialog.tsx` ↔ `use-review-keybindings.ts` are duplicated** with no shared constant. If you add or change a shortcut, edit BOTH. Hook H1 nudges on either edit.
2. **`use-modifier-state.ts`** clears flags on `window.blur` and `document.visibilitychange`. Don't remove these listeners — stuck-modifier bugs reappear immediately.
3. **`auto_negative_inferred` sticky flag** in `review.tsx` `DraftAnnotation`: prevents re-creation of auto-inferred negatives within a case. Reset on case advance via `emptyDraft()`.
4. **`was_truncated` auto-toggle** in `emptyDraft()`: seeds `response_classes: ["truncated"]` when the result entry has `output.was_truncated = true` AND no existing annotation. Phase 3 behavior.
5. **`caseKey()` is `result_file_id::case_id::response_hash`** (not `case_id` alone). The triplet is the active-case identifier for undo-stack reset and draft isolation. Three layers because one result file routinely has 54 entries sharing one `test_id`.

---

## Translation panel — invariant

`frontend/src/components/review/translation-panel.tsx` MUST keep `select-none`. Annotation char offsets refer to the **original** response, not the translation. If translated text is selectable, annotators can mark offsets that mean something different in the original.

---

## Prompt Studio (in flight, untracked)

Backend: [docs/PROMPT_STUDIO.md](../docs/PROMPT_STUDIO.md). Frontend: `src/api/prompts.ts`, `src/types/prompts.ts`, `src/hooks/use-prompts.ts`, `src/pages/prompts/`, `src/components/prompts/` — currently all untracked per git status.

Three things to know:
- `PromptRef = {id: string; version: number | null}` — `null` = "latest", number = pinned. Wire format: `"id"` or `"id@N"`.
- EN content is **always required** at submit; other 5 languages are optional and fall back to EN at resolve time.
- Editing always creates `v(n+1)` from latest. There is no branching off an older version.

---

## Backend ↔ frontend type sync — manual (skill: `sync-types-with-backend`)

Types in `src/types/` are hand-maintained 1:1 with Pydantic models in `src/web/`. No codegen. When backend response shapes change:

1. Mirror in `src/types/<domain>.ts`
2. Grep: `grep -r 'OldField' src/`
3. Update `src/api/<domain>.ts` if request body changed
4. Update `src/hooks/use-<domain>.ts` if return shape changed

Hook H4 nudges on `src/web/api/*.py` or `src/web/*_store.py` edits.

---

## Build / lint surface

```bash
npm run lint        # ESLint
npm run build       # tsc -b && vite build (production SPA → dist/)
npm run dev         # Vite dev server, port 5173, proxies /api → :8000
```

ESLint config at [`eslint.config.js`](eslint.config.js). One project-specific rule disabled: `react-hooks/incompatible-library` (TanStack Table returns non-memoizable functions — known incompatibility). Don't re-enable it.

Hook H2 (`eslint-frontend-on-edit`) runs ESLint advisorily on every `*.ts` / `*.tsx` edit under `src/`. Output is informational; the hook does not block writes.

---

## When to update this file

Update when:
- A new shared frontend convention emerges (e.g. a form library is finally chosen)
- A new load-bearing file lands that agents must read first
- A new "edit two files in lockstep" risk surfaces (analogous to help-dialog ↔ keybindings)

Do NOT update with:
- Per-component specifics (those live with the component)
- React-ecosystem general knowledge (Claude already knows React)
- Release notes ([CHANGELOG.md](../CHANGELOG.md))
- Incomplete refactors ([TECHDEBT.md](../TECHDEBT.md))

---

*See also: [docs/FRONTEND_GUIDE.md](../docs/FRONTEND_GUIDE.md), [.claude/CLAUDE.md](../.claude/CLAUDE.md), and the frontend skills under [.claude/skills/](../.claude/skills/).*
