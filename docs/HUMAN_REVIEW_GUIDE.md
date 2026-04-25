# Human Review & Annotation Guide

> Comprehensive overview of the GoL Benchmark human-annotation subsystem — UI workflow, backend logic, persistence, and the Improvement Report contract that drives parser refactors.

---

## How to read this guide

This document has **two parts**, each with a different reader in mind. Pick your entry point:

| You are… | Read this | Skip… |
|---|---|---|
| **An annotator / triage user** — labelling responses to feed the parser-improvement loop | [Part 1 — Workflow Loop](#part-1--workflow-loop) | Part 2 (deep technical internals) |
| **A backend / SDK / agent contributor** — wiring up the system, debugging, or generating an Improvement Report for a parser refactor | [Part 2 — Technical Deep-Dive](#part-2--technical-deep-dive) | Part 1 (you can skim §1.4 + §1.6 for vocabulary) |

The two parts share vocabulary defined once in the [Glossary](#glossary). Cross-references between parts are explicit (`see §2.4`).

---

## Why this subsystem exists

A benchmark plugin's parser has one job: extract the model's final answer from a free-form response. When it fails, you want to know **how** it failed, not just **that** it failed. Counting wrong answers is cheap; understanding *which* phrasing or formatting tripped the parser is the actual work.

Human Review closes that loop:

1. A human opens incorrect / parse-error responses and **marks** the actual answer (and the patterns around it).
2. The system aggregates marks into an **Improvement Report** — a JSON artifact a coding agent can read to refactor the parser.
3. Refactored parser is re-run against the historical results (no model calls needed) — alignment ratios should rise.

Every labelled response becomes a parser test case in waiting. The mark types and response classes were designed to give an agent enough signal to write a regex without seeing the rendered UI.

---

## Glossary

| Term | Meaning |
|---|---|
| **Case** | One row in a result file: a single (test_id, language, user_style, system_style) execution producing a `raw_response`. |
| **`response_hash`** | 16-hex-char SHA256 prefix over the first 128 chars of `raw_response`. Distinguishes cases that share a `case_id` but differ in language / style / run. See [§2.2](#22-the-canonical-key). |
| **Sidecar** | Historical name for the per-result-file annotation payload. Now stored in SQLite; the term survives because the in-memory shape (`{meta, cases}`) is unchanged for the aggregator. |
| **Mark** | Generic name for any annotation primitive. v4: four author types — `spans`, `context_anchors`, `answer_keywords`, `negative_spans`. Differ in semantic role (positive vs negative) and verbosity (full span with `position`/`format` vs lightweight word). The legacy `negative_keywords[]` array is retained on the wire for back-compat; its entries fold into `negative_spans` on read. |
| **Span** | A specific mark type with extra metadata (`position`, `format`, `confidence`). Carries "this *is* the answer." |
| **Response class / classification / verdict** | One of seven multi-select tags describing the response as a whole — `hedge`, `truncated`, `gibberish`, `refusal`, `language_error`, `verbose`, `false_positive`. |
| **Improvement Report** | Aggregated JSON produced by [`build_report()`](../src/web/human_review_aggregator.py#L1942) over all annotations in selected files. Format version `"2.6"`. Consumed by parser-refactor agents. See [§2.7](#27-improvement-report-v26--the-contract). |
| **Phase 8** | The annotation-driven parser-refactor workflow established for `object_tracking` and now generalised. See [§2.9](#29-phase-8--annotation-to-refactor-workflow). |

---

# Part 1 — Workflow Loop

> **Audience:** annotators, triage users, anyone using the `/review` page to label responses.
> **You will learn:** how to enter the workspace, how to mark answers, how to classify responses, how to generate the report you'll hand to the next person (or agent).

## 1.1 What you'll do, in 30 seconds

1. Pick one or more result files on `/results`, click **Review**.
2. For each case, click words (or drag-select) in the response to **mark** where the answer is.
3. Optionally tag the response with one or more **classification chips** (`Hedge`, `Verbose`, `False-pos.`, etc.).
4. Press `→` (or click **Next**) — the draft saves and you advance.
5. After enough cases are annotated, generate the **Improvement Report** for hand-off to a parser-refactor session.

The whole UI is keyboard-first; the mouse is for marking text.

## 1.2 Entering the review workspace

Two ways in:

- **From `/results`** — select one or more rows, click the **Review** button. URL becomes `/review?files=<id>,<id>` and you land on the first eligible case.
- **By URL** — `/review?files=<id>` (single file), `/review?files=<a>,<b>&match_types=parse_error,mismatch` (filter to specific parser failure modes), `/review?files=<id>&case_id=<id>` (jump to a specific case).

Bare `/review` with no `files` param redirects to `/results` ([review.tsx:104-107](../frontend/src/pages/review.tsx#L104-L107)).

**Filter knobs** (header, all persisted in localStorage so they survive reloads):

| Knob | Default | What it does |
|---|---|---|
| **Skip empty** | on | Hides cases whose `raw_response` is empty or whitespace-only |
| **Skip correct** | off | Hides cases where the parser already got the right answer (turn this off to audit `verbose` / `false_positive` cases) |
| **Match-type filter** | all | Preset chips: `Parse errors only`, `Mismatches only`, `All wrong`, `All`. URL-driven via `?match_types=` |
| **Target language** | `en` | Default language for the 🌐 translate panel. Persisted per-session |

Active-index (which case you're on within the file-set) is also persisted — closing and reopening the same file-set lands you back where you stopped ([review.tsx:181-184](../frontend/src/pages/review.tsx#L181-L184)).

## 1.3 The two-column workspace

The screen is divided into a sticky header (case progress + filter knobs), a two-column body (35 / 65 split), and a sticky footer (classification chips + nav buttons).

```
┌─────────────────────────────────────────────────────────────┐
│  Case 12 / 47  •  qwen3:4b  •  testset_X  •  Skip-empty …  │
├─────────────────────────────────────────────────────────────┤
│                          │                                  │
│  STIMULUS PANEL          │  RESPONSE PANEL                  │
│  (35% width)             │  (65% width)                     │
│                          │                                  │
│  • System prompt         │  • Parser/Expected badges        │
│    (collapsed)           │  • Response text (markable)      │
│  • User prompt           │  • Mark chips below text         │
│  • Language badges       │  • Annotation dock + note area   │
│  • 🌐 Translate          │  • Disagreement banner           │
│                          │                                  │
├─────────────────────────────────────────────────────────────┤
│  [1 Hedge] [2 Trunc] … [7 False-pos.]    Prev | Skip | Next │
└─────────────────────────────────────────────────────────────┘
```

The response panel does the heavy lifting — every word in the rendered response is independently clickable, and drag-select works freely.

## 1.4 The four mark types

> **v4 (Phase 1) — hold-to-modify.** The modifier for each mark type is now a held letter key (A / D / Shift) rather than a browser-modifier chord (Ctrl / Alt / Shift). Hand stays on the home row; no three-limb coordination; plain drag-select commits an answer span immediately with zero dock round-trip.

Each mark type encodes a different *kind* of evidence the parser-refactor agent should consume. Use them deliberately — the report aggregator treats them differently (see [§2.7](#27-improvement-report-v26--the-contract)).

| # | Mark | Modifier (click or drag-select) | Visual | When to use |
|---|---|---|---|---|
| 1 | **Answer span** | Plain click/drag — no modifier | <span style="border-bottom:2px solid #3b82f6">solid blue</span> | The actual final answer. Carries `position` (start / middle / end) and `format` (bold / boxed / label / plain / …) auto-detected from context. Commits immediately on mouse-up. |
| 2 | **Context anchor** | Hold <kbd>A</kbd> + click/drag | <span style="border-bottom:1px dashed #818cf8">dashed indigo</span> | A phrase that *precedes* the answer (`Conclusion:`, `Therefore`, `**Answer:**`, `Висновок —`). Tells the agent "this is a high-leverage locating cue." |
| 3 | **Answer keyword** | Hold <kbd>D</kbd> + click/drag | <span style="border-bottom:1px dotted #a78bfa">dotted violet</span> | A token *inside* the answer that the parser should recognise (`drive`, `walk`, `flip`, `Conclusion`). Manual keyword distribution is higher-confidence than the auto-inferred `model_answer_distribution`. |
| 4 | **Negative** | Hold <kbd>Shift</kbd> + click/drag | <span style="border-bottom:2px solid #f43f5e">solid rose</span> | Text the parser **incorrectly extracted from**. Covers both bare distractor words (`drive` inside reasoning) and option-listing phrases (`or drive`, `walk vs drive`). The aggregator groups them in `negative_span_groups` without distinguishing sub-types. |

The `negative_keyword` mark type from v3 is gone — it folded into the single `Negative` type in Phase 1 (the distinction wasn't used in practice). Legacy sidecars with `negative_keywords[]` entries are auto-migrated on read, so no data is lost.

**Phase 2 — auto-inferred negatives.** When you mark an answer span while the parser extracted a different region, the UI automatically places a **dotted-rose negative mark** at the parser's region tagged `source: "auto_inferred"`. The dotted styling and reduced opacity (~60% of a manual negative) distinguish it at a glance. Removing it via the chip row below the response text keeps it dismissed for the rest of the draft — re-marking the answer span won't resurrect it. On case advance the flag resets. Auto-inferred marks persist to the sidecar and merge with manual negatives in the improvement-report `negative_span_groups[]`; each example record carries the `source` field for optional downstream filtering.

Modifier held-state is tracked by the [`useModifierState`](../frontend/src/hooks/use-modifier-state.ts) hook: precedence A > D > Shift; clears on `window.blur` / `document.visibilitychange` so a Cmd-Tab doesn't leave the UI stuck in "Anchor mode"; suppressed while focus is in a text field so `A` and `D` can be typed into notes.

**Visual feedback while held** — the response panel's root carries `data-modifier={"anchor" | "keyword" | "negative" | "none"}`. A subtle tint overlay (indigo / violet / rose / none) colors the panel background, and the plain-word hover preview shifts to the target mark colour so you see what the commit will produce before releasing.

**Auto-merge** — adding a mark within 1 character of an existing same-type mark merges them into one ([review.tsx `mergeOrAppendMark`](../frontend/src/pages/review.tsx)). Click two adjacent words and you get one mark spanning both — no need to drag-select carefully.

**Removal** — click any existing marked word to remove the mark.

## 1.5 Drag-select — immediate commit

In v4 there is no pending-span dock; drag-select commits on mouse-up with auto-detected `position` / `format`. The handler reads `activeModifier` at commit time, so if you release the modifier key before the mouse button the span commits as a plain answer (release-wins — intended behaviour; treat it as "oops, let me re-do this one"). The pure helpers `autoPosition` / `autoFormat` live in [span-autodetect.ts](../frontend/src/lib/span-autodetect.ts).

The browser's default behaviour for `Shift`+click is "extend the current text selection." The response panel keeps `event.preventDefault()` on `onMouseDown` when Shift is held so single-click Shift-as-negative works instead of creating a browser selection spanning the previous one.

## 1.6 The four response-class chips

Below the response are four toggleable chips — multi-select, no mutual exclusion. Numeric keys `1`–`5` + letter shortcuts `E/Q/F` toggle them ([classification-bar.tsx](../frontend/src/components/review/classification-bar.tsx)).

| Key | Code | When to use |
|---|---|---|
| `2` / `E` | `truncated` | Response cut off mid-sentence (token limit, server timeout). **Phase 3: auto-toggled at case load** when the inference-time `was_truncated` flag is set on the result entry (see below). Look, confirm, press Space to save; un-toggle if the auto-detect was wrong. |
| `3` / `Q` | `unrecoverable` | Model output unusable — gibberish, refusal, wrong language with no recoverable answer, generation loop. Collapses the old `gibberish` / `refusal` / `language_error` into one actionable bucket. |
| `4` / `F` | `false_positive` | The parser extracted the wrong token. **Coexists with a span** showing the actual answer. |
| `5` | `hedge` | Model gave an uncertain / qualified / "it depends" answer. Used sparingly. |

**Phase 3 — auto-toggled Truncated chip.** Every result entry written by `run_testset.py` or the Web UI inference path now carries an inference-time `was_truncated` boolean in the `output` dict. It's computed as `(finish_reason == "length") OR (tokens_generated >= max_tokens_used)` — all three model interfaces (Ollama / OpenAI-compatible / HuggingFace) now extract the provider's finish-reason where available. When the flag is set on a fresh case, `emptyDraft` seeds `response_classes: ["truncated"]` and marks the draft `dirty: true`. The chip renders identically to a manually-toggled one — no "(auto)" badge, no dashed border. Pressing Space confirms the flag to the sidecar; Ctrl+Space discards. Un-toggling and advancing skips the save (no content → no sidecar write) — re-visiting the case re-triggers the auto-toggle. Acceptable quirk for single-user workflow since auto-detect is authoritative.

`Extractable` is implicit when a span exists — no class needed (the old `verbose` / `verbose_correct` codes were redundant with "annotation has spans" and got dropped). `parser_ok` stays auto-inferred at report-build time from span/parser alignment.

**Important** — `false_positive` is not "instead of" a span, it's "in addition to." The annotation invariant requires *at least one of* `spans` or `response_classes`, but **both can be set**. When the parser misextracts, you want both: the span (where the answer really is) and the class (the diagnosis).

Your old sidecars still load — `_migrate_annotation()` folds legacy codes to the v4 canonical set on every read ([human_review.py `_migrate_annotation`](../src/web/api/human_review.py)):

| Legacy code | v4 code |
|---|---|
| `gibberish` | `unrecoverable` |
| `refusal` | `unrecoverable` |
| `language_error` | `unrecoverable` |
| `verbose` | (dropped — Extractable implicit) |
| `verbose_correct` | (dropped) |
| `parser_ok` | (dropped — auto-inferred) |
| `parser_false_positive` | `false_positive` |

## 1.7 Translation panel

When the response is in a language you don't read, click **Translate** in the stimulus panel header (only visible when source ≠ target language, [stimulus-panel.tsx:82-87](../frontend/src/components/review/stimulus-panel.tsx#L82-L87)). The translated text appears in a side pane.

Two modes:

- **Translate-all** — full response translated as one block.
- **Peek-translate gutter** — toggle in the response panel header. Vertical bars appear in the left gutter, one per text chunk (~500 chars). Hover a bar to peek the translation in a popover; click to pin.

**Why the translated text is `select-none`**: annotation char offsets refer to the *original* response. If you could select translated text, char offsets would point to the wrong string. The CSS class is enforced in [translation-panel.tsx:79](../frontend/src/components/review/translation-panel.tsx#L79).

Long responses are chunked on paragraph and sentence boundaries to stay within the translator's limits, and chunk boundaries preserve original char offsets so annotations remain valid regardless of which chunk you peek.

Translation provider is configurable via the `TRANSLATOR_PROVIDER` env var (`google` default, `libre` for self-hosted LibreTranslate, `mymemory` for the public service). All results are cached per `(text, source, target, provider)` tuple in an LRU.

## 1.8 Parser-disagreement workflow

The response panel always shows the **parser's extracted answer** at the top right. If found in the response text, it's highlighted with an amber dashed underline.

**Phase 2 — amber region is backend-anchored.** The amber highlight is now driven by `parsed_char_start` / `parsed_char_end` fields embedded in the result-file entry at inference time (either emitted natively by a migrated plugin parser or populated via the universal `resolve_parser_offsets` fallback). Legacy result files without these fields fall back to a client-side substring search. Non-string `parsed_answer` values (grids, dicts) land no highlight — that's intentional, not a bug.

**Phase 2 — parser-click semantics.** Click behaviour inside the amber region is now mark-type-aware:

- **Plain click** → confirms the parser's extraction by creating an answer span at the clicked word.
- **Shift+click** → toggles `false_positive` (instead of creating a negative span as elsewhere in the response text). One-keystroke classification shortcut for "parser grabbed the wrong thing."
- **Shift+drag across the amber region** → still creates a negative span over the dragged range. Drag never enters the click handler, so "drag wins over the click shortcut" is automatic.

The two disagreement affordances stack:

1. **Quiet mode** — parser badge is muted (gray) until you've engaged with the case. As soon as you mark a span or toggle a classification, the badge tones up to its real verdict colour.
2. **Persistent disagreement banner** — once you mark a span that doesn't match the parser's extraction, a rose alert appears: "Parser extracted X — your span is different." A one-click **Flag as false-positive** button toggles `false_positive` in `response_classes`. After flagging, the banner switches to a fuchsia confirmation badge.
3. **Auto-inferred negative span (Phase 2 §3.3)** — same trigger as the banner: when you mark an answer span at region Y and the parser extracted region X ≠ Y, a **dotted-rose negative mark** is synthesised at X with `source: "auto_inferred"`. The mark persists to the sidecar and feeds the improvement report's `negative_span_groups[]` alongside manual negatives (the `source` field is preserved on each example record for optional downstream filtering). The mark is rendered at ~60% opacity of a manual negative, with dotted-not-solid border, so annotators can distinguish them at a glance. Remove via the chip row below the response; removal is sticky for the rest of the draft (won't re-appear if you edit spans again on the same case). Advancing to the next case resets the dismissal flag.

You can also click **Jump to parser match** in the top-right of the response — scrolls to and flashes the parser's extraction (1.4-second amber ring fade).

## 1.9 Keyboard shortcuts

All shortcuts are disabled while focus is in an input / textarea / contenteditable / `[role=textbox]` element ([use-review-keybindings.ts `isTypingInField`](../frontend/src/hooks/use-review-keybindings.ts)).

| Key | Action |
|---|---|
| `Space` | Save dirty draft and advance; if the draft is empty, advance (skip-equivalent) |
| <kbd>Ctrl</kbd>/<kbd>⌘</kbd>+`Space` | Discard active draft and advance — deliberate friction for destructive action |
| `←` | Previous case (saves dirty draft first) |
| <kbd>Ctrl</kbd>/<kbd>⌘</kbd>+`Z` | Undo last draft edit in the current case |
| <kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>⇧</kbd>+`Z` | Redo |
| `2` / `E` | Truncated |
| `3` / `Q` | Unrecoverable |
| `4` / `F` | False-positive |
| `5` | Hedge |
| `?` | Toggle help dialog |

Removed vs v3: `S` (skip) and `ArrowRight` — Space now covers both the "save and advance" and "skip and advance" cases, and the Right-arrow-for-advance / Left-arrow-for-prev asymmetry annoyed more than it helped.

The mark-type modifier keys (A / D / Shift) are held-modifiers tracked by [`useModifierState`](../frontend/src/hooks/use-modifier-state.ts), not keybindings — see [§1.4](#14-the-four-mark-types).

## 1.10 Saving & navigation

The flow is **draft-buffered**, **save-on-advance**:

1. Marks and classifications mutate an in-memory `DraftAnnotation` keyed by `<file_id>::<case_id>::<response_hash>`.
2. The draft is marked `dirty` on any mutation. Every mutation also pushes a snapshot onto the per-case [`useUndoStack`](../frontend/src/hooks/use-undo-stack.ts) (10-step history).
3. Pressing `Space` (or the **Next** button) flushes a dirty draft via `POST /api/human-review/annotate`, then advances. Empty drafts skip the POST and just advance.
4. Pressing <kbd>Ctrl</kbd>+`Space` (or the **Discard** button) drops the draft without saving, clears the undo stack, and advances. At the last case this navigates to `/results` without a final save.
5. **Finish** on the last case saves the final dirty draft, then routes back to `/results`.

**Feedback:**

- `saved ✓` toast after a successful save (1.5s, bottom-right — `sonner`)
- `discarded` toast after <kbd>Ctrl</kbd>+`Space` with an active draft
- Save failures keep the draft in an `unsaved` set with a retry-hint toast

Undo/redo is scoped **per case** — advancing clears the stack so an undo pressed on case N+1 can never "un-save" case N. To recover from an accidental save, press `←` to return to the prior case; the saved annotation loads editable.

**Race guard** — a second `Space` press while a save is in flight is dropped (not queued) so duplicate POSTs don't hit the API ([review.tsx `savingRef`](../frontend/src/pages/review.tsx)).

**Reopening an annotated case** — `existing_annotation` is fetched from the backend and used to hydrate the draft. Spans whose char offsets fall outside the current response (sidecar contamination) are silently dropped.

## 1.11 Generating the Improvement Report

When you've annotated enough cases (rule of thumb: ≥100 cases for a parser-refactor session), it's time to hand off to the next reader.

**From the UI** — there's a **Generate Improvement Report** button on the `/results` page (or directly callable via `useImprovementReport()` in code). It calls `POST /api/human-review/report` with the selected `result_file_ids`. The response is the full v2.6 JSON.

The report opens in a 10-tab modal. Quick tour of what each tab tells *you* (the annotator):

| Tab | What you should look at |
|---|---|
| **Summary** | Top-line counts. `parser_was_correct` vs `parser_false_positive` vs `parser_missed_extractable`. Aim to get `parser_missed_extractable` to a small number — it means the parser is failing on cases the human can solve. |
| **Spans** | The richest tab. Per-(position × format) groups with example spans, prefix anchors, and **regex test rows**. Rows with green capture-quality pills (≥0.8) are drop-in regex candidates. |
| **Strategy** | Which parser strategies are firing on these cases. If you see `unknown` everywhere, your testset doesn't have parser metadata — annotate more recent runs. |
| **Languages** / **Misses** / **Answers** / **Ordering** / **Classes** / **Notes** | Cross-axis breakdowns. Most useful when annotating across multiple languages or styles. |
| **Negatives** | What the parser misextracted from — dominant failure modes the agent must filter against. |

**Data quality banner** — at the top of the dialog. If you see warnings like "every case shares one language" or "no parse strategies present," several cross-axis tabs are suppressed and won't help an agent. Annotate more diverse cases to unlock them.

The report also has **Copy JSON** and **Download JSON** buttons — that JSON is what you hand to a coding agent.

## 1.12 Common pitfalls

- **Marking the translated text** — physically prevented by `select-none` ([§1.7](#17-translation-panel)). Don't try to work around it.
- **Marking a whole reasoning chain as an answer span** — use `negative_span` instead. Answer span = "this *is* the answer." If you find yourself selecting half the response, you want the negative-span workflow.
- **Skipping classification when `false_positive` would have been right** — the parser-disagreement banner exists to remind you. The Improvement Report's `parser_was_correct` ratio depends on it.
- **Saving incomplete annotations** — there's no half-state. If you mark a span and forget to advance, it's just a draft. Press `→` or `S` to flush.
- **Annotating one language only** — many tabs in the report suppress under uniform-axis ([§2.7](#27-improvement-report-v26--the-contract)). Mix languages where possible.
- **Hash mismatch on reload** — if you see "no annotations" on a previously-annotated case, the response text changed (someone re-ran the testset). Annotations are response-locked; re-annotate. See [§2.2](#22-the-canonical-key) for the full contamination-detection story.

---

# Part 2 — Technical Deep-Dive

> **Audience:** backend / SDK / agent contributors, anyone debugging the annotation system, anyone consuming the Improvement Report programmatically.
> **You will learn:** the canonical key scheme, the API surface, the SQLite persistence layer, the full annotation data model, frontend internals, the v2.6 Improvement Report contract, and the Phase 8 refactor workflow.

## 2.1 Architecture overview

```
              ┌─────────────────────────────────────────────────────┐
              │  Browser (frontend/src)                              │
              │                                                     │
              │  /review page (review.tsx)                          │
              │   ├── StimulusPanel                                 │
              │   ├── ResponsePanel  ──┐                            │
              │   ├── ClassificationBar│  Drafts, mark-merging      │
              │   └── HelpDialog       │                            │
              │                        │                            │
              │  hooks/use-review.ts ──┘  React Query cache         │
              │                                                     │
              │  /results page (Improvement Report dialog)          │
              └────────────────────┬────────────────────────────────┘
                                   │ HTTP
              ┌────────────────────▼────────────────────────────────┐
              │  FastAPI (src/web/api/human_review.py)              │
              │                                                     │
              │   GET  /cases       POST /annotate                  │
              │   GET  /annotations DELETE /annotations[/{cid}/{h}] │
              │   POST /translate   POST /report                    │
              └──────┬─────────────────┬──────────────────┬─────────┘
                     │                 │                  │
                     │     reads       │ reads/writes     │ aggregates
                     ▼                 ▼                  ▼
       ┌─────────────────────┐  ┌─────────────────┐  ┌────────────────────────┐
       │  result_*.json.gz   │  │  AnnotationStore│  │  human_review_         │
       │  (immutable, raw    │  │  (SQLite)       │  │  aggregator.build_     │
       │   benchmark output) │  │                 │  │  report() → v2.6 JSON  │
       └─────────────────────┘  └────────┬────────┘  └────────────────────────┘
                                         │
                                         ▼
                              data/annotations.db
                              (PK: result_file_id, case_id, response_hash)
```

Result files are immutable — the canonical source of `raw_response`, `expected_answer`, `parsed_answer`, etc. Annotations are a derived layer that *points into* result files via `(result_file_id, case_id, response_hash)`. The Improvement Report joins both at read time.

## 2.2 The canonical key

### Why bare `case_id` is insufficient

A single result file routinely contains many entries with the same `test_id` (≡ `case_id`):

```
6 languages × 3 user_styles × 3 system_styles = 54 variants per test_id
```

If annotations were keyed by `case_id` alone, saving an annotation would overwrite another variant's annotation. The current key is a composite that's **unique by construction across all dimensions**.

### `response_hash` algorithm

```python
def _response_hash(raw_response: str) -> str:
    prefix = (raw_response or "")[:128].encode("utf-8", errors="replace")
    return hashlib.sha256(prefix).hexdigest()[:16]
```

— [human_review.py:100-115](../src/web/api/human_review.py#L100-L115)

**16 hex chars = 64-bit collision space.** Birthday-bound for collision is ~4 billion responses; safe for any realistic testset cardinality. The first 128 chars are enough entropy because LLM responses to the same prompt with the same parameters diverge in the first sentence.

### Legacy MD5 hash

Pre-TD-096 sidecars used 8 hex chars of MD5 over the same 128-char prefix (32-bit space, ~65k birthday-bound). The migrator (`annotation_store_migrator.py`) re-hashes legacy entries by:

1. Loading the source result file.
2. Computing the legacy MD5 for each `raw_response`.
3. Matching against the stored legacy hash.
4. Re-keying the entry with the new SHA256 hash.

If the source result file is gone (deleted), the legacy hash is preserved as an **opaque identifier** — the row still loads, just keyed by the old hash forever ([human_review.py:118-123](../src/web/api/human_review.py#L118-L123)).

### Fallback chain on load

When the API loads annotations for a case ([human_review.py:388-391](../src/web/api/human_review.py#L388-L391)):

```python
sidecar_key = f"{case_id}::{resp_hash}"
case_record = (
    annotations_by_case.get(sidecar_key)              # v2.6+ canonical
    or annotations_by_case.get(f"{case_id}::{lang}")  # v2.5 legacy
    or annotations_by_case.get(case_id, {})           # v2.0 legacy
)
```

This makes the schema additive — old annotations keep working even when the codebase moves forward.

### Contamination detection

When loading an annotation, the API recomputes the response_hash from the *current* case's response and drops the annotation if it disagrees with the stored hash ([human_review.py:396-405](../src/web/api/human_review.py#L396-L405)). This catches the case where a result file was re-run (responses changed) but the annotation sidecar wasn't deleted — the annotation now refers to a different response and would be misleading.

The frontend additionally drops spans whose `char_start`/`char_end` fall outside the current `raw_response.length` ([review.tsx:37-42](../frontend/src/pages/review.tsx#L37-L42)) — a second line of defence against char-offset drift.

## 2.3 Backend API surface — `/api/human-review/*`

Router defined in [src/web/api/human_review.py](../src/web/api/human_review.py). All routes mounted under `/api/human-review`.

### Pydantic models

| Model | Fields |
|---|---|
| `AnnotationSpan` | `text: str`, `char_start: int ≥ 0`, `char_end: int ≥ 0`, `position: "start"\|"middle"\|"end"`, `format: "bold"\|"boxed"\|"label"\|"plain"\|"other"`, `confidence: Optional["high"\|"medium"\|"low"]` |
| `MarkSpan` | `text: str`, `char_start: int ≥ 0`, `char_end: int ≥ 0` — used for context_anchors / answer_keywords / negative_spans / negative_keywords |
| `Annotation` | `spans: [AnnotationSpan]`, `response_classes: [str]`, `response_class: Optional[str]` (legacy, auto-converted on save), `annotator_note: str`, `timestamp: Optional[str]`, `context_anchors: [MarkSpan]`, `answer_keywords: [MarkSpan]`, `negative_spans: [MarkSpan]`, `negative_keywords: [MarkSpan]` |
| `AnnotateRequest` | `result_file_id: str`, `case_id: str`, `annotation: Annotation`, `response_hash: Optional[str]`, `language: Optional[str]` |
| `ReportRequest` | `result_file_ids: [str]` (min_length=1) |
| `TranslateRequest` | `text: str`, `source_lang: Optional[str]`, `target_lang: str` (default `"en"`) |

### Endpoints

#### `GET /cases`
Load review-ready cases for one or more result files.

| Query | Type | Default | Notes |
|---|---|---|---|
| `file_ids` | comma-separated str | (required) | Filenames of result files |
| `skip_correct` | bool | `false` | Hide cases where parser was correct |
| `skip_empty` | bool | `true` | Hide empty/whitespace responses |
| `match_types` | comma-separated str | (none) | Filter to specific `parser_match_type` values |

**Response shape**:
```json
{
  "plugin": "carwash",
  "plugins": ["carwash"],
  "mixed_plugins": false,
  "total": 47,
  "total_annotated_in_sidecars": 128,
  "cases": [ReviewCase, …]
}
```

Each `ReviewCase` contains the projected case context (`case_id`, `raw_response`, `parsed_answer`, `expected`, `parser_match_type`, `language`, `user_style`, `system_style`, etc.) plus `existing_annotation` (sidecar-shaped Annotation if present), `response_hash`, and `result_file_id`.

The backend resolves files, loads them as gzipped JSON, projects each entry into a ReviewCase, calls `_load_annotations_from_store()` for each file, and overlays annotations using the fallback chain in [§2.2](#22-the-canonical-key). Contamination check runs here.

Errors: `400` on missing `file_ids`, `500` on load failure.

#### `POST /annotate`
Upsert a single case annotation. Body is `AnnotateRequest`.

**Side effects** (in order):

1. **Schema migration on input** — `_migrate_annotation()` runs (`response_class` → `response_classes`, `verbose_correct` → `verbose`, `parser_false_positive` → `false_positive`, drop `parser_ok`).
2. **Invariant validation** — at least one of `spans` or `response_classes` must be non-empty. Error: `400 "Annotation must have either spans or response_classes"` ([human_review.py:438-441](../src/web/api/human_review.py#L438-L441)).
3. **Class validation** — every `response_class` must be in the canonical seven ([human_review.py:37-50](../src/web/api/human_review.py#L37-L50)).
4. **Result-entry resolution** — find the source result entry by iterating `results[]` and matching:
   - `case_id == case_id` (always)
   - **AND** if `response_hash` provided: `_response_hash(raw_response) == response_hash` (most specific)
   - **else** if `language` provided: `prompt_metadata.language == language`
   - **else** first match by `case_id`
5. **Context extraction** — `_extract_context_windows()` builds `context_windows[]` (120 chars before/after each span + full sentence) and stores it on the case record ([human_review.py:222-252](../src/web/api/human_review.py#L222-L252)).
6. **File-level meta** — `plugin` inferred via majority vote on `task_type` of successful results, `created_at` set on first save, `updated_at` set every save.
7. **Persist** — `store.save_case()` does an atomic SQLite upsert.

Errors: `404` on missing result file or case, `400` on validation failure.

#### `GET /annotations/{result_file_id}`
Fetch the full sidecar-shaped annotation payload for a file. Returns `{meta: {...}, cases: {...}}` or empty dict if no annotations exist.

#### `DELETE /annotations/{result_file_id}`
Wipe all annotations for a result file. Idempotent — returns `{status: "ok", deleted: bool, removed_count: int}` even if nothing was stored.

#### `DELETE /annotations/{result_file_id}/{case_id}/{response_hash}`
Remove a single row. Idempotent. Per-row delete resolves [TD-095](../TECHDEBT.md).

#### `POST /translate`
Body is `TranslateRequest`. Calls `translate_text()` from `src/web/translation.py`. Returns `{translated, provider, source_lang, target_lang}`.

Errors: `400` on empty text, `503` on provider error.

Provider routing is via the `TRANSLATOR_PROVIDER` env var — `google` (default, no key), `libre` (self-hosted, configurable URL via `LIBRETRANSLATE_URL` and key via `LIBRETRANSLATE_API_KEY`), or `mymemory` (public). Language tags are normalised before dispatch — `ua` → `uk`, `zh` → `zh-CN` (caller can pass `zh-tw` explicitly). When source equals target the call short-circuits with `provider="noop"`. Results are LRU-cached on `(text_sha256, text, source, target, provider)` with `maxsize=2048`.

#### `POST /report`
Body is `ReportRequest`. Returns the full v2.6 Improvement Report JSON.

Loads both annotation sidecars and source result payloads; passes the `result_payloads_by_file` map to `build_report()` so legacy sidecars (pre-v2.20.1) get backfilled context (language, parse_strategy, context_windows). Without backfill, missing fields degrade to `unknown` buckets in the report.

### Route ordering

All specific routes are declared **before** any path-param route to avoid the FastAPI catch-all bug where `/{filename}` would match `cases` / `annotate` / `report` as filenames ([human_review.py:9-11](../src/web/api/human_review.py#L9-L11)).

## 2.4 SQLite persistence layer (`AnnotationStore`)

### Why migrate from gzipped sidecars

Pre-Phase-2, annotations lived at `data/annotations/<stem>.json.gz`. Problems:

- **Atomic upserts required temp + rename** for every save.
- **Single-row deletes meant rewriting the whole gzip**.
- **`has_annotations` checks** had to read the whole file just to see if it was non-empty.
- **Concurrent saves** (multiple browser tabs) were racy.

Phase 2 (this branch, uncommitted) replaces the sidecar with SQLite. The on-disk file is `data/annotations.db`. The migrator (`annotation_store_migrator.py`) is a one-shot conversion — sidecars move to `data/annotations.bak/` for rollback.

### Schema

[`db_migrations/002_annotations.sql`](../src/web/db_migrations/002_annotations.sql):

```sql
CREATE TABLE IF NOT EXISTS annotations (
    result_file_id    TEXT NOT NULL,
    case_id           TEXT NOT NULL,
    response_hash     TEXT NOT NULL,
    -- Per-case context (denormalised from result file at save time)
    response_length   INTEGER,
    parser_match_type TEXT,
    parser_extracted  TEXT,
    expected          TEXT,
    language          TEXT,
    user_style        TEXT,
    system_style      TEXT,
    parse_strategy    TEXT,
    parse_confidence  TEXT,
    model_name        TEXT,
    -- v3 annotation payload (JSON arrays of dicts)
    spans             TEXT NOT NULL DEFAULT '[]',
    response_classes  TEXT NOT NULL DEFAULT '[]',
    context_anchors   TEXT NOT NULL DEFAULT '[]',
    answer_keywords   TEXT NOT NULL DEFAULT '[]',
    negative_spans    TEXT NOT NULL DEFAULT '[]',
    negative_keywords TEXT NOT NULL DEFAULT '[]',
    context_windows   TEXT NOT NULL DEFAULT '[]',
    annotator_note    TEXT NOT NULL DEFAULT '',
    annotation_ts     TEXT,
    -- File-level denormalised meta (copied onto every row of a file)
    plugin            TEXT,
    annotated_by      TEXT,
    file_created_at   TEXT,
    file_updated_at   TEXT,
    PRIMARY KEY (result_file_id, case_id, response_hash)
);
CREATE INDEX idx_annotations_result_file ON annotations(result_file_id);
CREATE INDEX idx_annotations_updated_at  ON annotations(file_updated_at);
```

Key design choices:

- **Composite PK** = `(result_file_id, case_id, response_hash)` — no surrogate id.
- **JSON1 columns** for the v3 mark arrays — SQLite has JSON1 if you ever need to query into them, but we never do (cheap read-the-whole-row). Avoids child tables and the join overhead they'd impose.
- **File-level meta is denormalised onto every row** — costs a few bytes per row, saves a separate `annotation_files` table. Updated by `_propagate_meta()` ([annotation_store.py:209-222](../src/web/annotation_store.py#L209-L222)) inside the same transaction as the upsert.

### `save_case()` flow

[annotation_store.py:124-151](../src/web/annotation_store.py#L124-L151):

```python
with transaction(self._conn):
    # 1. Upsert this row
    self._conn.execute(
        "INSERT INTO annotations (...) VALUES (...) "
        "ON CONFLICT(result_file_id, case_id, response_hash) DO UPDATE SET ...",
        values,
    )
    # 2. Propagate file-level meta onto every row of the file
    self._propagate_meta(result_file_id, meta)
```

The `transaction()` context manager wraps both in a single SQLite transaction so they commit-or-rollback atomically.

### Migrator (`annotation_store_migrator.py`)

`migrate_sidecar_files_to_db(annotations_dir, backup_dir)` — one-shot, idempotent ([annotation_store_migrator.py:32-120](../src/web/annotation_store_migrator.py#L32-L120)):

1. Scan `annotations_dir/*.json.gz`.
2. For each sidecar: parse JSON, extract `meta`, iterate `cases`.
3. For each case: call `_migrate_one_case()`:
   - Apply schema migrations (`_migrate_annotation()`).
   - Try to rehash from MD5 → SHA256 via the source result file.
   - If source is missing, keep the legacy hash as opaque identifier.
   - Build the case record and call `store.save_case()`.
4. Move the original sidecar to `backup_dir/`.

Backwards compatibility is exhaustive: scalar `response_class` → `response_classes` array, old class names renamed, `parser_ok` dropped, missing v3 mark-type arrays initialised to `[]`.

### Other store methods

- `load_for_file(result_file_id) → {meta, cases} | None` — returns the sidecar-shaped dict the aggregator already knew how to consume.
- `delete_file(result_file_id) → int` — bulk delete by file.
- `delete_case(result_file_id, case_id, response_hash) → bool` — single row.
- `list_annotated_result_files() → set[str]` — which files have any annotations.
- `has_annotations(result_file_id) → bool` — single-row check via `LIMIT 1`. Used by `/api/results` summaries.

## 2.5 The full annotation data model

### File-level metadata (`meta` dict, same across all rows in a file)

| Field | Type | Notes |
|---|---|---|
| `result_file` | str | Filename |
| `plugin` | str | Inferred task_type via majority vote on results |
| `annotated_by` | str | Default `"human"` |
| `created_at` | str | ISO 8601, set on first save |
| `updated_at` | str | ISO 8601, set on every save |
| `annotated_count` | int | Rows with non-empty `spans` OR `response_classes` |
| `skipped_count` | int | Rows with neither (file-level — currently unused on save side) |

### Case-level context (top-level fields of the `cases[<key>]` dict)

| Field | Type | Notes |
|---|---|---|
| `case_id` | str | `test_id` from the result file |
| `response_length` | int | `len(raw_response)` at annotation time |
| `response_hash` | str | 16-hex SHA256 (or 8-hex legacy MD5) |
| `parser_match_type` | str | `correct`, `mismatch`, `parse_error`, `localized_match`, etc. |
| `parser_extracted` | str \| None | What the parser pulled out |
| `expected` | str \| None | Ground truth from `task_params` or evaluation |
| `language` | str | Default `"en"` |
| `user_style` | str \| None | `minimal` / `casual` / `linguistic` |
| `system_style` | str \| None | `analytical` / `casual` / `adversarial` |
| `parse_strategy` | str | Plugin parser's strategy name; `unknown` if missing |
| `parse_confidence` | str \| None | Confidence score from output |
| `model_name` | str \| None | LLM model |
| `context_windows` | [dict] | Auto-built per span: `{text, char_start, char_end, before, after, sentence}` |

### Nested `annotation` dict (the actual user input)

| Field | Type | Notes |
|---|---|---|
| `spans` | `[AnnotationSpan]` | Full spans with `position` + `format` + `confidence` |
| `response_classes` | `[str]` | Multi-select, validated against `_RESPONSE_CLASSES` |
| `context_anchors` | `[MarkSpan]` | Lightweight: `text` + `char_start` + `char_end` (+ optional `source`) |
| `answer_keywords` | `[MarkSpan]` | "" |
| `negative_spans` | `[MarkSpan]` | **Phase 2**: MarkSpan may carry `source: "manual" \| "auto_inferred"`. Absent = implicit `"manual"`. Auto-inferred entries are synthesised on parser-disagreement (see §1.8). |
| `negative_keywords` | `[MarkSpan]` | v4: no longer authored by the UI; legacy entries fold into `negative_spans` on read. Column kept for back-compat; cleanup tracked as TD-115. |
| `annotator_note` | str | Free-form, optional |
| `timestamp` | str \| None | ISO 8601, set on save if not provided |

### Valid response classes (v4 — Phase 1)

```python
{"hedge", "truncated", "unrecoverable", "false_positive"}
```

— [human_review.py](../src/web/api/human_review.py)

Rename/drop map applied automatically on read AND on save:

| Legacy code | v4 mapping |
|---|---|
| `gibberish` | renamed → `unrecoverable` |
| `refusal` | renamed → `unrecoverable` |
| `language_error` | renamed → `unrecoverable` |
| `parser_false_positive` | renamed → `false_positive` |
| `verbose_correct` | dropped |
| `verbose` | dropped |
| `parser_ok` | dropped (auto-inferred from span/parser alignment) |

Deduplication: if multiple legacy codes fold to the same v4 code (e.g. `["gibberish", "refusal"]`), the result is deduped so `response_classes` never contains a repeat. Old sidecars continue to load via `_migrate_annotation()` invoked from `_load_annotations_from_store`.

## 2.6 Frontend internals

### React Query hooks

All in [`frontend/src/hooks/use-review.ts`](../frontend/src/hooks/use-review.ts):

| Hook | Query key | Cache settings | Invalidates on success |
|---|---|---|---|
| `useReviewCases(fileIds, opts)` | `["review-cases", sortedFileIds, skipCorrect, skipEmpty, sortedMatchTypes]` | `staleTime: Infinity`, `refetchOnWindowFocus: false` | (read-only) |
| `useSaveAnnotation()` | (mutation) | — | `["results"]` |
| `useAnnotations(result_file_id)` | `["annotations", result_file_id]` | (default) | (read-only) |
| `useImprovementReport(fileIds, enabled)` | `["improvement-report", sortedFileIds]` | `refetchOnWindowFocus: false` | (read-only — re-fetched on demand) |
| `useDeleteAnnotations()` | (mutation) | — | `["results"]`, `["annotations", filename]`, **`["review-cases"]`** |
| `useTranslation(text, source, target, enabled)` | `["translate", source, target, text]` | `staleTime: Infinity`, `retry: false` | (read-only) |

**Why `useReviewCases` has `staleTime: Infinity`**: the case list is a snapshot. Background refetching mid-session would change `activeIndex` semantics and could even reorder cases under the user. The cost is that you must explicitly invalidate `["review-cases"]` when annotations change in a way that affects what's shown — only `useDeleteAnnotations` does this (it nukes everything for a file, which definitely affects review-cases).

**Why `useImprovementReport` does NOT have `staleTime: Infinity`**: the report changes whenever annotations change. The default `staleTime` (5 min for tanstack v5) is acceptable since users explicitly trigger generation and the cache key is per-file-set.

### Draft state machine

Lives entirely in `ReviewWorkspace` ([review.tsx:124+](../frontend/src/pages/review.tsx#L124)):

```
                         ┌──────────────────┐
            on mount /   │                  │
            case change  │   emptyDraft()   │── seeded from existing_annotation
        ────────────────►│                  │   (with char-offset clamping)
                         └────────┬─────────┘
                                  │
                                  │ user marks/classifies
                                  ▼
                         ┌──────────────────┐
                         │  draft (dirty)   │
                         └────────┬─────────┘
                                  │
                          press → │   press S
                                  │       │
                       ┌──────────▼─┐   ┌─▼─────────┐
                       │ saveDraft()│   │ skip      │
                       │ → POST     │   │ (advance, │
                       │   /annotate│   │  no save) │
                       └──────────┬─┘   └─┬─────────┘
                                  │       │
                                  ▼       ▼
                              advance to next case
```

Key data: `drafts: Record<caseKey, DraftAnnotation>` ([review.tsx:206](../frontend/src/pages/review.tsx#L206)), `unsaved: Set<caseKey>` (failed saves), `savedIds: Set<caseKey>` (confirmed saves).

`caseKey()` ([review.tsx:92-94](../frontend/src/pages/review.tsx#L92-L94)) is `${result_file_id}::${case_id}::${response_hash}` — uniqueness across all variants.

### Mark click vs drag-select

[response-panel.tsx:490-583](../frontend/src/components/review/response-panel.tsx#L490-L583):

- `handleWordClick(start, end, text, event)` — every word in the response is wrapped in a clickable element. Modifier detection branches into the five mark types.
- `handleMouseUp(event)` — fires on drag-select. Reads `window.getSelection()`, validates the range is inside the response container, computes char offsets via `range.cloneRange()` + `toString().length`, then either:
  - **With modifiers**: directly creates the appropriate mark, clears the selection.
  - **Without modifiers**: opens a `PendingSpan` that the dock displays for confirmation.

The `mergeOrAppendMark()` callback in `ReviewWorkspace` ([review.tsx:260-279](../frontend/src/pages/review.tsx#L260-L279)) does the auto-merge math (within 1 char gap → merge by extending `char_start`/`char_end`).

### Selection suppression

[response-panel.tsx:706-718](../frontend/src/components/review/response-panel.tsx#L706-L718):

```tsx
onMouseDown={(e) => {
  if (e.shiftKey || e.altKey) e.preventDefault()
}}
onContextMenu={(e) => {
  if (e.shiftKey || e.altKey || e.ctrlKey || e.metaKey) e.preventDefault()
}}
```

Without these, browser-native shift-extend / context-menu would fire instead of our click handler.

### Translation chunking

[`frontend/src/lib/translate-chunks.ts`](../frontend/src/lib/translate-chunks.ts):

1. Split on paragraph boundaries (`\n{2,}`).
2. Paragraphs > 500 chars: split on sentence-end punctuation (`.!?` + CJK), greedy re-group into ~500-char chunks.
3. Sentence > 500 chars (no punctuation): hard-split at 500-char intervals.

Each chunk stores its original `start` / `end` offset into the full response. The translation panel renders chunks back into a continuous block with `select-none` so annotation char offsets remain valid even when peek-translating an arbitrary sub-region.

## 2.7 Improvement Report v2.7 — the contract

### Why this exists

The Improvement Report is **the agent-facing artifact**. Annotators produce it; coding agents read it to refactor parsers. Its shape has iterated rapidly across v2.1 → v2.7 and every section is engineered to give an agent enough signal to make a decision without re-running code.

Top-level entry point: `build_report()` ([human_review_aggregator.py](../src/web/human_review_aggregator.py)). Format constant: `REPORT_FORMAT_VERSION = "2.7"`.

**What v2.7 changed** (Phase 1 — spec [ANNOTATION_UI_REDESIGN.md](../ANNOTATION_UI_REDESIGN.md)):

- `negative_span_groups[]` no longer carries `mark_type` — the negative_span / negative_keyword distinction collapsed at the UI layer. Legacy v2.6 reports on disk still carry the field; consumers should null-guard it.
- `summary.response_class_counts` reports only the v4 canonical codes (`truncated` / `unrecoverable` / `false_positive` / `hedge` / auto-inferred `parser_missed`). Legacy codes folded on read.
- No other shape changes. Old tooling that reads v2.6 reads v2.7 unchanged except for the dropped `mark_type` field.

### Top-level schema

| Field | Always present | What an agent does with it |
|---|---|---|
| `format_version` | yes | Schema sentinel (`"2.6"`) |
| `source_files` | yes | Filenames the annotations came from — traceability |
| `summary` | yes | Counts: `total_cases`, `annotated`, `skipped`, `parser_was_correct`, `parser_false_positive`, `parser_missed_extractable`, `true_unparseable`. `summary.response_class_counts` folded in when non-zero |
| `false_positive_rate` | yes | Mirrored at top for prominence |
| `parser_span_alignment` | yes | `aligned_with_parser` / `misaligned` / `no_output` split. **Always pair with `parser_missed_extractable`** — a fully aligned `parser_extracted` still lands in `missed_extractable` when the annotator used spans-only workflow |
| `data_quality` | yes | `warnings[]` + `suppressed_sections[]`. **Read first** — tells you which sections to trust |
| `model_answer_distribution` | yes | Histogram of normalised model text — what the model *actually* chose |
| `model_answer_variants` | yes | Raw variants per normalised bucket — case / markdown / phrasing variation inside each answer class |
| `span_groups` | yes | **Primary regex-candidate signal.** Per-(position × format) groups with structural ratios, prefix anchors, label taxonomy, regex test harness |
| `answer_when_missed` | when not suppressed | Distractor distribution under uniform_expected suppression |
| `strategy_breakdown` | when not suppressed | Failure-mode attribution per parser strategy. Suppressed under `no_parse_strategy` |
| `long_tail_groups` | when present | Compact `{position, format, count, example}` stubs for groups with `count < 4`. Only emitted when at least one rich group exists ([§2.7.3](#273-the-long-tail-collapse-rule-v25)) |
| `ordering_hints` | when non-empty | Strategy-reordering recommendations |
| `annotator_notes` | when non-empty | Free-form notes from annotators, with case_id |
| `negative_span_groups` | when present (v2.6) | Patterns the parser must FILTER. See [§2.7.5](#275-negative-mark-semantics) |
| `manual_keyword_distribution` | when present (v2.6) | High-confidence answer-keyword distribution from `answer_keywords[]` annotations |
| `context_anchor_groups` | when present (v2.6) | High-leverage locating phrases from `context_anchors[]` annotations |
| `language_breakdown` | when not suppressed | Per-language case counts |
| `config_breakdown` | when not suppressed | Per-system_style |
| `user_style_breakdown` | when not suppressed | Per-user_style |

### 2.7.1 Per-span-group structure

Each entry in `span_groups[]` ([human_review_aggregator.py:1521-1537](../src/web/human_review_aggregator.py#L1521-L1537)):

```json
{
  "position": "start" | "middle" | "end",
  "format": "bold" | "italic" | "plain" | "label" | "boxed" | "header" | "strikethrough" | "other",
  "count": 12,
  "languages": ["en", "uk"],
  "example_spans": [
    {
      "text": "drive",
      "before": "…the recommendation is to ",
      "after": ".",
      "sentence": "Therefore the recommendation is to drive.",
      "case_id": "carwash_042",
      "language": "en",
      "parser_extracted": "walk",
      "parser_match_type": "mismatch"
    }, …  // up to 5
  ],
  "suggested_strategy": "label_line",       // FORMAT_TO_STRATEGY map
  "confidence": "high" | "medium" | "low",  // anchor ratio + group size
  "missed_by_existing": true,
  "structural_ratios": {
    "line_start": 0.83,
    "paragraph_start": 0.50,
    "list_marker": 0.0,
    "label_colon": 0.92,
    "bold_wrap": 0.0,
    "quote_wrap": 0.0,
    "answer_label_match": 0.92
  },
  "prefix_anchors": [
    {"phrase": "Recommendation:", "count": 11, "ratio": 0.92, "type": "label"},
    {"phrase": "Therefore", "count": 7, "ratio": 0.58, "type": "phrase"},
    …  // up to 5
  ],
  "label_taxonomy": [
    {"label": "Recommendation", "count": 11},
    {"label": "Conclusion", "count": 1}
  ],
  "suggested_regex": [
    {
      "pattern": "(?i)(?:recommendation|conclusion)\\s*[:：]\\s*([^.\\n]+?)(?:[.\\n]|$)",
      "kind": "merged_label_disjunction",
      "support": 12,
      "anchor_phrase": null,
      "participating_atoms": ["recommendation", "conclusion"]
    }, …  // up to 4, priority order
  ],
  "regex_test": [   // sorted by match_rate desc
    {
      "pattern": "(?i)(?:recommendation|conclusion)\\s*[:：]\\s*([^.\\n]+?)(?:[.\\n]|$)",
      "kind": "merged_label_disjunction",
      "support": 12,
      "match_rate": 1.0,
      "matched_count": 12,
      "total": 12,
      "capture_exact_rate": 0.25,
      "capture_contains_rate": 0.92,
      "sample_captures": [
        {"case_id": "carwash_042", "captured": "Definitively walk to the carwash",
         "annotated": "walk", "exact_match": false, "aligned": true},
        …  // up to 3
      ]
    }, …
  ]
}
```

**Prefix anchor `type` taxonomy** (load-bearing — used to rank candidates):

| Type | Meaning |
|---|---|
| `label` | Anchor ends with `:` or `：`. Examples: `**Answer:**`, `Recommendation:`, `Conclusion:` |
| `format` | Anchor ends with markdown marker (`**`, `__`, `~~`, `*`, `_`, `\``) or emoji (`✅`, `✓`, `➜`, `→`, `▶`, `➤`, `•`). Format-anchored without explicit label |
| `phrase` | Flowing text with no locating cue. Lowest-confidence anchor |

**Candidate `kind` priority** (highest → lowest):

1. `merged_label_disjunction` — multiple label atoms combined into one regex (`(?i)(?:recommendation\|conclusion)…`). Best signal when 2+ distinct labels appear.
2. `context_anchor` — anchored on top 1-2 prefix phrases.
3. `format_only` — distinctive format wrapper (e.g. all spans are bold).
4. `text_pattern` — fallback from span-text longest-common-prefix.

**Low-support filter** ([human_review_aggregator.py:1034-1064](../src/web/human_review_aggregator.py#L1034-L1064)): candidates with `support < 2` AND `support/group_size < 0.1` are dropped post-harness — except `format_only` (safety net) and compile errors (bug signal). Candidates that don't fire (`match_rate < 0.1` AND `capture_contains_rate < 0.1`) are also dropped.

### 2.7.2 `match_rate` ≠ capture quality (load-bearing)

The single most important distinction in the report. A pattern can fire 100% and still be useless.

| Field | Meaning |
|---|---|
| `match_rate` | Fraction of cases where the regex *fires at all* |
| `capture_exact_rate` | Fraction where `normalize(capture) == normalize(annotated_span)` |
| `capture_contains_rate` | Fraction where capture and annotated span align via single-word inclusion. **The actual usefulness measure.** |

Classic failure mode: `(?i)recommendation:\s*([^.\n]+?)(?:[.\n]|$)` matches every "Recommendation:" line (`match_rate=1.0`) but captures `Definitively walk to the carwash` instead of `walk` (`capture_contains_rate=0.3`). Agent reads "fires correctly but grabs the wrong substring" and adds post-processing.

The frontend `CaptureQualityPill` tones on `capture_contains_rate`: **green ≥0.8**, amber ≥0.5, red <0.5.

### 2.7.3 The long-tail collapse rule (v2.5)

`_split_long_tail()` ([human_review_aggregator.py:1541-1572](../src/web/human_review_aggregator.py#L1541-L1572)):

```python
_LONG_TAIL_THRESHOLD = 4

def _split_long_tail(span_groups):
    has_rich = any(g["count"] >= _LONG_TAIL_THRESHOLD for g in span_groups)
    if not has_rich:
        return span_groups, []   # small session — keep everything rich
    rich = [g for g in span_groups if g["count"] >= _LONG_TAIL_THRESHOLD]
    long_tail = [_compact_stub(g) for g in span_groups if g["count"] < _LONG_TAIL_THRESHOLD]
    return rich, long_tail
```

Why: in a small focused session every group might be `count < 4`. Collapsing them all to long-tail erases the entire signal. The guard says **"only collapse when at least one group survives the threshold."**

Long-tail entries strip `structural_ratios` / `prefix_anchors` / `regex_test` (no statistical meaning at n ≤ 3) but retain `position`, `format`, `count`, and one `example`.

### 2.7.4 Suppressed sections vs missing sections

`data_quality.warnings[]` and `data_quality.suppressed_sections[]` are how the report tells you "this section is intentionally absent because it would be noise."

Warning codes ([human_review_aggregator.py:1687-1771](../src/web/human_review_aggregator.py#L1687-L1771)):

| Code | Triggered when | Suppresses |
|---|---|---|
| `no_parse_strategy` | >90% of cases have `parse_strategy=="unknown"` | `strategy_breakdown` |
| `uniform_language` | All cases share one language | `language_breakdown` |
| `uniform_expected` | All cases expect the same answer | `answer_when_missed.by_expected` (and the whole `answer_when_missed` section if all sub-blocks are empty) |
| `uniform_system_style` | Single bucket | `config_breakdown` |
| `uniform_user_style` | Single bucket | `user_style_breakdown` |

**Reader contract**: if a section is missing from the JSON, check `data_quality.suppressed_sections[]`. Absent without warning = no signal observed (e.g. no negative spans annotated). Absent with warning = single-bucket, statistically pointless.

### 2.7.5 Negative-mark semantics

`negative_span_groups[]` (v2.7, [human_review_aggregator.py `_collect_negative_records` + `_negative_span_analysis`](../src/web/human_review_aggregator.py)):

```json
[
  {
    "text": "or drive",
    "normalized_text": "or drive",
    "count": 7,
    "example_negatives": [
      {
        "text": "or drive",
        "before": "…should you walk ",
        "after": " to the carwash?",
        "case_id": "carwash_017",
        "language": "en",
        "correct_span": "drive",
        "parse_strategy": "first_sentence"
      }
    ]
  }
]
```

**v2.7 changes** (Phase 1): the `mark_type` field is gone. In v2.6 it distinguished `negative_span` ("bare distractor word the parser extracted from") vs `negative_keyword` ("option-listing/comparison phrase the parser must filter"). The distinction was load-bearing in the agent contract but not used by annotators in practice, so Phase 1 collapsed the two types into a single `Negative` author surface. The aggregator now groups all negative marks uniformly in `negative_span_groups[]`.

Legacy v2.6 reports on disk still carry `mark_type` on each group; v2.7 consumers must null-guard. The `_collect_negative_records` helper defensively folds both `negative_spans[]` and legacy `negative_keywords[]` at report-build time, so un-migrated in-flight sidecars still produce a single-typed output.

**Phase 2 addition — `source` field on example records.** Each `example_negatives[]` entry now carries `source: "manual" | "auto_inferred"` (absent on pre-Phase-2 reports → defaulted to `"manual"` at read time). Auto-inferred negatives are synthesised by the UI when the annotator marks an answer span while the parser extracted a different region (see §1.8). Groups themselves merge auto and manual uniformly — a single group may contain both source types. Agents that want manual-only signal can filter `example_negatives` by `source == "manual"`; the default assumption is that merging is the right call (parser-grabbed-the-wrong-spot is the same signal regardless of whether a human clicked it or the UI derived it).

**Agent action** — cross-reference `correct_span` to see what the parser should have won; cross-reference `context_anchor_groups[]` to see which labels precede the right answers. Negative groups with high `count` are always worth reading; they're the parser's most consistent failure modes.

These feed parser-refactor signal differently than positive spans: positive = "find pattern X"; negative = "avoid pattern Y / don't extract token Z when context C is present."

### 2.7.6 Per-helper aggregator map

The helpers in `human_review_aggregator.py` and what they produce:

| Helper | Lines | Produces |
|---|---|---|
| `_session_summary` | 1610s | `summary` + `false_positive_rate` |
| `_collect_span_records` | – | Flattened span records joined with case context |
| `_span_analysis` | 1403–1538 | `span_groups[]` (pre-collapse) |
| `_split_long_tail` | 1541–1572 | `(rich, long_tail)` partition |
| `_prefix_anchors_per_group` | 856–919 | `prefix_anchors[]` per group |
| `_context_anchored_regex` | 1067–1161 | Up to 4 candidate regexes per group |
| `_merged_label_disjunction` | 983–1031 | Synthesises multi-label disjunction when ≥2 label atoms |
| `_filter_candidates` | 1034–1064 | Drops weak candidates post-harness |
| `_regex_test_harness` | 1305–1400 | `regex_test[]` rows with `match_rate` / `capture_*_rate` / `sample_captures` |
| `_data_quality` | 1687–1771 | `warnings[]` + `suppressed_sections[]` |
| `_response_class_counts` | 1662–1685 | Folded into `summary.response_class_counts` |
| `_model_answer_stats` | 1247–1304 | `model_answer_distribution` + `model_answer_variants` |
| `_collect_negative_records` | 1801–1845 | Records joined with case context for negative analysis |
| `_negative_span_analysis` | 1848–1881 | `negative_span_groups[]` |
| `_answer_keyword_distribution` | 1884–1903 | `manual_keyword_distribution` |
| `_context_anchor_groups` | 1906–1934 | `context_anchor_groups[]` |
| `_axis_breakdown` | – | `language_breakdown` / `config_breakdown` / `user_style_breakdown` |
| `_strategy_breakdown` | – | `strategy_breakdown` |
| `_answer_when_missed` | – | `answer_when_missed` with by_expected / by_distractor / by_pair |
| `_ordering_hints` | – | `ordering_hints[]` |
| `_collect_notes` | – | `annotator_notes[]` |
| `_parser_span_alignment` | – | `parser_span_alignment` |

### 2.7.7 Open issues

- **[TD-113](../TECHDEBT.md)** — `strategy_breakdown.parser_ok` is back-filled from manual `parser_ok` annotations rather than auto-inferred from alignment data. Agents see `0` for every strategy even when global `alignment_ratio` is high. Fix: cross-reference each case's `parse_strategy` with its alignment status to populate per-strategy correct counts.

## 2.8 Improvement Report dialog — the 10 tabs

[`frontend/src/components/review/improvement-report-dialog.tsx`](../frontend/src/components/review/improvement-report-dialog.tsx). Tabs render conditionally on the underlying JSON section being present.

| # | Tab | JSON section consumed | What it shows |
|---|---|---|---|
| 1 | **Summary** | `summary`, `parser_span_alignment`, `false_positive_rate` | Top-line stat cards, parser-missed split (aligned / misaligned / no-output) |
| 2 | **Spans** | `span_groups[]`, `long_tail_groups[]` | Per-group cards: position/format header, examples, prefix-anchor chips (type-coloured), regex-test harness rows |
| 3 | **Strategy** | `strategy_breakdown` | Per-strategy table; only if not suppressed |
| 4 | **Languages** | `language_breakdown`, `config_breakdown`, `user_style_breakdown` | Three stacked breakdown sections |
| 5 | **Misses** | `answer_when_missed` | by_expected / by_distractor / by_pair tables |
| 6 | **Answers** | `model_answer_distribution`, `model_answer_variants` | Histogram + raw variant chips per bucket |
| 7 | **Ordering** | `ordering_hints[]` | Observation + recommendation per hint |
| 8 | **Classes** | `summary.response_class_counts` | Histogram of non-zero classes |
| 9 | **Notes** | `annotator_notes[]` | One row per note: case_id, language, text |
| 10 | **Negatives** | `negative_span_groups[]`, `manual_keyword_distribution`, `context_anchor_groups[]` | Negative-pattern cards with examples + correct_span reference; manual-keyword chips; context-anchor chips |

`CaptureQualityPill` ([improvement-report-dialog.tsx:881-905](../frontend/src/components/review/improvement-report-dialog.tsx#L881-L905)) tones on `capture_contains_rate` (≥0.8 green, ≥0.5 amber, <0.5 red). Title attribute shows both `capture_contains_rate` and `capture_exact_rate` so agents can spot exact-vs-contains divergence.

Sample-captures table renders `case_id` / `captured` / `annotated` / alignment marker (✓ exact, ~ partial, ✗ misaligned) per row.

Footer: **Copy JSON** + **Download JSON** — the format the parser-refactor agent consumes.

Tab declarations: [improvement-report-dialog.tsx:140-225](../frontend/src/components/review/improvement-report-dialog.tsx#L140-L225). Note all conditional tabs use the same `report.section && report.section.length > 0` pattern.

## 2.9 Phase 8 — annotation-to-refactor workflow

The canonical loop, established by the `object_tracking` plugin refactor and now generalised:

1. **Annotate ≥100 cases per plugin** via `/review`. Mix mark types deliberately — context anchors and negative keywords are as important as answer spans.
2. **Generate the Improvement Report** (`POST /api/human-review/report` or **Generate Improvement Report** button on `/results`). Download the JSON.
3. **Hand the JSON to a coding agent** (or read it yourself). The agent identifies failure modes by reading:
   - `span_groups[].regex_test` — pairs `match_rate` vs `capture_contains_rate` to find regex candidates.
   - `context_anchor_groups[]` — high-leverage locating phrases (e.g. `Conclusion`, `Therefore`, `Висновок`).
   - `negative_span_groups[]` — patterns the parser must filter out.
   - `data_quality.warnings[]` — signals about what's missing from the report.
4. **Implement parser fixes** scoped to identified modes. Extrapolate multilingual entries from annotated languages to unannotated ones (e.g. EN/UA conclusion anchors → ES/FR/DE/ZH heuristics).
5. **Add `test_phase8_*` regression tests** encoding the failure modes with real annotation samples.
6. **Log multilingual extrapolations in TECHDEBT** (e.g. [TD-114](../TECHDEBT.md)) so later annotation rounds can validate.
7. **Re-parse historical results** with the updated parser (no model calls — `reanalyze.py` does this) and compare alignment ratios pre/post.

The goal of each Phase 8 cycle is to push `parser_was_correct` and `alignment_ratio` upward without regressions in any plugin.

## 2.10 Known issues & gotchas (cross-references)

These are documented authoritatively in [.claude/CLAUDE.md](../.claude/CLAUDE.md) "Known Issues & Gotchas" §12-18; this section is a cross-ref index.

| # | Topic | Source of truth |
|---|---|---|
| 12 | Annotation invariant: ≥1 of `spans` / `response_classes` / mark-arrays. Both span and class may coexist. | CLAUDE.md §12, validated [human_review.py:438-441](../src/web/api/human_review.py#L438-L441) |
| 13 | Translation panel must be `select-none` — prevents char-offset contamination. | CLAUDE.md §13, enforced [translation-panel.tsx:79](../frontend/src/components/review/translation-panel.tsx#L79) |
| 14 | `match_rate` ≠ capture quality. Always pair with `capture_contains_rate`. | CLAUDE.md §14, see [§2.7.2](#272-match_rate--capture-quality-load-bearing) |
| 15 | Suppressed sections vs missing sections — `data_quality.warnings[]` is the source of truth. | CLAUDE.md §15, see [§2.7.4](#274-suppressed-sections-vs-missing-sections) |
| 16 | Long-tail collapse is guarded — small focused sessions keep all groups intact. | CLAUDE.md §16, see [§2.7.3](#273-the-long-tail-collapse-rule-v25) |
| 17 | Annotation sidecar key is `case_id::response_hash`, not `case_id` alone. | CLAUDE.md §17, see [§2.2](#22-the-canonical-key) |
| 18 | `useDeleteAnnotations` MUST invalidate `["review-cases"]` (the otherwise infinite-stale cache). | CLAUDE.md §18, see [§2.6](#26-frontend-internals) |

---

# Appendix

## A.1 Quick reference card

```
┌───────────────────────── KEYBOARD ─────────────────────────┐
│                                                            │
│  ←/→     Prev / Next case (saves draft on Next)            │
│  S       Skip — advance without saving                     │
│  1–7     Toggle classification chip                        │
│  Space   Commit pending drag-selection                     │
│  Enter   ↑ alias                                           │
│  ?       Toggle help dialog                                │
│                                                            │
├──────────────────────── MARK TYPES ────────────────────────┤
│                                                            │
│  LMB                Answer span        (blue solid)        │
│  Ctrl/Cmd+LMB       Context anchor     (indigo dashed)     │
│  Alt/Opt+LMB        Answer keyword     (violet dotted)     │
│  Shift+LMB          Negative span      (rose solid)        │
│  Shift+Alt/Ctrl+LMB Negative keyword   (dark rose dotted)  │
│                                                            │
│  All combos work for one-click and drag-select.            │
│  Adjacent same-type marks auto-merge.                      │
│  Click an existing mark to remove it.                      │
│                                                            │
├────────────────────── RESPONSE CLASSES ────────────────────┤
│                                                            │
│  1 Hedge          5 Lang. error                            │
│  2 Truncated      6 Verbose                                │
│  3 Gibberish      7 False-pos.                             │
│  4 Refusal                                                 │
│                                                            │
│  Multi-select. Coexists with spans (often required).       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## A.2 Source file index

Grouped by area. Every file mentioned in this guide.

### Backend — Python

| Path | Role |
|---|---|
| [src/web/api/human_review.py](../src/web/api/human_review.py) | FastAPI router, Pydantic models, response_hash, schema migration |
| [src/web/annotation_store.py](../src/web/annotation_store.py) | SQLite persistence layer, atomic upserts, JSON-array de/serialisation |
| [src/web/annotation_store_migrator.py](../src/web/annotation_store_migrator.py) | One-shot sidecar→DB migration, MD5→SHA256 rehash logic |
| [src/web/human_review_aggregator.py](../src/web/human_review_aggregator.py) | Pure-function Improvement Report builder (`format_version="2.6"`) |
| [src/web/translation.py](../src/web/translation.py) | deep-translator wrapper, provider routing, LRU cache |
| [src/web/db.py](../src/web/db.py) | SQLite migration runner, `transaction()` context manager |
| [src/web/db_migrations/002_annotations.sql](../src/web/db_migrations/002_annotations.sql) | Annotation table schema |

### Frontend — TypeScript / React

| Path | Role |
|---|---|
| [frontend/src/pages/review.tsx](../frontend/src/pages/review.tsx) | `/review` workspace, draft state, keyboard handler, `caseKey()` |
| [frontend/src/components/review/stimulus-panel.tsx](../frontend/src/components/review/stimulus-panel.tsx) | Left column: prompts, language badges, translate trigger |
| [frontend/src/components/review/response-panel.tsx](../frontend/src/components/review/response-panel.tsx) | Right column: response rendering, click/drag handlers, mark-type modifier detection, parser disagreement banner |
| [frontend/src/components/review/annotation-dock.tsx](../frontend/src/components/review/annotation-dock.tsx) | Pending-span confirmation dock with position/format dropdowns |
| [frontend/src/components/review/classification-bar.tsx](../frontend/src/components/review/classification-bar.tsx) | Seven response-class chips with on/off Tailwind tones |
| [frontend/src/components/review/case-progress.tsx](../frontend/src/components/review/case-progress.tsx) | Header progress bar, filter knobs, target-language dropdown |
| [frontend/src/components/review/verdict-pill.tsx](../frontend/src/components/review/verdict-pill.tsx) | Active classifications as removable pills |
| [frontend/src/components/review/translation-panel.tsx](../frontend/src/components/review/translation-panel.tsx) | Translation pane with `select-none` enforcement |
| [frontend/src/components/review/chunk-gutter.tsx](../frontend/src/components/review/chunk-gutter.tsx) | Peek-translate vertical bars per chunk |
| [frontend/src/components/review/help-dialog.tsx](../frontend/src/components/review/help-dialog.tsx) | `?`-triggered keyboard reference modal |
| [frontend/src/components/review/improvement-report-dialog.tsx](../frontend/src/components/review/improvement-report-dialog.tsx) | 10-tab report viewer, `CaptureQualityPill`, sample-captures table |
| [frontend/src/hooks/use-review.ts](../frontend/src/hooks/use-review.ts) | React Query hooks: `useReviewCases`, `useSaveAnnotation`, `useImprovementReport`, `useDeleteAnnotations`, `useTranslation` |
| [frontend/src/api/human-review.ts](../frontend/src/api/human-review.ts) | API client: `fetchReviewCases`, `saveAnnotation`, `fetchAnnotations`, `fetchImprovementReport`, `deleteAnnotations`, `translate` |
| [frontend/src/lib/translate-chunks.ts](../frontend/src/lib/translate-chunks.ts) | Paragraph/sentence chunking with offset preservation |

### Tests

| Path | Coverage |
|---|---|
| [tests/test_annotation_store.py](../tests/test_annotation_store.py) | Atomic upsert, meta propagation, delete semantics |
| [tests/test_human_review.py](../tests/test_human_review.py) | API endpoints, validation invariants, fallback chain, contamination detection |

### Reference

| Path | Notes |
|---|---|
| [.claude/CLAUDE.md](../.claude/CLAUDE.md) | §10 (architecture summary, agent-facing) and §12-18 (Known Issues authoritative source) |
| [CHANGELOG.md](../CHANGELOG.md) | Per-release annotation-system change history |
| [TECHDEBT.md](../TECHDEBT.md) | Open items: TD-095 (per-row delete — resolved), TD-096 (SHA256 hash — resolved), TD-113 (strategy_breakdown.parser_ok backfill — open), TD-114 (multilingual anchor extrapolation — open) |
