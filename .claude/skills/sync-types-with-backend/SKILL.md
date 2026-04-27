---
name: sync-types-with-backend
description: Mirror a backend Pydantic model change into the frontend TypeScript types. Use when the user says "the backend response shape changed", "I added a field to the API", "frontend doesn't see the new field", or after editing src/web/api/*.py / src/web/*_store.py. Walks the 5-step manual sync (no codegen) and lists where to grep for call sites.
tools: Read, Edit, Bash, Grep, Glob
---

# Sync Frontend Types with Backend

Frontend TypeScript types in `frontend/src/types/` are **hand-maintained, 1:1 with Pydantic models** in `src/web/`. There is no codegen. When backend response shapes change, the frontend must follow.

The hook H4 (`type-drift-sentinel`) prints a reminder when an agent edits backend API or store files. This skill is the manual checklist.

For the slim agent index see [frontend/CLAUDE.md](../../../frontend/CLAUDE.md). For the full frontend reference see [docs/FRONTEND_GUIDE.md](../../../docs/FRONTEND_GUIDE.md).

---

## The 5-step sync

### Step 1 — Find the Pydantic model

The backend organizes models by domain:

| Layer | Where models live | Examples |
|---|---|---|
| API request/response models | `src/web/api/<domain>.py` (top of file as `class XxxRequest(BaseModel)` / `class XxxResponse(BaseModel)`) | `src/web/api/testsets.py` `PromptConfig`, `src/web/api/matrix.py` `MatrixPromptAxes` |
| Persistence models (sometimes Pydantic, sometimes dataclasses, sometimes dicts) | `src/web/<domain>_store.py` | `src/web/prompt_store.py` `PromptVersionRow` |
| Plugin contract types | `src/plugins/base.py` | `TestCase`, `ParsedAnswer`, `EvaluationResult` |

Once you've identified the changed model, note **every field name + type + optionality**. Pay attention to:

- `Optional[X]` / `X | None` → TS `X | null` or `X | undefined`
- `Literal[...]` → TS string union
- `Dict[str, X]` → TS `Record<string, X>`
- `List[X]` → TS `X[]`
- `datetime` → TS `string` (FastAPI serializes to ISO 8601)
- Default values → mostly irrelevant on the wire, but `Optional` fields without defaults can still be omitted

### Step 2 — Find the corresponding TS type

Frontend types are organized in `frontend/src/types/`:

| Domain | File |
|---|---|
| Plugin schemas, ConfigField | `plugin.ts` |
| Models, providers | `model.ts` |
| Result entries, summaries | `result.ts` |
| Review cases, annotations, marks, classifications, improvement reports | `review.ts` |
| Prompts, versions, refs | `prompts.ts` |
| Jobs, job state | `job.ts` |
| Test sets | `testset.ts` |
| Matrix wizard | `matrix.ts` |
| Re-exports | `index.ts` |

**If the file doesn't exist for a new domain**, create it AND add a re-export to `frontend/src/types/index.ts`.

### Step 3 — Mirror the change

```typescript
// frontend/src/types/<domain>.ts
export interface MyResponse {
  id: string
  name: string
  newField: string | null      // ← matches Pydantic Optional[str] = None
  tags: string[]               // ← matches List[str]
  createdAt: string            // ← matches datetime (ISO 8601 wire format)
}
```

Conventions:

- **camelCase** at the wire boundary if FastAPI's response model uses `alias_generator` to camelCase. Check the model's `Config` class. **In this repo, most responses are snake_case** — keep TS field names matching the wire format (`new_field`, not `newField`) unless the backend explicitly aliases.
- **Use `interface` for object shapes**, `type` for unions / intersections / aliases.
- **Prefer `string | null` over `string | undefined`** when the backend returns `null` explicitly. Use `?` optional only when the field may be absent from the JSON entirely.

### Step 4 — Grep call sites

```bash
cd frontend
grep -rn "OldFieldName\|MyResponse\b" src/
```

Update:

- **API clients** in `frontend/src/api/<domain>.ts` if the request body or query params changed. The clients are thin fetch wrappers; usually one line per method.
- **React Query hooks** in `frontend/src/hooks/use-<domain>.ts` if the return shape changed (TanStack inference does most of the work, but `select` / `transform` callbacks may need updating).
- **Consumers** (pages + components) that read the changed field.

The TypeScript compiler will catch most consumer breakage:

```bash
cd frontend
npm run build   # tsc -b runs first; will surface type errors
```

The H2 hook (`eslint-frontend-on-edit`) provides single-file feedback as you edit.

### Step 5 — Smoke-test

```bash
# Start backend
python -m src.web

# In another shell, start frontend dev
cd frontend && npm run dev

# Open http://localhost:5173/<affected-page>, exercise the changed flow
```

Open browser DevTools → Network tab, hit the affected endpoint, confirm:

- Request body matches the TS type
- Response body matches the TS type
- No console errors about undefined fields
- The affected UI renders correctly

---

## Common drift patterns to watch for

### Pattern 1 — New optional field added to response

Backend:
```python
class JobResponse(BaseModel):
    id: str
    state: str
    created_at: datetime
    paused_at_index: Optional[int] = None  # ← NEW
```

Frontend follow-up:
```typescript
export interface JobResponse {
  id: string
  state: string
  created_at: string
  paused_at_index: number | null  // ← MIRROR
}
```

This is **safe drift** — frontend keeps working without the change, but the new field isn't visible. Mirror it when you want to consume it; track in TECHDEBT if you can't mirror immediately.

### Pattern 2 — Field renamed

Backend:
```python
class TestCase(BaseModel):
    id: str
    test_id: str       # was: case_id
    expected: str
```

Frontend follow-up: rename in `frontend/src/types/testset.ts` AND grep for every consumer:
```bash
grep -rn "case_id" frontend/src/
```

This is **breaking drift** — the frontend will silently get `undefined` for the old field name. Type errors won't fire because the wire format is `Record<string, unknown>` between TS and JSON. **Always smoke-test** after a field rename.

### Pattern 3 — Enum values changed

Backend:
```python
ResponseClass = Literal["truncated", "unrecoverable", "false_positive", "hedge"]
# was: Literal["truncated", "gibberish", "refusal", "language_error", "verbose", ...]
```

Frontend follow-up: update the union in `frontend/src/types/review.ts`. Look for hardcoded code arrays in components (e.g. `classification-bar.tsx` defines its own list of chips) — those are NOT auto-derived from the type.

This is the **highest-friction** drift case: TS will catch the missing literal in `case` statements but not in array literals. Phase 1's collapse from 7 codes to 4 hit this exact pattern.

---

## What NOT to do

- **Don't introduce codegen** (e.g. `openapi-typescript`, Zod schemas mirroring Pydantic). The benefit-to-maintenance ratio for this app size is poor; hand-maintained is the deliberate choice. If you propose codegen, do it via TECHDEBT.
- **Don't camelCase frontend fields when the backend returns snake_case.** Match the wire format exactly. If you want camelCase in components, transform at the React Query `select` callback, not at the type definition.
- **Don't use `any` to silence drift errors.** That's the type system telling you something needs updating.
- **Don't update the type and leave consumers broken.** TS will catch most cases via `noUnusedLocals`, but enum-shaped drift can slip through. Always grep + smoke-test.
- **Don't sync types and skip the API client.** If the request body changed, the client method signature must change too. The H2 lint hook catches stale parameters.
- **Don't add `as unknown as MyType` casts** to bridge type mismatches. They're a flag to fix the type definition properly.

---

## Quick reference

```
Backend changed →  src/web/api/<domain>.py            edited
                   src/web/<domain>_store.py          edited
                                ↓
Mirror in frontend → frontend/src/types/<domain>.ts   field added/renamed
                                ↓
Update API client → frontend/src/api/<domain>.ts      method signature if body changed
                                ↓
Update hook       → frontend/src/hooks/use-<domain>.ts  if return shape changed
                                ↓
Grep consumers    → grep -rn "OldField" frontend/src/
                                ↓
Build + smoke     → npm run build && npm run dev
```
