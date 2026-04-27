---
name: frontend-react-query-recipes
description: React Query (TanStack Query 5) patterns for the GoL Benchmark frontend. Use when adding a new query/mutation hook under frontend/src/hooks/, debugging stale data, or fixing cache invalidation. Covers staleTime decisions, exact-vs-prefix invalidation, polling, and the project-specific snapshot semantics for review cases and prompt versions.
tools: Read, Write, Edit, Bash, Grep, Glob
---

# React Query Recipes

The frontend uses TanStack React Query 5 for **all** server state. There is no Redux, no Zustand. Every backend interaction goes through a `use*` hook in `frontend/src/hooks/`.

The conventions below are load-bearing — breaking them produces silent staleness, runaway polling, or cache leaks across multi-file workflows. The hook H2 (`eslint-frontend-on-edit`) catches some violations but not semantic ones; this skill is the design rulebook.

For the slim agent index see [frontend/CLAUDE.md](../../../frontend/CLAUDE.md). For the full frontend reference see [docs/FRONTEND_GUIDE.md](../../../docs/FRONTEND_GUIDE.md).

---

## The `staleTime` decision matrix

| Data lifetime | `staleTime` | Why | Examples |
|---|---|---|---|
| **Immutable / versioned snapshot** | `Infinity` | Once fetched, the bytes never change. Refetching is wasted work and breaks UX (e.g. annotation drafts). | `useReviewCases`, `useTranslation`, `usePromptVersion` (older versions), `usePlugins`, `useMetadata` |
| **Slow-changing metadata** | `30_000` – `60_000` | Updates only when an external system changes (Ollama daemon restart, prompt archived). | Ollama / OpenAI / HF model lists, prompt list (`30_000`) |
| **Expensive aggregation** | `5_000` | Re-running the aggregation is costly; small staleness window is acceptable. | `useChartData` |
| **Live state** | `0` (default) | List endpoints where the backend is the source of truth and items can change anytime. | `useResults`, `useTestsets`, `useJobs` (when not polling) |

**Global defaults** (set in `App.tsx` `QueryClient`): `retry: 1`, `refetchOnWindowFocus: false`. Combined with `staleTime: Infinity` for review cases, this guarantees an annotation session never silently swaps data while the user is mid-draft.

```tsx
// Good — immutable snapshot, never refetch
return useQuery({
  queryKey: ["review-cases", key, opts.skipCorrect, opts.skipEmpty, matchKey],
  queryFn: () => fetchReviewCases({ ... }),
  enabled: fileIds.length > 0,
  refetchOnWindowFocus: false,
  staleTime: Infinity,
})

// Good — slow-changing metadata
return useQuery({
  queryKey: ["models", "ollama", host],
  queryFn: () => fetchOllamaModels(host),
  staleTime: 30_000,
})

// Bad — list endpoint pinned to Infinity hides backend changes
return useQuery({
  queryKey: ["results"],
  queryFn: fetchResults,
  staleTime: Infinity,  // ❌ stale results page after a job completes
})
```

---

## Cache invalidation — exact vs prefix matching

`invalidateQueries({ queryKey })` semantics are crucial and easy to get wrong.

### Exact match (most common)

```tsx
qc.invalidateQueries({ queryKey: ["jobs", filename] })
```

Invalidates **only** the entry whose key is exactly `["jobs", filename]`. Use this when the mutation affects one specific resource.

### Prefix match (high-impact)

```tsx
qc.invalidateQueries({ queryKey: ["review-cases"] })
```

Invalidates **every** query whose key starts with `["review-cases"]`, regardless of trailing args. Used by `useDeleteAnnotations` because the same hook is called with different file lists across multi-file review sessions:

```tsx
// All of these get busted by one prefix invalidation:
["review-cases", "fileA", true, false, ""]
["review-cases", "fileA,fileB", true, false, "exact,partial"]
["review-cases", "fileC", false, false, ""]
```

**When to use prefix**: when the same hook produces many query keys for slightly different inputs and a mutation affects the underlying data they all read from. **When NOT**: when you mean to invalidate one specific entry — prefix-invalidation will burn unrelated caches.

### Cascade invalidation

When a mutation changes a parent + dependent shape, invalidate both:

```tsx
// useDeleteAnnotations
onSuccess: (_, { result_file_id, filename }) => {
  qc.invalidateQueries({ queryKey: ["results"] })                  // refresh `has_annotations` flag
  qc.invalidateQueries({ queryKey: ["annotations", filename] })    // exact: this file's annotations
  qc.invalidateQueries({ queryKey: ["review-cases"] })             // prefix: ALL active sessions
}
```

This is fragile if query keys change. Add a code comment when you use prefix invalidation explaining WHY the prefix is needed.

---

## Polling

Polling is opt-in per call site. Two patterns:

### Static interval

```tsx
export function useJobs(polling = false) {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: polling ? 3000 : false,
  })
}
```

The Jobs page calls `useJobs(true)`; the Dashboard calls `useJobs(false)`. **Default to `false`** so consumers opt in deliberately.

### Dynamic interval (stop-on-terminal)

```tsx
export function useJobStatus(id: string) {
  return useQuery({
    queryKey: ["jobs", id],
    queryFn: () => fetchJob(id),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 1000
      const terminal = ["completed", "failed", "cancelled"].includes(data.state)
      return terminal ? false : 1000
    },
  })
}
```

This pattern saves wasted polling once the resource reaches a terminal state. Use it for any resource that has terminal states (jobs, judge runs).

---

## Mutation patterns

The codebase uses **server-authoritative** mutations: block on the server response, then `onSuccess` invalidates. **No optimistic updates anywhere.** They're not needed; the workflows tolerate the round-trip latency.

```tsx
export function useSaveAnnotation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AnnotateRequest) => saveAnnotation(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["results"] })
      // Note: deliberately NOT invalidating ["review-cases"] — the user's draft
      // is the source of truth until they explicitly save. Refetching the case
      // list mid-session would discard their work.
    },
  })
}
```

Comment your invalidation choices. Future-you will thank you.

### Mutation invariants

- **Always invalidate something** unless you're certain no other query reads the affected data. Forgotten invalidations show up as "the UI didn't update" bugs.
- **Don't mutate cache directly** with `setQueryData` unless you have a measured perf reason. Server-round-trip + invalidate is the path of least surprise.
- **Toast on `onSuccess` / `onError`** for user-initiated mutations. Use the `sonner` toast (`import { toast } from "sonner"`).

---

## Query key conventions

Keys are arrays. The first element is always a string identifying the resource family:

```tsx
["jobs"]                      // job list
["jobs", id]                  // single job
["results"]                   // result list
["results", filename]         // single result file
["review-cases", ...args]     // review session — prefix-busted on annotation delete
["annotations", filename]     // annotations for one file
["models", "ollama", host]    // hierarchical: provider, then host
["prompt", id, "versions", v] // hierarchical: prompt, then versions, then version number
["metadata"]                  // global metadata (cached Infinity)
```

**Hierarchical keys** are friendly to prefix-invalidation: invalidating `["models", "ollama"]` busts all hosts; invalidating `["models"]` busts all providers.

**Don't use objects in keys**. `["jobs", { state: "running" }]` is technically valid but `JSON.stringify` ordering can produce subtle cache misses across renders. Pass primitives, joined / sorted as needed:

```tsx
// Good
const key = fileIds.slice().sort().join(",")
const matchKey = (matchTypes ?? []).slice().sort().join(",")
queryKey: ["review-cases", key, skipCorrect, skipEmpty, matchKey]
```

---

## When the hook is enabled / disabled

Use `enabled` to defer fetching until preconditions are met. Don't `useQuery` only when you have data — that violates rules of hooks. Always call the hook, conditionally enable the fetch:

```tsx
return useQuery({
  queryKey: ["review-cases", key],
  queryFn: () => fetchReviewCases(...),
  enabled: fileIds.length > 0,  // ← guard
})
```

The hook returns `data: undefined, isLoading: false, isPending: true` when disabled. Branch on that in the consumer.

---

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| "I deleted an annotation but the list still shows it" | Mutation forgot to invalidate the parent list | Add `invalidateQueries` to `onSuccess`. Use prefix match if many keys read from the same shape. |
| "After Prompt Studio archive/restore, picker shows stale entries" | `useMetadata` is `staleTime: Infinity` and not auto-invalidated | After mutation: `qc.invalidateQueries({ queryKey: ["metadata"] })` |
| "Job page polls forever after job completes" | Used static `refetchInterval` instead of dynamic | Switch to the stop-on-terminal pattern (see Polling above) |
| "Two pages show different versions of the same data" | One uses default `staleTime: 0`, one uses `Infinity` | Pick one — usually the more permissive (`30_000`+). The default-0 hook will refetch on next mount. |
| "Tests/`tsc` passes but UI shows undefined fields" | Backend returns a field the TS type doesn't declare; React Query passes it through but no consumer reads it | Sync types via `sync-types-with-backend` skill |
| `react-hooks/incompatible-library` ESLint error | TanStack Table function returned mid-component | This rule is disabled project-wide (see `eslint.config.js`); don't see this error. If you do, your hook usage is genuinely buggy. |

---

## What NOT to do

- **Don't pin list endpoints to `Infinity`.** They MUST refetch when the underlying server-side resource changes; default `staleTime: 0` is correct.
- **Don't use prefix invalidation when you mean a single entry.** It burns unrelated caches and creates "why did everything just refetch?" mysteries.
- **Don't skip `enabled` for conditional queries.** `useQuery` must be called unconditionally; gate the FETCH, not the HOOK CALL.
- **Don't introduce `setQueryData` shortcuts.** The pattern in this codebase is server-round-trip + invalidate. Optimistic updates have a maintenance cost; only adopt them with a measured benefit.
- **Don't add `refetchOnWindowFocus: true` per-hook.** The global default is `false`; an exception is a strong signal something is wrong with the cache strategy.
- **Don't forget to comment prefix invalidations.** Future-you reading `invalidateQueries({ queryKey: ["X"] })` won't know whether the `["X"]` is exact or prefix without the comment.
