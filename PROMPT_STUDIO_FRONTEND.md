# Prompt Studio — System Prompts Frontend

> A frontend design plan for the `/prompts` surface introduced by the Prompt
> Studio backend. Companion to the backend doc inlined in
> `.claude/CLAUDE.md` §13. Audience: implementers (claude / human) who will
> turn this into React code.

---

## 1. Aesthetic direction — *editorial, restrained, typeset*

The rest of the app is utilitarian: forms, dashboards, data tables. Prompt
Studio is different — it's a workspace for **crafting text**. Long-form,
multilingual, versioned. The design should reflect that, the way the
`/review` workspace already steps slightly outside the table-and-card
default to feel editorial.

**Tone commitment:** *manuscript editor / typeset journal*. Restrained,
typography-led, monospace where it earns it (the prompt text itself —
it's instructions to a language model, treated as code). System fonts only
(matches the rest of the app — no new web font dependency); character comes
from weight, tracking, and inset margins, not new typefaces.

**Three motifs that carry this through:**

1. **The version spine.** Each prompt's version history rendered as a
   vertical timeline rail down the right side of the detail page — not
   buried in a "history" modal. Makes the immutability of versions a
   compositional asset.
2. **The reading column.** Prompt content is rendered in monospace inside
   a max-`68ch` typeset block with off-white inset (off-black in dark mode)
   and a subtle hairline border. Reads like a typewriter page, not a
   `<textarea>`.
3. **Canon vs drafts.** The four built-in prompts get a small uppercase
   *BUILT-IN* ribbon and slightly larger cards on the catalog, displayed
   above user-authored prompts ("My drafts") with a hairline divider
   between. Sets a *received text vs. your work* hierarchy without bolting
   on a new color.

**No new colors, no new fonts, no animation theatre.** Restraint is the
point. Within the existing OKLch palette, we lean on:

- `--color-foreground` for prompt body text (full-contrast — it's the
  payload).
- `--color-muted-foreground` for metadata (slug, timestamps, tags).
- `--color-primary` only for the active version-spine node and the primary
  save button.
- A single accent: language-coverage dots use `--color-foreground/80` for
  filled, `--color-border` for empty (no extra hue).

---

## 2. Information architecture

### Routes

| Path | Purpose |
|---|---|
| `/prompts`             | Catalog: built-ins + user prompts, with archive filter |
| `/prompts/new`         | Author a new user prompt (full page, not a modal) |
| `/prompts/:id`         | Read-only detail: language tabs + version spine |
| `/prompts/:id/edit`    | Edit: creates v(n+1) on save (full page) |

We intentionally **do not** model the editor as a Dialog/Sheet. The content
is multilingual long-form text; modals at that scale fight the user. The
configure / matrix wizards are the precedent for "this deserves its own
URL".

### Sidebar entry

Single flat item, between *Configure* and *Test Sets*:

```ts
{ to: "/prompts", icon: BookOpenText, label: "Prompt Studio" }
```

The page-header subtitle reads *"System Prompts · Manage versioned prompts
used as a benchmark axis."* — telegraphs that this is the System Prompts
sub-section of a larger Prompt Studio area without committing to a
sidebar group yet. When User Prompts / Plugin Prompts arrive, a horizontal
sub-nav strip slides into the page, and the sidebar item becomes a
collapsible group.

---

## 3. Page A — Catalog (`/prompts`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  System Prompts                          [⌕ search] [+ New prompt]  │
│  Versioned prompts used as a benchmark axis.                        │
└─────────────────────────────────────────────────────────────────────┘

┌─ CANON ────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐  │
│  │ ▏ BUILT-IN       │ │ ▏ BUILT-IN       │ │ ▏ BUILT-IN       │   │
│  │ Analytical       │ │ Casual           │ │ Adversarial      │   │
│  │ ─                │ │ ─                │ │ ─                │   │
│  │ Rigorous, step-  │ │ Friendly,        │ │ Resource-        │   │
│  │ by-step CoT      │ │ supportive       │ │ efficient        │   │
│  │                  │ │                  │ │                  │   │
│  │ ● ● ● ● ● ●  v1  │ │ ● ● ● ● ● ●  v1  │ │ ● ● ● ● ● ●  v1  │   │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘   │
│                                                                    │
│  ┌──────────────────┐                                              │
│  │ ▏ BUILT-IN       │                                              │
│  │ None             │                                              │
│  │ ─                │                                              │
│  │ Empty system     │                                              │
│  │ prompt.          │                                              │
│  │                  │                                              │
│  │ ○ ○ ○ ○ ○ ○  v1  │                                              │
│  └──────────────────┘                                              │
└────────────────────────────────────────────────────────────────────┘

──────────────────────────────────────────────────────────────────────

┌─ MY DRAFTS ─────────────────────────  [grid|list] [show archived] ┐
│                                                                    │
│  ┌──────────────────┐ ┌──────────────────┐                         │
│  │ Debug Verbose    │ │ Strict JSON Out  │                         │
│  │ debug-verbose    │ │ strict-json      │                         │
│  │ ─                │ │ ─                │                         │
│  │ Asks the model   │ │ Forces JSON-only │                         │
│  │ to narrate steps │ │ output, no prose │                         │
│  │                  │ │                  │                         │
│  │ ● ○ ○ ○ ○ ○  v3  │ │ ● ● ○ ○ ○ ●  v1  │                         │
│  └──────────────────┘ └──────────────────┘                         │
└────────────────────────────────────────────────────────────────────┘
```

### Card anatomy (`<PromptCard>`)

- **Top-left ribbon**: tiny uppercase `BUILT-IN` (`text-[10px] tracking-widest`) for canon, omitted for drafts. The ribbon is implemented as an inset-left border accent (`▏`) plus the label, not a corner badge — keeps the card edge clean.
- **Title**: prompt name, `text-base font-semibold`. Truncates at one line.
- **Slug line**: `text-xs font-mono text-muted-foreground`. Truncates.
- **Hairline rule**: separates header from description.
- **Description**: `text-sm text-muted-foreground`, two-line clamp.
- **Footer row** (`flex justify-between items-center mt-3`):
  - **Language coverage strip** (`<LanguageDots>`): six 6-pixel circles, en→es→fr→de→zh→ua. Filled if `content[lang]` is non-empty, hollow ring otherwise. Tooltip on hover gives the language name.
  - **Latest version chip**: `Badge` variant `outline`, label `v{n}`.
- **Hover**: subtle `bg-muted/40` lift, no shadow change. Cursor: pointer. Whole card is the click target → `/prompts/:id`.
- **Archived state** (drafts only): `opacity-70` + a small "ARCHIVED" pill in the footer instead of the version chip.

### Sections

- **Canon** — fixed three-up grid (`grid-cols-3`), built-ins always shown in the same order: Analytical, Casual, Adversarial, None. The fourth wraps to a new row.
- **Hairline divider** — `<Separator className="my-8" />` with a small `MY DRAFTS` label centered above it (mimics the masthead of a journal section).
- **My Drafts** — responsive grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`). Search filters by name/slug/tags. Toolbar (right side of section header) holds:
  - Search input (`<Input>` with leading `Search` icon, `w-64`)
  - View toggle (grid/list) — defaults to grid; list mode renders one row per prompt with the same data, useful for >20 drafts.
  - "Show archived" toggle (`<Checkbox>`).

### Empty states

- **No drafts**: large quiet block centered in section, text *"Author your first prompt"* + outline button. Uses the existing pattern from `ResultsPage` empty state.
- **Search returns nothing**: row of muted text *"No prompts match `"foo"`."*

### Top-bar action

`+ New prompt` is a **primary button** in the page-header right slot. Routes to `/prompts/new`.

---

## 4. Page B — Detail (`/prompts/:id`)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Analytical                                              ▏ BUILT-IN  │
│  builtin_analytical · 1 version                                      │
│  Rigorous, step-by-step chain-of-thought reasoning.                  │
│  [analytical] [reasoning]                                            │
│                                  [Edit (creates v2)] [Duplicate ⋯]   │
└──────────────────────────────────────────────────────────────────────┘

┌─ Tabs: [EN] [ES] [FR] [DE] [ZH] [UA] ────────┐ ┌─ History ─────────┐
│ ●        ●     ●    ●    ●    ●               │ │                   │
│                                               │ │   ●  v1           │
│  ┌─────────────────────────────────────┐      │ │      Apr 24       │
│  │                                     │      │ │      seeded from  │
│  │  You are an expert analytical       │      │ │      PromptEngine │
│  │  engine designed for precision      │      │ │                   │
│  │  and complex problem-solving.       │      │ │                   │
│  │                                     │      │ │                   │
│  │  Your primary directive is to       │      │ │                   │
│  │  employ rigorous, step-by-step      │      │ │                   │
│  │  chain of thought reasoning…        │      │ │                   │
│  │                                     │      │ │                   │
│  └─────────────────────────────────────┘      │ │                   │
│                                               │ │                   │
└───────────────────────────────────────────────┘ └───────────────────┘
```

### Layout

`grid-cols-[minmax(0,1fr)_220px]` desktop, single-column on mobile. Right rail collapses into a `<Sheet>` triggered by a "History" button when narrow.

### Header block (`<PromptDetailHeader>`)

- Big name (`text-2xl font-bold tracking-tight`).
- Sub-row: slug (mono, muted) · *"N versions"* count · separator · timestamp of latest version (relative).
- Description (one paragraph, max-w-prose).
- Tags row: `<Badge variant="secondary">` chips, small.
- Action bar (right-aligned on desktop, full-width below on mobile):
  - **Edit** — primary button. For built-ins the label reads *"Edit (creates v2)"* — explicit warning against assuming overwrite.
  - **Duplicate as new** — outline button. Pre-fills the editor with current content under a fresh `usr_…` ID.
  - **Archive / Restore** — ghost button under a `⋯` dropdown. Confirms via toast.

### Language tabs (`<LanguageTabs>`)

Six tabs, each marked with a coverage dot (filled if the active version has non-empty content for that language, hollow otherwise). Switching to a hollow tab shows a faint banner *"This language falls back to English."* + a faded EN content body, not a hard empty state.

Tab labels are ISO codes uppercase (`EN`, `ES`, `FR`, `DE`, `ZH`, `UA`) — short, consistent with how `language` appears in the result-file metadata.

### Reading column (`<PromptContent>`)

The actual prompt text. Inside a card with:

- `bg-muted/30` (off-white in light, off-black in dark)
- `border border-border/60` hairline
- `rounded-md`
- `p-6`
- `font-mono text-sm leading-7`
- `whitespace-pre-wrap break-words`
- `max-w-[68ch]` to keep lines readable

Toolbar above the column (right-aligned, small ghost buttons):

- **Copy** — copies the rendered text. Toast confirms.
- **View raw** — toggles a higher-fidelity view (no soft-wrap, horizontal scroll).

### Version spine (`<VersionTimeline>`)

Vertical, top-to-bottom newest-first.

- Each node: a 14px circle. Active version (the one shown in the reading column) is filled with `bg-primary`. Others are `border-2 border-border` with no fill.
- Connector: 1px dashed `border-border/60` between nodes.
- Each row holds:
  - `v{n}` (mono, semibold)
  - relative timestamp (`text-muted-foreground text-xs`)
  - change_note (one-line clamp, `text-xs text-muted-foreground`)
- Click a node → URL becomes `/prompts/:id?v=N`, reading column scrubs to that version. v param is reflected in the active node and the tab content.
- For built-ins with only one version, the spine still renders (single node) — keeps layout stable, telegraphs that more versions are possible.

### Archived banner

If the prompt is archived: top of the page renders an amber-tinted banner *"Archived. New testsets won't see this prompt unless restored."* with a Restore button.

---

## 5. Page C — Editor (`/prompts/:id/edit`, `/prompts/new`)

The most distinctive page. Where authoring happens.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Edit · Analytical                         ▏ BUILT-IN · saving v2    │
└──────────────────────────────────────────────────────────────────────┘

  Name        [ Analytical                                          ]
  Slug        [ builtin_analytical                              read-only ]    (read-only on edit)
  Description [ Rigorous, step-by-step chain-of-thought reasoning  ]
  Tags        [ analytical ✕ ]  [ reasoning ✕ ]  [ + add ]


  ┌─ Content ──────────────────────────────────────────────────────────┐
  │ Tabs: [EN ●] [ES ●] [FR ●] [DE ●] [ZH ●] [UA ●]                    │
  │                                                                    │
  │  v1 baseline (what users see today, read-only):                    │
  │  ┌────────────────────────────────────────────────────────────┐    │
  │  │ You are an expert analytical engine…  (faded, read-only)   │    │
  │  └────────────────────────────────────────────────────────────┘    │
  │                                                                    │
  │  Your draft for v2:                                                │
  │  ┌────────────────────────────────────────────────────────────┐    │
  │  │ ▌                                                          │    │
  │  │                                                            │    │
  │  │                                                            │    │
  │  └────────────────────────────────────────────────────────────┘    │
  │                                                       2,041 chars  │
  └────────────────────────────────────────────────────────────────────┘

──────────────────────────────────────────────────────────────────────
[Sticky footer]                                                        
  Change note  [ Tighter wording around chain-of-thought         ]
                                              [Cancel]  [Save as v2]
```

### Form fields

- **Name** — `<Input>`, required.
- **Slug** — `<Input>`. **Editable only when creating a new prompt.** On `/prompts/:id/edit` the slug becomes read-only with a tooltip *"Slugs are immutable so existing testsets stay resolvable."*
- **Description** — `<Textarea>` short (`min-h-[60px]`).
- **Tags** — small chip input. Backspace deletes last; comma/enter commits new tag. Cap at 32 (matches backend).

### Content editor (the centerpiece)

- **Tab strip**: same six tabs as the detail page. Each tab carries a coverage dot — but the dot now reflects the **draft** state, not the saved state. As the user types a non-empty value into a tab, that tab's dot fills. EN's dot has a small asterisk ★ — required.
- **Per-tab body** (split vertically when editing an existing prompt):
  - **Baseline panel** (top half, `h-[180px]`, `bg-muted/40`, `font-mono text-sm`, `opacity-65`, read-only): the previous version's content for this language. Helps the author see what they're amending. **Hidden entirely for `/prompts/new`** — there's no baseline.
  - **Draft textarea** (bottom half, `min-h-[280px]`, `font-mono text-sm`, `leading-7`): the new content. Auto-grows up to ~600px before scroll. Tab key inserts spaces (default browser behaviour is fine).
  - **Char count** at the bottom-right corner of the textarea (`text-xs text-muted-foreground`).
- **For new prompts**: only the draft textarea, full height. EN tab is opened by default and the textarea has placeholder *"Write the system prompt your model should receive…"*.
- **Per-tab "fall back to English"** small affordance: when a non-EN tab has empty content, a hairline note below the textarea reads *"Empty → falls back to EN at runtime."* — explanatory, not error-y.

### Sticky footer

`fixed bottom-0` on small screens, sticky at the bottom of the editor card on desktop. Always visible.

- **Change note** input (`<Input>`). Optional but encouraged. Placeholder *"What changed?"*. On save, lands in `prompt_versions.change_note`.
- **Cancel** outline button → router-back, with an *unsaved-changes* confirm dialog if the draft is dirty.
- **Save as v{n+1}** primary button. Disabled until EN content is non-empty *and* something has actually changed vs. the latest version (no-op edits are blocked client-side; backend would also reject if we wanted to enforce, but the UX win is preventing accidental "noise versions").

### Save flow

For an existing prompt:

1. Validate locally (`content.en` non-empty, name non-empty, no draft = baseline).
2. `POST /api/prompts/:id/versions` with `{ content, change_note }`.
3. On success: invalidate `["prompts"]`, `["prompts", id]`, `["prompts", id, "versions"]`. Toast: *"Saved as v{n+1}"*. Navigate to `/prompts/:id?v=N`.
4. On error (400/409/server): inline error banner inside the editor, no navigation.

For a new prompt:

1. Validate locally (name, slug-or-derive, content.en).
2. `POST /api/prompts` with `{ name, slug?, description, content, tags }`.
3. On success: invalidate `["prompts"]`. Toast: *"Created"*. Navigate to `/prompts/:returned_id`.
4. 409 (slug conflict): focus the slug field, surface the message inline ("Slug already in use — try `debug-verbose-2`?").

### Unsaved-changes guard

`useBlocker` from React Router on a dirty form. Shadcn `<AlertDialog>` (or a plain `<Dialog>` since we don't have AlertDialog) confirms *"Discard your changes?"*.

---

## 6. Component inventory

New components, all under `frontend/src/components/prompts/`:

| Component | Purpose |
|---|---|
| `<PromptCard>`           | Catalog card with ribbon + coverage strip + version chip |
| `<LanguageDots>`         | Six-dot coverage indicator (also used inside `<LanguageTabs>` triggers) |
| `<LanguageTabs>`         | Six-tab strip with coverage dots in trigger labels |
| `<PromptContent>`        | Read-only typeset reading column with copy/raw toolbar |
| `<VersionTimeline>`      | Vertical version spine, click to scrub |
| `<PromptDetailHeader>`   | Page-header variant with name, slug, description, tags, action bar |
| `<PromptStatusRibbon>`   | Inset-left BUILT-IN / ARCHIVED ribbon |
| `<PromptCatalogSection>` | Reusable section wrapper for Canon / My Drafts (header + grid) |
| `<TagInput>`             | Chip-input for tags (could be lifted to `components/ui/` if reused) |
| `<UnsavedChangesGuard>`  | Hook + AlertDialog wrapper around React Router's blocker |
| `<PromptEditor>`         | The whole editor body (form fields + tabbed content + footer) — used by both `new` and `edit` routes |

All consume existing shadcn primitives — no new design-system primitives.

Pages, under `frontend/src/pages/prompts/`:

- `index.tsx`      → Catalog
- `[id].tsx`       → Detail (uses URL search-param `?v=N` for active version)
- `[id].edit.tsx`  → Editor (existing prompt)
- `new.tsx`        → Editor (new prompt)

The two editor pages are thin wrappers around `<PromptEditor>` — they differ only in initial state and submit handler.

---

## 7. Data layer

### Types (`frontend/src/types/prompts.ts`)

Mirror the backend Pydantic schemas:

```ts
export type PromptSummary = {
  id: string
  name: string
  slug: string
  description: string
  is_builtin: boolean
  tags: string[]
  archived_at: string | null
  created_at: string
  created_by: string | null
  updated_at: string
  latest_version: number | null
}

export type PromptDetail = PromptSummary & {
  content: Record<string, string>  // {"en": "...", "es": "...", ...}
  change_note: string
}

export type PromptVersionMeta = {
  version: number
  parent_version: number | null
  change_note: string
  created_at: string
  created_by: string | null
}

export type PromptVersionDetail = PromptVersionMeta & {
  prompt_id: string
  content: Record<string, string>
}

export type CreatePromptRequest = {
  name: string
  slug?: string
  description?: string
  content: Record<string, string>
  tags?: string[]
  created_by?: string
}

export type CreateVersionRequest = {
  content: Record<string, string>
  change_note?: string
  parent_version?: number
  created_by?: string
}

export type UpdatePromptRequest = {
  name?: string
  description?: string
  tags?: string[]
}
```

### API client (`frontend/src/api/prompts.ts`)

```ts
import { get, post, patch, del } from "./client"
// (patch / del helpers — extend client.ts if not yet exported)

export const fetchPrompts = (includeArchived = false) =>
  get<PromptSummary[]>("/api/prompts", { include_archived: String(includeArchived) })

export const fetchPrompt = (id: string) =>
  get<PromptDetail>(`/api/prompts/${id}`)

export const fetchPromptVersions = (id: string) =>
  get<PromptVersionMeta[]>(`/api/prompts/${id}/versions`)

export const fetchPromptVersion = (id: string, version: number) =>
  get<PromptVersionDetail>(`/api/prompts/${id}/versions/${version}`)

export const createPrompt = (body: CreatePromptRequest) =>
  post<{ prompt_id: string }>("/api/prompts", body)

export const createPromptVersion = (id: string, body: CreateVersionRequest) =>
  post<{ prompt_id: string; version: number }>(`/api/prompts/${id}/versions`, body)

export const updatePromptMetadata = (id: string, body: UpdatePromptRequest) =>
  patch<{ ok: boolean }>(`/api/prompts/${id}`, body)

export const archivePrompt = (id: string) =>
  post<{ ok: boolean }>(`/api/prompts/${id}/archive`, {})

export const restorePrompt = (id: string) =>
  post<{ ok: boolean }>(`/api/prompts/${id}/restore`, {})
```

The client wrapper at `frontend/src/api/client.ts` needs `patch<T>(path, body)` added. One-liner — same shape as `post`.

### React Query hooks (`frontend/src/hooks/use-prompts.ts`)

```ts
export const usePrompts = (includeArchived = false) =>
  useQuery({
    queryKey: ["prompts", { archived: includeArchived }],
    queryFn: () => fetchPrompts(includeArchived),
    staleTime: 30_000,         // catalog is mildly hot — refresh after 30s
  })

export const usePrompt = (id: string | undefined) =>
  useQuery({
    queryKey: ["prompts", id],
    queryFn: () => fetchPrompt(id!),
    enabled: Boolean(id),
    staleTime: 30_000,
  })

export const usePromptVersions = (id: string | undefined) =>
  useQuery({
    queryKey: ["prompts", id, "versions"],
    queryFn: () => fetchPromptVersions(id!),
    enabled: Boolean(id),
    staleTime: 30_000,
  })

export const usePromptVersion = (id: string | undefined, version: number | null) =>
  useQuery({
    queryKey: ["prompts", id, "versions", version],
    queryFn: () => fetchPromptVersion(id!, version!),
    enabled: Boolean(id) && version != null,
    staleTime: Infinity,        // versions are immutable — never refetch
  })

export const useCreatePrompt = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createPrompt,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  })
}

export const useCreatePromptVersion = (id: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateVersionRequest) => createPromptVersion(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prompts"] })
      qc.invalidateQueries({ queryKey: ["prompts", id] })
      qc.invalidateQueries({ queryKey: ["prompts", id, "versions"] })
    },
  })
}

export const useUpdatePromptMetadata = (id: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: UpdatePromptRequest) => updatePromptMetadata(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prompts"] })
      qc.invalidateQueries({ queryKey: ["prompts", id] })
    },
  })
}

export const useArchivePrompt = () => { /* same shape, calls archivePrompt */ }
export const useRestorePrompt = () => { /* same shape, calls restorePrompt */ }
```

`staleTime: Infinity` on `usePromptVersion` is the key correctness lever —
versions are immutable on the backend (no UPDATEs ever), so cached version
content is forever-valid. Saves a refetch every time the user scrubs the
spine.

---

## 8. Routing & nav wiring

### `frontend/src/App.tsx`

Below the `judge` route:

```tsx
const PromptsPage = lazy(() => import("@/pages/prompts"))
const PromptDetailPage = lazy(() => import("@/pages/prompts/[id]"))
const PromptEditPage = lazy(() => import("@/pages/prompts/[id].edit"))
const PromptNewPage = lazy(() => import("@/pages/prompts/new"))

// Inside <Route element={<AppShell />}>
<Route path="prompts"           element={<Suspense fallback={<PageLoader />}><PromptsPage     /></Suspense>} />
<Route path="prompts/new"       element={<Suspense fallback={<PageLoader />}><PromptNewPage   /></Suspense>} />
<Route path="prompts/:id"       element={<Suspense fallback={<PageLoader />}><PromptDetailPage/></Suspense>} />
<Route path="prompts/:id/edit"  element={<Suspense fallback={<PageLoader />}><PromptEditPage  /></Suspense>} />
```

Order matters: `prompts/new` before `prompts/:id` so React Router doesn't
match `new` as an `:id`.

### `frontend/src/components/layout/app-shell.tsx`

Add to `NAV_ITEMS`, between `Configure` and `Test Sets`:

```tsx
{ to: "/prompts", icon: BookOpenText, label: "Prompt Studio" },
```

`BookOpenText` is from lucide-react; if it's not in the version pinned by the project, fall back to `BookOpen` — both convey the right metaphor.

---

## 9. Implementation order — five small PRs

A single big PR would be hard to review. Splitting:

1. **Plumbing** — types, API client (`prompts.ts`), hooks (`use-prompts.ts`), routes registered, sidebar entry, empty placeholder pages that render `PageHeader` + a "coming soon" stub. Confirms the nav and lazy-loading work end-to-end. *Tiny.*
2. **Catalog page** — `<PromptCard>`, `<LanguageDots>`, `<PromptCatalogSection>`, search + grid/list toggle. Read-only. *Medium.*
3. **Detail page** — `<PromptDetailHeader>`, `<LanguageTabs>`, `<PromptContent>`, `<VersionTimeline>`. URL-backed `?v=N`. Still read-only (Edit button exists but routes to a stub). *Medium.*
4. **Editor** — full `<PromptEditor>` with form fields, tabbed content, sticky footer, save flow, unsaved-changes guard. Both `/new` and `/:id/edit` wired. *Largest piece.*
5. **Polish** — Archive/Restore actions, Duplicate-as-new, Tag input, copy-to-clipboard on `<PromptContent>`, responsive collapsing of the version rail into a Sheet on mobile. *Small.*

Each PR ships a testable surface. After (3), users can browse the catalog and read prompts. After (4) they can author + version. (5) is quality-of-life.

---

## 10. Open decisions worth confirming before code

A handful of decisions I made by default but that are worth a quick gut-check:

1. **Built-in editability surface.** I made *Edit (creates v2)* the primary action on built-ins, mirroring the backend's "seed-but-editable" choice. Alternative: hide *Edit* on built-ins, force users to *Duplicate as new* into a `usr_…` prompt, which keeps canon pristine. **Recommendation: keep Edit on built-ins** (matches the backend semantic) but the explicit *(creates v2)* label is the safety rail. Confirm.

2. **Editor as full-page route, not modal/Sheet.** The configure / matrix wizards are precedent — long-form authoring earns its own URL. Modals would lose unsaved-changes guards on accidental close. Confirm.

3. **"Compare two versions" diff view.** Not in this plan. Could be added later as a v1 / v2 split-pane on the detail page. The version spine is enough to *see* history; comparing prose diffs is a power feature that would deserve its own page if added. **Recommendation: defer to a follow-up.**

4. **Slug immutability on edit.** Backend doesn't enforce immutable slug, but I want to enforce it client-side to protect old testsets that may reference a slug-derived URL. **Recommendation: lock the slug after creation.** If a slug ever needs renaming, that becomes an admin operation.

5. **No-op save prevention.** I'd like the *Save as v(n+1)* button to disable when the draft is byte-identical to the latest version. Stops noise versions. The backend allows them, but UX-wise they're traps. Confirm.

If any of those land differently, the impact is tightly localized to the editor page — the catalog and detail layouts don't change.

---

## 11. What this plan deliberately does NOT do

- No web fonts. The system stack is enough.
- No new color tokens. The OKLch palette + foreground/muted/border carry it.
- No animation library (no Framer Motion). Tailwind transitions on hover and tab switch only.
- No diff library. Plain `<pre>` baseline above plain `<Textarea>` is enough for v1.
- No drag-and-drop reordering of versions (versions are append-only by design).
- No collaborative editing / locking. Single-user assumption matches the rest of the app.
- No language priority / fallback configuration. EN-fallback is the rule, hardcoded.
- No prompt templating / variables in v1. Prompts are static text.
- No frontend tests (the project doesn't have a frontend test harness — verified earlier in CLAUDE.md). Manual browser testing per the conventions in `.claude/CLAUDE.md`.
