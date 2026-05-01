# Feature Request: Annotation UI Ergonomics Redesign

> Phased redesign of the `/review` workspace to reduce hand fatigue, simplify the mark-type taxonomy, and infer more state from context. Driven by sustained solo-annotator usage revealing that the current modifier-key combinations cause hand strain over long annotation sessions and that the answer-span dock adds round-trip overhead to the most frequent operation.

**Status:** Proposed
**Scope:** `frontend/src/pages/review.tsx`, `frontend/src/components/review/*`, `src/web/api/human_review.py` (response_classes set), `src/stages/run_testset.py` or equivalent (auto-truncation flag), aggregator schema (negative span unification).
**Phases:** 3 (see §6).
**Backward compatibility:** None for keybindings (single-user system; clean break). Annotation schema migrations apply (existing annotations continue to load).

---

## 1. Motivation

The current `/review` workspace requires constant hand repositioning between the mouse, the modifier keys (Ctrl/Alt/Shift), and the number row (1–7) for classifications. Sessions of 30+ minutes cause measurable hand discomfort and break focus flow. Additionally, the answer-span workflow (drag-select → dock → confirm position/format → Space) has a round-trip overhead on what is by far the most frequent annotation action — and the position/format auto-detection has been observed to be reliable enough that the human override has not been used in practice.

The redesign targets four specific problems:

1. **Modifier-combo fatigue** — Ctrl/Alt/Shift+click forces three-limb coordination per mark.
2. **Dock round-trip** — answer spans require an extra confirmation step on the most common operation.
3. **Mark-type taxonomy creep** — the answer/context/keyword/negative-span/negative-keyword schema has grown beyond what's used in practice.
4. **Classification redundancy** — the seven response classes have blurred boundaries and one of them (`truncated`) is machine-detectable from inference metadata.

---

## 2. Design principles

- **Most frequent operation = zero hand repositioning.** Drag-select → Space to advance must require no hand movement away from mouse + left-hand home position.
- **Hold-to-modify, not click-to-toggle.** Modifier keys (A/D/Shift) are held during selection. Released after commit. No mode state to remember between cases.
- **Auto-infer what's machine-detectable.** Truncation, parser-disagreement implications, and position/format are all inferred — human attention reserved for true judgment calls.
- **Visual feedback is mandatory for every modifier state.** Holding a modifier without visible UI response is a bug.
- **Single-user clean break.** No legacy keybinding fallbacks. The old Ctrl/Alt/Shift+click bindings are removed.

---

## 3. Keybinding spec

### 3.1 Mouse + modifier grammar

| Action | Modifier | Result |
|---|---|---|
| Drag-select / click | (none) | Answer span (blue solid) |
| Drag-select / click | Hold **A** | Context anchor (indigo dashed) |
| Drag-select / click | Hold **D** | Answer keyword (violet dotted) |
| Drag-select / click | Hold **Shift** | Negative span (rose solid) |
| Click on parser-highlighted region | (none) | Confirm parser's extraction as answer span |
| Click on parser-highlighted region | Hold **Shift** | Toggle `false_positive` classification |

**Auto-merge** behavior is unchanged — adjacent same-type marks merge within 1-character gap.
**Removal** is unchanged — clicking an existing mark removes it.
**Drag-select dock for answer spans is removed** — answer spans commit immediately on mouse-up with auto-detected position/format. If position/format is wrong, the human marks the wrong-format span as removed (click) and re-marks; format misclassification is acceptable cost vs. dock overhead.

### 3.2 Disambiguation rules

- **Shift+click on a parser-highlighted word**: toggles `false_positive`. Does NOT create a negative span.
- **Shift+click on a non-parser-highlighted word**: starts a negative span (length 1 unless extended via drag).
- **Shift+drag-select crossing the parser-highlighted region**: creates a negative span over the entire dragged range, including the parser region. Negative span wins over false_positive in this case (the explicit drag intent overrides the click-on-parser shortcut).
- **A and D held simultaneously**: undefined — system picks A (anchor takes precedence), no error. Document this in the help dialog.
- **Shift held with A or D**: undefined — system ignores the secondary modifier, treats as A or D respectively.

### 3.3 Auto-inferred negative span on parser disagreement

When the parser extracted region X and the human marks region Y as the answer span (where X ≠ Y), the system **automatically creates a negative span at region X**. The human does not need to manually mark the parser's wrong extraction as a negative.

Rationale: in the parser-was-wrong workflow (the majority of annotated cases), the parser's extraction is by definition the wrong region. Auto-inferring this saves one explicit mark per case and produces cleaner `negative_span_groups[]` data without relying on annotator discipline.

The auto-inferred negative span is visually distinguishable from manually-created ones (e.g., subtler outline, tooltip "auto-inferred from parser disagreement"). The human can remove it like any other mark if it's not actually a useful negative example.

### 3.4 Classification keys

5 classes (down from 7). Bound to keys 1–5 AND to letter keys for left-hand reachability:

| Key | Letter | Class | Notes |
|---|---|---|---|
| 1 | (implicit) | Extractable | Default state — auto-set when an answer span exists. No button or key needed. |
| 2 | E | Truncated | Auto-pre-toggled when result-file flag indicates truncation; human can un-toggle. |
| 3 | Q | Unrecoverable | Folds previous `gibberish`, `refusal`, generation loops, `language_error`-with-no-recoverable-answer. |
| 4 | F | False-positive | Toggleable via Shift+click on parser highlight (preferred) OR by pressing F. |
| 5 | (no letter) | Hedge | Bound only to 5 — used rarely enough that keyboard ergonomics don't dominate. |

**Removed classes:** `verbose` (folded into Extractable — verbose-with-recoverable-answer is just a normal extractable case with a span), `language_error` (folded into Unrecoverable when no recoverable answer; otherwise just Extractable), `parser_ok` (already auto-inferred at report time), `gibberish` (folded into Unrecoverable).

**Number keys 1–5 also work** as fallback / for users who think in numeric IDs.

Live toggle behavior is preserved — pressing Q/E/F/5 (or 2-5) at any time during marking toggles the relevant class.

### 3.5 Navigation keys

| Key | Action |
|---|---|
| **Space** | If draft has any annotation: save and advance. If no annotation: skip and advance. |
| **Ctrl+Space** | Reject changes (discard draft) and advance. Pinky-deliberation; intentional friction. |
| **←** | Previous case (saves dirty draft first). |
| **Ctrl+Z** | Undo last action (span creation, classification toggle, mark removal) within current case. |
| **Ctrl+Shift+Z** | Redo. |
| **?** | Toggle help dialog. |

**Undo/redo scope:** Per-case, with at least 10-step history. Cleared on case advance. Specifically covers the "I accidentally pressed Ctrl+Space" recovery case — pressing ← after Ctrl+Space restores the rejected draft (since save-on-advance doesn't fire when Ctrl+Space was used).

**Removed keys:** `S` (skip — replaced by Space-on-empty-draft).

---

## 4. Visual feedback spec

### 4.1 Modifier-hold indicators

When a modifier key (A, D, or Shift) is held, the response panel must provide visible feedback. Two layers:

1. **Panel tint** — the entire response panel background gets a subtle color overlay (5-10% opacity) matching the mark color: indigo for A, violet for D, rose for Shift.
2. **Hover-word preview** — the word currently under the cursor is highlighted with the target mark color (border-bottom matching the mark style).

Optional third layer: a small mode badge in the response panel corner showing the mark type name in the mark color (e.g., "ANCHOR" in indigo while A is held). Implementation discretion — if the tint + hover preview is sufficient, the badge may be omitted.

### 4.2 Save-state feedback

On successful save (after Space-with-draft), display a 1.5-second micro-toast in the bottom-right corner: `saved ✓` in muted green. Existing failure-toast behavior is unchanged.

On Ctrl+Space (reject and advance), display `discarded` in muted rose for 1.5 seconds.

### 4.3 Parser-pre-highlight reliability

Investigation issue: the user reports the parser's extracted-region pre-highlight occasionally lags or fails to render. Root cause is suspected to be the parser not consistently emitting position information. Fix scope:

1. Audit each plugin's parser output for `start_offset` / `end_offset` fields on extractions.
2. Where missing, add a deterministic post-extraction string-search to compute offsets (find the extracted text in the response, return first match, prefer end-position matches for end-first parsers).
3. Cache the computed offsets on the result entry so subsequent loads don't recompute.

This is a prerequisite for §3.1 "click on parser-highlighted region" semantics to work reliably.

---

## 5. Schema changes

### 5.1 Annotation schema

**Removed mark types:** `negative_keywords`. Existing annotations with `negative_keywords` are migrated on read by folding entries into `negative_spans` (preserving `text`, `char_start`, `char_end`).

**Removed response classes:** `verbose`, `gibberish`, `language_error`, `parser_ok`. Migration map (applied in `_migrate_annotation()`):

| Old class | New class |
|---|---|
| `verbose` | (dropped — Extractable is implicit when a span exists) |
| `gibberish` | `unrecoverable` |
| `refusal` | `unrecoverable` |
| `language_error` | `unrecoverable` (if no span present) OR (dropped — extractable case) |
| `parser_ok` | (dropped — auto-inferred at report time) |
| `verbose_correct` | already aliased to `verbose`, then dropped |
| `parser_false_positive` | already aliased to `false_positive`, retained |

The canonical class set becomes: `{truncated, unrecoverable, false_positive, hedge}`. Extractable is the implicit default and not a stored value.

### 5.2 Result-file schema (auto-truncation)

Add `was_truncated: bool` to each entry in `results[]`. Computed at inference time:

```python
was_truncated = (generated_tokens >= max_tokens) or (finish_reason == "length")
```

Both signals are checked because some providers report `finish_reason="length"` without exposing token counts, and some report token counts without `finish_reason`. The flag is `True` if either signal fires.

Backward compatibility: existing result files without `was_truncated` are treated as `False`. The review UI's truncated chip is not pre-toggled for these — human must toggle manually as before.

### 5.3 Improvement Report

`negative_span_groups[]` no longer carries `mark_type` field (only one negative type exists post-redesign). Existing reports retain the field for legacy compatibility.

`response_class_counts` no longer reports `verbose`, `gibberish`, `language_error`, `parser_ok`. Migration of historical reports is not performed — old reports remain readable as v2.6 with these fields, new reports omit them.

---

## 6. Phasing

### Phase 1 — Core UX (highest priority)

- Implement new keybinding grammar (§3.1, §3.2, §3.4, §3.5).
- Remove answer-span dock; immediate commit on mouse-up with auto-detected position/format.
- Implement undo/redo (§3.5).
- Implement modifier-hold visual feedback (§4.1) and save-state toasts (§4.2).
- Schema migration: remove `negative_keywords`, fold into `negative_spans` (§5.1).
- Schema migration: collapse response classes to 4 + implicit Extractable (§5.1).
- Update help dialog and quick-reference card.
- Update `human_review.md` Part 1 (Workflow Loop) and §1.4, §1.6, §1.9 specifically.

### Phase 2 — Smarter defaults

- Implement parser-click semantics (§3.1 row "Click on parser-highlighted region", §3.2 disambiguation).
- Implement auto-inferred negative span on parser disagreement (§3.3).
- Audit parser output for position info; add string-search fallback (§4.3).
- Update `human_review.md` Part 2 §2.5 (annotation data model — auto-inferred marks) and §2.7.5 (negative-mark semantics now single-type).

### Phase 3 — Inference-time integration (can run in parallel with Phase 2 by a separate agent)

- Add `was_truncated` computation to result-collection path (§5.2).
- Pre-toggle Truncated chip in review UI when flag is set.
- Update result-file schema documentation.
- Backfill not required — historical files remain at the human-toggle baseline.

---

## 7. Out of scope (explicit non-goals)

- **Configurable keybindings.** Settings-driven keymap is desirable but deferred. Single-user system; current spec is the user's preferred layout.
- **Multi-annotator support.** Inter-annotator agreement, qualification tests, reviewer roles, and per-annotator attribution remain future work tied to the (separate) collaborative-deployment direction.
- **System prompt registry / community prompt competition.** Discussed as a future extension to the prompt engine; orthogonal to annotation UI.
- **Annotation versioning / intra-annotator agreement.** Useful for quality claims in writeups but not blocking for current usage.
- **Mobile / touch support.** Annotation workflow assumes desktop with keyboard + mouse.

---

## 8. Acceptance criteria

### Phase 1
- [ ] Holding A while drag-selecting creates a context anchor; releasing A and selecting creates an answer span.
- [ ] Holding D while drag-selecting creates an answer keyword.
- [ ] Holding Shift while drag-selecting creates a negative span.
- [ ] Each modifier shows panel tint + hover-word preview while held.
- [ ] Pressing Space with a draft saves and advances; with no draft, skips and advances.
- [ ] Pressing Ctrl+Space discards draft and advances; `discarded` toast appears.
- [ ] Pressing ← restores previous case including any draft state from Ctrl+Space within the same session.
- [ ] Ctrl+Z undoes the last mark or classification; Ctrl+Shift+Z redoes.
- [ ] Q/E/F and 2/3/4 toggle Unrecoverable / Truncated / False-positive respectively.
- [ ] 5 toggles Hedge.
- [ ] Existing annotations with removed classes load successfully (migrated per §5.1).
- [ ] Existing annotations with `negative_keywords` load with entries folded into `negative_spans`.
- [ ] Help dialog reflects new keybinding grammar.
- [ ] No regressions in `tests/test_human_review.py` after migration logic updates.

### Phase 2
- [ ] Clicking a parser-highlighted region with no modifier creates an answer span at that region and advances on Space.
- [ ] Shift+click on parser-highlighted region toggles `false_positive` without creating a negative span.
- [ ] Marking an answer span at region Y when parser extracted region X auto-creates a negative span at X with distinct visual styling.
- [ ] Auto-inferred negative spans can be removed by clicking; removal is undoable.
- [ ] Plugin parsers consistently emit position offsets; pre-highlight no longer lags or fails.

### Phase 3
- [ ] New result files have `was_truncated` flag computed at inference time.
- [ ] Truncated chip is pre-toggled in review UI when flag is true.
- [ ] Human can un-toggle the pre-set Truncated chip; un-toggle is persisted.
- [ ] Files without `was_truncated` (legacy) display Truncated chip in default off state.

---

## 9. Open implementation questions for the coding agent

These are decisions the agent should make and document in the PR rather than ask back:

1. **Hover-word preview rendering technique** — CSS pseudo-element vs JS-driven className swap. Performance under fast cursor movement matters.
2. **Undo stack data structure** — naive action log vs immutable snapshot. Snapshot is simpler if cases are small (they are).
3. **Auto-inferred negative span styling** — exact opacity / dash pattern. Suggest 60% opacity of normal negative span color, dotted instead of solid border.
4. **Save-toast positioning** — bottom-right vs near the response panel. Suggest bottom-right matching existing toast conventions.
5. **Migration of `verbose`-classified historical annotations** — drop the class entirely (cleanest) vs preserve it as a no-op field for archival traceability. Suggest drop; the spans tell the story.

---

## 10. Documentation updates required

- `docs/human_review.md` Part 1 §1.4 (mark types), §1.6 (response classes), §1.9 (keyboard shortcuts), §1.11 (Improvement Report tabs), Appendix A.1 (quick reference card).
- `docs/human_review.md` Part 2 §2.5 (annotation data model), §2.7.5 (negative-mark semantics), §2.10 (cross-references — drop or update items affected by class removals).
- `.claude/CLAUDE.md` §12 (annotation invariant — confirm still holds), §17 (canonical key — unchanged).
- `CHANGELOG.md` entries per phase.
- `TECHDEBT.md` — close out items resolved by Phase 2 (auto-inferred negative); add new items if Phase 3 surfaces parser output gaps.
