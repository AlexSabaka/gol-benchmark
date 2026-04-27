---
name: parser-refactor-from-annotations
description: Drive a parser refactor from a Human Review Improvement Report JSON. Use when the user shares an Improvement Report file, asks "refactor the parser using these annotations", mentions "Phase 8 refactor", or hands over annotated review cases to act on. Walks through the standard read-JSON-identify-modes-fix-test workflow established by the object_tracking refactor.
tools: Read, Write, Edit, Bash, Grep, Glob
---

# Parser Refactor From Annotations (Phase 8 Workflow)

The Improvement Report JSON (produced by `POST /api/human-review/report`, format version 2.7) is structured specifically to drive parser refactors. This skill is the template for that workflow.

The first parser refactor driven entirely by user annotations was `object_tracking` (v2.26+) — 129 annotated EN/UA cases pushed `alignment_ratio` from 0.712 toward a targeted ≥0.85. Read [docs/HUMAN_REVIEW_GUIDE.md § 2.9](../../../docs/HUMAN_REVIEW_GUIDE.md#29-phase-8--annotation-to-refactor-workflow) for the full architectural context; this skill is the operational checklist.

---

## Prerequisites

Before starting, verify:

- The Improvement Report JSON is at `format_version: "2.7"`. Older versions are missing `negative_span_groups` and `context_anchor_groups`.
- The annotation set covers at least 100 cases for the target plugin. Below 30 cases, the per-group statistics aren't trustworthy — the report's `data_quality.warnings[]` will say so.
- Both languages with significant failure rates are annotated. Single-language refactors produce single-language fixes; the plugin then regresses on un-annotated languages.
- `data_quality.warnings[]` does NOT include `uniform_*` codes (uniform expected answer / uniform language) — those mean the section was suppressed and you have no signal.

If the report is too thin, ask the user to annotate more cases before starting. Don't refactor on insufficient evidence.

---

## Step 1 — Read the report and identify failure modes

The report has these load-bearing sections (per [docs/HUMAN_REVIEW_GUIDE.md § 2.7](../../../docs/HUMAN_REVIEW_GUIDE.md#27-improvement-report-v26--the-contract)):

| Section | Use it to find |
|---|---|
| `summary.parser_span_alignment` | The big-picture metric. `aligned_with_parser` ratio < 0.85 = significant work to do. |
| `summary.response_class_counts` | If `truncated` or `unrecoverable` dominate, the issue is upstream (model OOM, refusal) — not the parser. |
| `span_groups[]` | Each group is one failure mode. `position` + `format` + `count` describe what the parser missed. Look at the top 3–5 groups by count. |
| `regex_test[]` | For each candidate regex the report generated, `match_rate` says "how often does it fire" and `capture_contains_rate` says "when it fires, does it capture the right substring." Pair them: a 1.0/0.3 split means the regex is firing on the wrong region. |
| `context_anchor_groups[]` | Phrases the annotators marked as A-modifier (Answer-context anchors). These are the WORDS that signal "the answer is nearby" — useful for new strategies. |
| `negative_span_groups[]` | Phrases the parser MUST NOT match. Often option-listing phrases (`"or drive"`) or distractor words. |
| `parser_span_alignment.misaligned[]` | Specific cases where the parser extracted X but the annotator marked Y. Read 3–5 raw examples directly to see the pattern. |
| `data_quality.warnings[]` + `data_quality.suppressed_sections[]` | Read these FIRST. They tell you which dimensions of the analysis are trustworthy. |

Group failure modes into 1–4 buckets. The `object_tracking` refactor identified three:

1. **Conclusion-anchored plain trailer** — `"Therefore, the X is in the Y"` — needed a strategy that walked from the LAST reasoning anchor forward.
2. **Bold trailer at end of verbose response** — needed a two-pass `_strategy_bold_keyword` (existing first-match pass kept for concise answers; new end-first anchored pass added for verbose).
3. **`last_word` junk tokens** (`"within"`, `"relative"`, `"bottom"`) — needed tightening to require `known_locations` membership or return None.

If you can't articulate a specific failure mode for a fix, it's premature. Go back to the report.

---

## Step 2 — Plan multilingual extrapolation explicitly

Annotation evidence usually covers EN + one other language. Fixes need to work in all 6. The pattern (from object_tracking):

- For each new dict (`_CONCLUSION_ANCHORS`, `_LOCATION_PREPS`, `_BOLD_TRAILER_ANCHORS`), populate the annotated languages from real data.
- Extrapolate ES/FR/DE/ZH from reasoning-closure vocabulary in the same semantic class.
- Track each extrapolated entry in `TECHDEBT.md` with a TD number — annotated validation comes later.

Example TECHDEBT entry shape:

```markdown
## TD-XXX: Extrapolated `<dict_name>` entries for <plugin> in ES/FR/DE/ZH

The Phase 8 refactor of `<plugin>` parser added `<dict_name>` entries for English and Ukrainian based on annotated cases. ES/FR/DE/ZH entries were extrapolated from reasoning-closure vocabulary in the same semantic class. Validate against per-language annotations when available; remove this TD when validated.
```

---

## Step 3 — Implement scoped fixes

One fix per failure mode. Resist the temptation to refactor the whole parser.

For each fix:

- **Add a new strategy method** (`_strategy_<name>`) rather than modifying an existing one. Existing strategies have annotation-validated behavior; don't break that.
- **Order it correctly in the strategy pipeline** — high-confidence on raw text first, lower-confidence on `strip_verification_tail()`-stripped text later.
- **Honor `parse_strategy` naming** — plugin-specific names for the new strategies; reserved names `"empty"` and `"fallback"` only for the canonical terminal states.
- **If the fix changes a multilingual dict**, update ALL 6 languages in one commit (annotated + extrapolated). Splitting across commits creates a window where some languages are broken.

Reference shape (from object_tracking):

```python
# New module-level dicts at top of parser.py
_CONCLUSION_ANCHORS: Dict[str, List[str]] = {
    "en": ["Conclusion", "Therefore", "In conclusion", "Final Location"],
    "uk": ["Висновок", "Отже", "У підсумку", "Кінцеве розташування"],
    "es": ["Conclusión", "Por lo tanto", "En conclusión"],  # extrapolated, see TD-114
    # ... fr, de, zh
}

# New strategy method
def _strategy_anchored_trailer(self, text: str, task_params: Dict) -> Optional[ParsedAnswer]:
    """Walk from LAST reasoning-anchor position forward, match preposition + 1-3 word capture,
    require intersection with known_locations. Targets failure mode #1 from Phase 8."""
    lang = get_language(task_params)
    anchors = _CONCLUSION_ANCHORS.get(lang, []) + _CONCLUSION_ANCHORS["en"]
    # ... implementation ...

# Inserted into the strategy pipeline at the right place
def parse(self, response: str, task_params: Dict) -> ParsedAnswer:
    text = normalize_unicode(response.strip())
    if not text:
        return ParsedAnswer(value=None, raw_response=response, parse_strategy="empty")

    # High-confidence first
    if (result := self._strategy_bold_keyword(text, task_params)):
        return result
    if (result := self._strategy_anchored_trailer(text, task_params)):  # NEW
        return result

    # Lower-confidence on stripped text
    stripped = strip_verification_tail(text)
    # ... etc ...

    return ParsedAnswer(value=None, raw_response=response, parse_strategy="fallback")
```

---

## Step 4 — Add `test_phase8_*` regressions

For each failure mode targeted, add at least one test in `tests/plugins/test_<plugin>.py` that:

- Uses a real annotation-sample response (paste verbatim from the report's `parser_span_alignment.misaligned[]` examples)
- Asserts the parser now extracts the right value
- Names the test `test_phase8_<short_mode_name>` so it's grep-able later

```python
def test_phase8_conclusion_anchored_trailer():
    """Phase 8: 'Therefore, the X is in the Y' should extract Y, not last bold."""
    parser = ObjectTrackingParser()
    response = "...long reasoning... Therefore, the grape is in the cup."
    task_params = {"language": "en", "known_locations": ["cup", "bowl", "plate"]}
    parsed = parser.parse(response, task_params)
    assert parsed.value == "cup"
    assert parsed.parse_strategy == "anchored_trailer"
```

Run them:

```bash
pytest tests/plugins/test_<plugin>.py -v -k phase8
```

---

## Step 5 — Re-run reanalysis on the original results

```bash
python3 -c "
from src.web.reanalyze import reanalyze_file
import sys
report = reanalyze_file('results/<original_file>.json.gz', dry_run=False)
print(report)
"
```

Spot-check the diff:

- Did `summary.accuracy` improve in the expected direction?
- Did `parse_strategy` distribution shift to the new strategies as expected?
- Are there any cases that REGRESSED (used to be correct, now wrong)? If yes, the fix over-reaches — narrow it.

The `object_tracking` Phase 8 work targeted ≥ 0.85 alignment ratio post-refactor; pick a similar concrete metric for your plugin's refactor target so you can declare done.

---

## Step 6 — Update docs and TECHDEBT

- Add a CHANGELOG entry under the next release.
- For each TD-numbered extrapolation, add the TECHDEBT entry from Step 2.
- If the refactor introduces a new pattern that other plugins should adopt (cross-plugin alignment Phase 6+?), note it in [docs/PLUGIN_GUIDE.md § End-First Parsing Convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention) for the next maintainer.

CLAUDE.md does NOT need updating — the architectural reference for end-first parsing lives in PLUGIN_GUIDE.

---

## Known caveats

- **`strategy_breakdown.parser_ok = 0` aggregator bug (TD-113)** — currently the per-strategy win/loss rates are not populated. Until that's fixed, you can't read the report's `strategy_breakdown` section to see which strategies are winning. Use raw inspection of `parser_span_alignment.aligned[]` vs `misaligned[]` instead.
- **Uniform-axis suppression** — if every annotated case shares one expected answer, `answer_when_missed.by_expected` is omitted. The report says so in `data_quality.suppressed_sections`. Don't treat absence as a bug.
- **Markdown-stripped buckets keep stems separate** — `walk` and `walking` are different buckets on purpose. If you want them treated the same, the parser needs explicit stemming.
- **`match_rate` ≠ capture quality** — see [HUMAN_REVIEW_GUIDE.md § 2.10 #3](../../../docs/HUMAN_REVIEW_GUIDE.md#210-known-issues--gotchas). Always pair `match_rate` with `capture_contains_rate` before adopting a regex from the report's auto-generated candidates.

---

## What NOT to do

- **Do not refactor without 100+ annotated cases.** The report's group statistics need that floor to be reliable.
- **Do not modify existing strategies in place.** Add new strategies; insert them at the right priority. Existing strategies have annotation-validated behavior.
- **Do not drop `parse_strategy` labels** — they're how the next refactor will measure your work.
- **Do not ship multilingual extrapolation without a TECHDEBT entry.** The whole point of Phase 8 is iterative validation; extrapolations need to be visible so the next round of annotations can confirm or correct them.
