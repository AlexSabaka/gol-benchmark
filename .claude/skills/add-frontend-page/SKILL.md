---
name: add-frontend-page
description: Add a new page (route) to the GoL Benchmark React SPA. Use when the user asks to "add a new page", "wire up a /foo route", "create a new screen", or scaffolds a file under frontend/src/pages/. Walks the three places that must stay in sync — page file, App.tsx route entry, AppShell NAV_ITEMS — and the optional useBlocker for unsaved-changes guards.
tools: Read, Write, Edit, Bash, Grep, Glob
---

# Add a New Frontend Page

The frontend uses React Router 7 (data router) with **lazy-loaded pages** under `frontend/src/pages/`. A new page requires edits in **three places** because the sidebar nav has no auto-discovery. The hook `H3` (`nav-items-nudge`) prints a reminder when a new page file is written; this skill is the recipe.

For broader frontend conventions see [docs/FRONTEND_GUIDE.md](../../../docs/FRONTEND_GUIDE.md). For the slim agent index see [frontend/CLAUDE.md](../../../frontend/CLAUDE.md).

---

## Step 1 — Create the page file

Pages live under `frontend/src/pages/`. Two layouts are used:

| Layout | When |
|---|---|
| `frontend/src/pages/<route>.tsx` | Single-file page, no nested routes |
| `frontend/src/pages/<route>/index.tsx` (+ siblings for nested routes) | Page with sub-routes (e.g. `/prompts`, `/prompts/new`, `/prompts/:id`, `/prompts/:id/edit`) |

For nested pages use file names that mirror the route, e.g. `[id].tsx` for `:id`, `[id]/edit.tsx` for `:id/edit`. (See the existing `pages/prompts/` cluster for the canonical pattern.)

```tsx
// frontend/src/pages/foo/index.tsx
import { useEffect } from "react"
import { PageHeader } from "@/components/layout/page-header"

export default function FooPage() {
  useEffect(() => {
    document.title = "Foo · GoL Benchmark"
  }, [])

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <PageHeader title="Foo" description="One-sentence description." />
      {/* page content */}
    </div>
  )
}
```

Conventions:

- **Default export** the page component. (Page files differ from primitives, which are named-exported.)
- Set `document.title` in a one-shot `useEffect` if you want the browser tab to reflect the page name.
- Use `PageHeader` from `@/components/layout/page-header` for the top-of-page title block — it gives consistent typography.
- Wrap content in `flex h-full flex-col gap-4 p-4` (the AppShell consumer expects a flex column).

---

## Step 2 — Lazy-load + register the route in `App.tsx`

Open [`frontend/src/App.tsx`](../../../frontend/src/App.tsx). Every page (except Dashboard, which is eager-loaded) is registered in two places: the `lazy(...)` declarations near the top, and the `createBrowserRouter` route table.

**Add the lazy import** (alphabetize roughly with neighbors):

```tsx
const FooPage = lazy(() => import("@/pages/foo"))
```

**Add the route entry** inside the `children` array:

```tsx
const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      // ... existing routes ...
      { path: "foo", element: wrap(FooPage) },          // ← new
      // ... keep `{ path: "*", element: <NotFound /> }` last
    ],
  },
])
```

The `wrap()` helper (defined at the top of `App.tsx`) wraps the lazy component in `<Suspense fallback={<PageLoader />}>` — every lazy page must use it. The Dashboard is the only exception (eager-loaded so the first paint is fast).

For nested routes, register each path explicitly:

```tsx
{ path: "foo", element: wrap(FooPage) },
{ path: "foo/new", element: wrap(FooNewPage) },
{ path: "foo/:id", element: wrap(FooDetailPage) },
{ path: "foo/:id/edit", element: wrap(FooEditPage) },
```

(There's no nested-children form in this codebase — every route is a flat entry under the AppShell parent. Matches the existing `prompts/...` pattern.)

---

## Step 3 — Add the sidebar entry in `AppShell`

Open [`frontend/src/components/layout/app-shell.tsx`](../../../frontend/src/components/layout/app-shell.tsx). The `NAV_ITEMS` constant at the top is the **single source of truth** for sidebar navigation. There is no auto-discovery from routes.

```tsx
import { /* existing icons */, FileBarChart } from "lucide-react"  // pick a lucide icon

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  // ... existing entries ...
  { to: "/foo", icon: FileBarChart, label: "Foo" },              // ← new
]
```

**Choosing the icon**: browse [lucide.dev/icons](https://lucide.dev/icons) and pick something semantically aligned. Existing examples:
- `LayoutDashboard` → Dashboard
- `Settings2` → Configure
- `BookOpenText` → Prompt Studio
- `Database` → Test Sets
- `Play` → Execute
- `Activity` → Jobs
- `BarChart3` → Results
- `LineChart` → Charts
- `FileText` → Reports
- `Scale` → Judge

**Choosing the position**: the order in `NAV_ITEMS` is the order in the sidebar. Match the conceptual workflow (build → execute → inspect → analyze) rather than alphabetical.

---

## Step 4 (optional) — Wire `useBlocker` for unsaved-changes guards

If your page has form-style editing where the user could lose work by navigating away, use React Router 7's `useBlocker`. The canonical pattern is in `frontend/src/components/prompts/prompt-editor-page.tsx`:

```tsx
import { useBlocker } from "react-router"

function MyEditorPage() {
  const [isDirty, setIsDirty] = useState(false)
  const [isPending, setIsPending] = useState(false)

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      isDirty &&
      !isPending &&
      currentLocation.pathname !== nextLocation.pathname,
  )

  useEffect(() => {
    if (blocker.state === "blocked") {
      const ok = window.confirm("Discard unsaved changes?")
      if (ok) blocker.proceed()
      else blocker.reset()
    }
  }, [blocker])

  // ... rest of editor
}
```

**Caveats**:
- `useBlocker` only catches in-app navigation. Browser tab close / refresh is NOT guarded by default. If you need that too, also add a `beforeunload` listener.
- `useBlocker` requires the data router (`createBrowserRouter`). The repo already uses it; just import.

---

## Step 5 — URL state (search params)

If the page has filters, modes, or shareable selections, persist them in the URL via React Router's `useSearchParams`. Existing patterns:

- `/execute?mode=simple` vs `/execute?mode=matrix` (Execute page mode toggle)
- `/charts?files=a.json.gz,b.json.gz` (Charts page file filter)
- `/review?files=...&case_id=...` (Review page case navigation)

```tsx
import { useSearchParams } from "react-router"

const [searchParams, setSearchParams] = useSearchParams()
const mode = searchParams.get("mode") ?? "simple"

// To update without losing other params:
setSearchParams((prev) => {
  prev.set("mode", "matrix")
  return prev
})
```

URL state is preferred over `useState` for anything the user might want to bookmark, share, or restore on reload.

---

## Step 6 — Smoke-test

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173/foo`. Verify:

- The page renders (no Suspense fallback stuck forever — that means the lazy import path is wrong)
- The sidebar shows the new entry (highlighted when on `/foo`)
- Browser title is updated (if you set `document.title`)
- TypeScript compiles: `npm run build` produces no errors
- ESLint passes: `npm run lint` (the `H2` hook also runs this on every edit)

---

## What NOT to do

- **Do not skip the `NAV_ITEMS` edit.** The page works without it (route resolves), but users have no way to find it.
- **Do not eager-import a new page.** Only Dashboard is eager. Lazy-load + `wrap()` keeps the initial bundle small.
- **Do not put route children under `path` in the route table.** This codebase uses a flat route list under one AppShell parent; match it.
- **Do not invent a new layout component.** Use `AppShell` (already provided by the parent route) + `PageHeader` for consistency.
- **Do not add `beforeunload` handlers globally.** They belong only on pages with truly unsaved state, and they prevent legitimate refreshes during dev.
- **Do not use a default export for primitives** (only pages get default exports).
