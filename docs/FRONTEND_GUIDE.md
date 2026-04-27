# Frontend Guide

**Version 2.26.0** | Last updated: 2026-04-27

Counterpart to [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for the React SPA at `frontend/`. Covers stack, conventions, the React Query data layer, design tokens, the human-review and Prompt Studio subsystems, and the build/lint surface.

The slim agent-facing pointer lives at [`frontend/CLAUDE.md`](../frontend/CLAUDE.md). The task-specific recipes (add a page, install a shadcn component, sync a backend type, etc.) live as `.claude/skills/`. **This file is the depth those two surfaces point to.**

---

## Stack & quality gates

- **Runtime**: React 19.2 + Vite 6.4 + TypeScript 5.9 + Tailwind CSS v4.2
- **UI primitives**: shadcn/ui (new-york style, neutral base, CSS variables) + Radix UI + lucide-react + cmdk + sonner
- **Data**: TanStack React Query 5.95 + TanStack React Table 8.21
- **Routing**: React Router 7.13 (`createBrowserRouter` data router, lazy pages)
- **Charts**: recharts 3.8 + d3-regression
- **Misc**: html-to-image, clsx, tailwind-merge, class-variance-authority

**Path alias**: `@/` → `frontend/src/`. Use it everywhere; relative imports across folders are tech debt.

**Quality gates** (`frontend/package.json` + `frontend/tsconfig.app.json` + `frontend/eslint.config.js`):

- TypeScript: `strict: true` + `noUnusedLocals` + `noUnusedParameters` + `noFallthroughCasesInSwitch` + `noUncheckedSideEffectImports`. Target ES2023.
- ESLint: `@eslint/js` + `typescript-eslint` + `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh`. One project-specific rule disabled (`react-hooks/incompatible-library`) because TanStack Table returns non-memoizable functions.
- No Prettier, no Husky, no test runner. Strict mode + ESLint catches most regressions.

```bash
cd frontend
npm run lint        # ESLint
npm run build       # tsc -b && vite build
npm run dev         # Vite dev server, port 5173, proxies /api → :8000
```

---

## Project shape

```
frontend/
├── package.json
├── vite.config.ts          # base "/", proxy /api → :8000, alias @/ → src/
├── tsconfig.app.json       # strict mode + noUnusedLocals/Parameters
├── eslint.config.js
├── components.json         # shadcn/ui config (new-york, neutral, css vars, lucide)
├── index.html
├── public/
└── src/
    ├── App.tsx             # createBrowserRouter, lazy pages, providers
    ├── index.css           # Tailwind v4 @theme block (OKLCH tokens) — NO tailwind.config.ts
    ├── api/                # Typed fetch clients (1:1 with src/web/api/*)
    ├── hooks/              # React Query hooks + custom UI hooks
    ├── types/              # Hand-maintained TS interfaces mirroring Pydantic
    ├── lib/                # cn(), formatDuration, credential-store, local-storage, span-autodetect, …
    ├── pages/              # Route components (lazy-loaded, except Dashboard)
    └── components/
        ├── ui/             # shadcn/ui primitives (named exports, CVA variants)
        ├── layout/         # AppShell + NAV_ITEMS + PageHeader
        ├── wizard/         # Multi-step form scaffolding
        ├── model-selection/# Provider-specific forms + ModelList
        ├── plugin-config/  # Dynamic ConfigField renderer
        ├── charts/         # recharts wrappers
        ├── data-table/     # TanStack Table wrapper + faceted filters
        ├── review/         # Human-annotation workspace
        └── prompts/        # Prompt Studio editor + picker (in flight)
```

---

## Adding a new page

This is the most-broken workflow because three places must stay in sync. Use the [`add-frontend-page`](../.claude/skills/add-frontend-page/SKILL.md) skill for the full recipe; the short version:

1. Create `frontend/src/pages/<route>/index.tsx` (or `<route>.tsx` for non-nested).
2. Lazy-load it in `frontend/src/App.tsx` and add a route entry.
3. **Add a `NAV_ITEMS` entry in `frontend/src/components/layout/app-shell.tsx`** — there is no auto-discovery. The hook `H3` (NAV_ITEMS nudge) prints a reminder when a new page file is written.
4. If the page has unsaved-state editing, wire `useBlocker()` (see Prompt Studio editor for the canonical pattern).

---

## React Query conventions

Three things are easy to break here. Use the [`frontend-react-query-recipes`](../.claude/skills/frontend-react-query-recipes/SKILL.md) skill when adding a new hook.

### `staleTime` decision matrix

| Data lifetime | `staleTime` | Examples |
|---|---|---|
| Immutable (versioned, snapshot) | `Infinity` | `useReviewCases`, `useTranslation`, `usePromptVersion`, `usePlugins`, `useMetadata` |
| Slow-changing metadata | `30_000` – `60_000` | Ollama model list, OpenAI model list, HF endpoint metadata |
| Expensive aggregations | `5_000` | `useChartData` |
| Live state | `0` (default) | `useResults`, `useTestsets`, list endpoints |

`refetchOnWindowFocus: false` is set globally in `App.tsx` QueryClient defaults. Combined with `staleTime: Infinity` for review cases, this guarantees that an active annotation session never silently swaps data underneath the user.

### Cache invalidation

- **Exact match** (most common): `queryClient.invalidateQueries({ queryKey: ["jobs", filename] })` — invalidates the one specific entry.
- **Prefix match** (used in `useDeleteAnnotations`): `queryClient.invalidateQueries({ queryKey: ["review-cases"] })` — invalidates ALL `["review-cases", ...]` keys regardless of the trailing args. Critical for multi-file review sessions where the same hook is called with different file lists.
- **List + cascade**: when a mutation changes a parent + dependent shape, invalidate both. Example: `useSaveAnnotation` invalidates `["results"]` (to refresh `has_annotations`) AND lets `useReviewCases` stay stale (snapshot) — the user's draft is the source of truth until they save.

### Polling

- `useJobs(polling=true)` enables `refetchInterval: 3000` only when actively watching jobs. The Jobs page passes `polling=true`; other consumers don't.
- `useJobStatus` uses **dynamic** polling — stops the moment job state hits `completed` / `failed` / `cancelled` to avoid wasted requests.

### Mutations

Default pattern: server-authoritative. Mutations block on the server response, then `onSuccess` invalidates affected query keys. No optimistic updates anywhere in the codebase — they're not needed for the workflows.

---

## Design tokens (Tailwind v4)

**There is no `tailwind.config.ts`.** Tailwind v4 reads tokens from CSS, not JS. All design tokens live in [`frontend/src/index.css`](../frontend/src/index.css) inside an `@theme { ... }` block.

```css
@import "tailwindcss";

@custom-variant dark (&:is(.dark *));

@theme {
  --color-background: oklch(1 0 0);
  --color-foreground: oklch(0.145 0 0);
  --color-primary: oklch(0.205 0 0);
  --color-chart-1: oklch(0.646 0.222 41.116);
  --color-sidebar: oklch(0.985 0 0);
  --color-sidebar-primary: oklch(0.205 0 0);
  --radius-sm: 0.25rem;
  /* ... */
}
```

Token families:

| Family | Variables | Used by |
|---|---|---|
| Base | `--color-{background,foreground,card,popover,primary,secondary,muted,accent,destructive,border,input,ring}` | shadcn/ui primitives |
| Sidebar palette | `--color-sidebar*` (background, foreground, primary, accent, border, ring) | `AppShell` sidebar only — keep distinct from base |
| Chart palette | `--color-chart-1` through `-5` | recharts wrappers in `components/charts/` |
| Radius | `--radius-{sm,md,lg,xl}` | shadcn radius scale |

**Dark mode**: toggled via `.dark` class on `<html>` (set by `ThemeProvider`). The `@custom-variant dark (&:is(.dark *))` declaration teaches Tailwind v4 to interpret `dark:` prefixed classes correctly.

**When adding a color**: extend `@theme`, do NOT inline OKLCH values in component classes. The `cn()` helper composes class names; raw color literals can't be theme-shifted.

Use the [`frontend-design-tokens`](../.claude/skills/frontend-design-tokens/SKILL.md) skill for guidance on theme-aware additions.

---

## shadcn/ui & component conventions

Configuration in [`frontend/components.json`](../frontend/components.json):
- Style: `new-york`
- Base color: `neutral`
- CSS variables: `true` (consume tokens from `index.css`)
- Icon library: `lucide`
- Aliases: `@/components`, `@/components/ui`, `@/lib/utils`, `@/hooks`

**Primitives**: 20 components installed under `components/ui/` (button, card, dialog, dropdown-menu, sheet, select, tabs, table, tooltip, popover, collapsible, command, label, input, textarea, checkbox, progress, badge, separator, sonner). All use **named exports** and `class-variance-authority` for variant systems.

**To install a new primitive**: `cd frontend && npx shadcn add <component>`. The CLI handles file placement; you usually don't need to edit anything else. See the [`add-shadcn-component`](../.claude/skills/add-shadcn-component/SKILL.md) skill.

**Class composition**: always use `cn(...inputs)` from `@/lib/utils`. Never concatenate classes manually — `tailwind-merge` resolves conflicts that string concat misses.

**No form library**: forms use raw `useState` + `onChange` callbacks. Validation is per-component. If you reach for react-hook-form / Zod, propose it via TECHDEBT first; it's a deliberate non-choice today.

---

## State management

- **Server state**: TanStack React Query (see § React Query conventions above).
- **Theme**: `ThemeProvider` in `App.tsx`, localStorage-backed (`light` / `dark` / `system`).
- **localStorage**: namespaced via `frontend/src/lib/local-storage.ts` with the scheme `gol-bench:v1:<scope>:<key>`. The `v1` segment lets future migrations land without collision.
- **Encrypted credentials**: `frontend/src/lib/credential-store.ts` uses AES-GCM in-browser for multi-endpoint API keys.
- **URL state**: filters, mode toggles, and case navigation use search params (e.g. `/execute?mode=matrix`, `/charts?files=...`).
- **No Redux / Zustand / Jotai**. The Query cache + a few Contexts cover everything.

---

## Human review workspace

Full reference: [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md). Frontend-specific notes:

**Load-bearing files** (read first when working in this area):
- [frontend/src/pages/review.tsx](../frontend/src/pages/review.tsx) — orchestrator: draft state, case navigation, undo/redo, auto-negative inference
- [frontend/src/components/review/response-panel.tsx](../frontend/src/components/review/response-panel.tsx) — text rendering, drag/click marking, parser-disagreement banner
- [frontend/src/hooks/use-modifier-state.ts](../frontend/src/hooks/use-modifier-state.ts) — A/D/Shift hold-to-modify with blur cleanup
- [frontend/src/hooks/use-undo-stack.ts](../frontend/src/hooks/use-undo-stack.ts) — per-case 10-step snapshot stack
- [frontend/src/hooks/use-review-keybindings.ts](../frontend/src/hooks/use-review-keybindings.ts) — consolidated document-level keyboard handler
- [frontend/src/lib/span-autodetect.ts](../frontend/src/lib/span-autodetect.ts) — auto-position + auto-format on drag-select

**Stale-by-design risk**: shortcut definitions are duplicated across `help-dialog.tsx` (hardcoded MARK_ROWS table) and `use-review-keybindings.ts` (the actual handler). **No shared constant.** Hook H1 (`keybindings-sync-nudge`) prints a reminder when either file is touched.

**Modifier-state cleanup**: `use-modifier-state.ts` clears all flags on `window.blur` and `document.visibilitychange` to avoid stuck-modifier bugs when the user alt-tabs away. Text-field detection (`isTyping()`) suppresses tracking inside `<input>` / `<textarea>` / `contenteditable` so notes don't accidentally trigger mark-type changes.

**`auto_negative_inferred` sticky flag**: when the annotator marks an answer span while the parser extracted a different region, the UI auto-creates a dotted-rose negative span at the parser region. The flag prevents re-creation after dismissal within the same case. Reset on case advance.

**`was_truncated` auto-toggle**: every result entry carries `output.was_truncated` (computed at inference time from `finish_reason == "length"` OR `tokens_generated >= max_tokens_used`). When `emptyDraft()` runs on a case with this flag set AND no existing annotation, it seeds `response_classes: ["truncated"]` automatically.

---

## Prompt Studio frontend

Backend reference: [PROMPT_STUDIO.md](PROMPT_STUDIO.md). Frontend status: **all files currently untracked** (in active development by the user). The shape:

**Pages** (under `frontend/src/pages/prompts/`):
- `index.tsx` (catalog landing)
- `new.tsx` (`/prompts/new` — fresh prompt editor)
- `[id].tsx` (`/prompts/:id` — detail + version timeline)
- `[id]/edit.tsx` (`/prompts/:id/edit` — versioned editor)

**Components** (under `frontend/src/components/prompts/`):
- `prompt-catalog.tsx` — list view with filters
- `prompt-card.tsx` — list item
- `prompt-detail.tsx` — metadata + `VersionTimeline`
- `prompt-editor-page.tsx` — tabbed multi-language editor (6 LanguageTabs, plain `<Textarea>` per language, no Monaco)
- `prompt-picker.tsx` — single/multi-select picker for matrix wizard
- `language-tabs.tsx`, `language-dots.tsx` — language presence indicators
- `tag-input.tsx`, `version-timeline.tsx`

**Conventions specific to Prompt Studio**:
- `PromptRef = {id: string; version: number | null}` — `null` = "latest", number = pinned version. Serialized as `"id"` or `"id@N"` over the wire.
- EN content is **always required** at submit; other 5 languages are optional and fall back to EN at resolve time.
- Editing always creates a new version `v(n+1)` from the latest — there is no branching off an older version.
- `useMetadata().prompts` is cached `staleTime: Infinity`. After archive/restore mutations, manually `invalidateQueries(["metadata"])` to refresh the picker. (See React Query conventions.)
- Unsaved-changes guard via `useBlocker()` only catches in-app route changes; browser tab close is NOT guarded (no `beforeunload` handler).

---

## Backend ↔ frontend type sync

Types are hand-maintained in `frontend/src/types/`, mirroring Pydantic models in `src/web/`. There is no codegen.

Workflow when a backend response shape changes:

1. Find the Pydantic model in `src/web/api/<domain>.py` or `src/web/<domain>_store.py`.
2. Mirror the change in `frontend/src/types/<domain>.ts` (or the file that re-exports).
3. Grep call sites: `cd frontend && grep -r 'OldFieldName' src/`.
4. Update the corresponding API client in `frontend/src/api/<domain>.ts` if the request body or query params changed.
5. Update the React Query hook in `frontend/src/hooks/use-<domain>.ts` if return shape changed.
6. Smoke-test in the dev server.

Hook H4 (`type-drift-sentinel`) prints a reminder when an agent edits `src/web/api/*.py` or `src/web/*_store.py`. Use the [`sync-types-with-backend`](../.claude/skills/sync-types-with-backend/SKILL.md) skill for the checklist.

---

## Build artifacts

`frontend/dist/` is the production SPA, built by `npm run build`. The FastAPI app at `src/web/app.py` serves `dist/` at `/`. **Do not commit `dist/`** — it's gitignored. Re-build before pushing to staging if the deploy expects the SPA to be present.

---

## What's NOT in this codebase

(Things you might assume from React-ecosystem habits — none of these exist here.)

- No test runner (no Jest, no Vitest, no Playwright). Quality is enforced by TS strict mode + ESLint + manual smoke-testing.
- No form library. `useState` + `onChange`. (Deliberate.)
- No state container besides React Query + Contexts. No Redux, Zustand, Jotai, MobX.
- No CSS-in-JS (no styled-components, no Emotion). Tailwind v4 + CSS variables only.
- No Storybook. Component examples live in their consumers.
- No `tailwind.config.ts`. Tokens in `index.css` `@theme` block only.
- No Husky / lint-staged / commit hooks. ESLint runs in CI / pre-push manually.
- No Prettier config. Editor formatters use defaults.

---

*See also: [README.md](README.md) for the doc index, [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md) for annotation depth, [PROMPT_STUDIO.md](PROMPT_STUDIO.md) for system-prompt versioning, [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the cut-a-release workflow including frontend steps.*
