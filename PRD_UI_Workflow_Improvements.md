# PRD: gol-eval UI & Workflow Improvements

**Status:** Draft  
**Source:** Handwritten notes (IMG_1154 / IMG_1155)  
**Scope:** Frontend pages — Charts, Results, Test Sets, Configure, Execute

---

## 1. Charts Page

### 1a. Heatmap
- Fix the heat bar rendering
- Add filtering by: task type, task params, language

### 1b. Comparison View
- Add filtering by: language, task params

### 1c. Scaling
- Add log scaling toggle (on/off)
- Add filtering by: task type, params, language

---

## 2. Results Page

### 2a. Reanalyze Button
- Add a "Reanalyze" button scoped to the current results set
- Triggers re-evaluation of existing model outputs without re-running inference

### 2b. Grouping
- Add grouping by: task type, model

### 2c. Rerun with Different Params
- Add a "Rerun with different params" button
- Opens the shared **Param Override Modal** (see Test Sets §3b)
- After confirming overrides, routes directly to the Execute page with the modified config

---

## 3. Test Sets Page

### 3a. View Details Improvements
- Move the "View details" button into its own table column (not inline/overflow)
- Add a "Sample cases" tab inside the details view (mirroring the results preview pattern)
- Display **all** cases in the details view, not a truncated subset

### 3b. Regenerate with Different Params
- Add a "Regenerate with different params" button per test set
- Opens the shared **Param Override Modal** — a reusable component used by both this flow and Results §2c
- Produces a variation of the same test set with overrides for:
  - User prompt
  - System prompt (global per test set — see Configure §4b)
  - Language
- After confirming, stays on the Test Sets page with the new variant

### 3c. Grouping
- Add grouping by task type

---

## 4. Configure Page

### 4a. Number of Cases Field
- Every plugin config should expose a "Number of cases" (or equivalent) field
- This field must always appear **first** in the plugin config form

### 4b. Custom System Prompt
- Add an option to supply a custom system prompt **per test set** (global scope — not per-plugin)
- Input options:
  - Text area (inline entry)
  - File upload
  - "Add by URL" — fetch prompt from a remote URL (e.g. a GitHub Gist or raw pastebin link)

---

## 5. Execute Page

### 5a. Available Models Filter
- Add a filter/search input for the model list scoped to "Available Models" only
- Hides models that are unavailable or unconfigured

### 5b. Remember URL + API Key
- Add an option to save/remember a URL–API key pair for OpenAI-compatible API endpoints
- Persisted via **encrypted localStorage** — no backend storage, no server-side secrets
- Rationale: avoids community suspicion around credential handling; everything stays client-side

### 5c. Favorite Models Panel
- Add a "Favorite Models" side panel for quick model selection
- Add a ★ button next to each model to toggle it into/out of favorites
- Favorites panel is always visible on the Execute page for one-click selection

---

## Resolved Decisions

| # | Decision |
|---|----------|
| 1 | **Shared modal** — Rerun (§2c) and Regenerate (§3b) use the same Param Override Modal component; they differ only in post-confirm routing (Execute page vs. stay on Test Sets) |
| 2 | **System prompt scope** — per test set (global), not per plugin |
| 3 | **API key storage** — encrypted localStorage only; no backend involved |
