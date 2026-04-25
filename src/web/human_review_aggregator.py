"""Improvement-report aggregator for the Human Review feature.

Pure-function module. Given a list of annotation sidecar payloads (and
optionally the source result-file payloads they came from), produces the
report sections consumed by the Improvement Report dialog and by downstream
coding agents tasked with parser refactors.

Output schema (`format_version: "2.5"`):

  {
    "format_version": "2.5",
    "source_files": [...],
    "summary": {...},                 # totals + false_positive_rate + response_class_counts
    "false_positive_rate": float,     # mirrored at top-level for prominence
    "parser_span_alignment": {...},   # aligned / misaligned / no_output split
    "data_quality": {...},            # warnings + suppressed_sections
    "model_answer_distribution": {...},
    "model_answer_variants": {...},   # raw text variants per normalized bucket
    "span_groups": [...],             # rich (position, format) groups — count ≥ 4
    "long_tail_groups": [...],        # v2.5: collapsed groups with count < 4
    "answer_when_missed": {...},      # suppressed under `uniform_expected`
    "strategy_breakdown": {...},      # suppressed under `no_parse_strategy`
    "language_breakdown": {...},      # suppressed under `uniform_language`
    "config_breakdown": {...},        # suppressed under `uniform_system_style`
    "user_style_breakdown": {...},    # suppressed under `uniform_user_style`
    "ordering_hints": [...],          # omitted when empty
    "annotator_notes": [...],         # omitted when empty
  }

v2.5 dropped `confusion_matrix`, top-level `anchor_frequency`, top-level
`response_classes` (folded into `summary.response_class_counts`). All
suppressions are recorded in `data_quality.suppressed_sections` so consumers
can distinguish "absent because empty" from "absent because noise".

Backwards-compat: legacy annotation sidecars (pre-v2.20.1) lack the per-case
metadata fields (`language`, `parse_strategy`, `context_windows`, etc.). When
`build_report` is given a `result_payloads_by_file` map, the aggregator
back-fills those fields from the source result entries before computing.
Without the map, missing fields just degrade to `unknown` buckets.

All I/O is the caller's responsibility — this module only transforms data.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.plugins.parse_utils import build_answer_label_re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORMAT_TO_STRATEGY: Dict[str, str] = {
    "bold": "bold_keyword",
    "italic": "italic_keyword",
    "strikethrough": "strikethrough_keyword",
    "header": "header_line",
    "boxed": "boxed_expression",
    "label": "labelled_answer",
    "plain": "last_sentences",
    "other": "full_text",
}

# Known answer-label words across locales — used both as structural signal
# ("answer_label_match_ratio") and for per-group label taxonomy breakdown.
_LABEL_WORDS: Tuple[str, ...] = (
    "answer", "result", "solution", "response", "recommendation", "conclusion",
    "bottom line", "in short", "in summary", "tldr", "tl;dr", "final answer",
    "respuesta", "resultado", "solución", "recomendación", "conclusión",
    "réponse", "résultat", "solution", "recommandation", "conclusion",
    "antwort", "ergebnis", "lösung", "empfehlung", "fazit",
    "答案", "结果", "解答", "建议", "结论",
    "відповідь", "результат", "рішення", "рекомендація", "висновок",
)
_LABEL_WORDS_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _LABEL_WORDS) + r")\b\s*[:：]",
    re.IGNORECASE,
)

# Stop-words that make for useless single-word prefix anchors — drop them
# unless they're part of a longer multi-word phrase.
_PREFIX_STOP_WORDS: set[str] = {
    "to", "is", "a", "an", "the", "of", "in", "on", "at", "it", "as", "be",
    "so", "for", "by", "or", "and", "but", "my", "our", "i", "you", "we",
    # Markdown artifacts that appear alone when the annotation is right after a
    # format marker; low-information as anchors.
    "**", "__", "*", "_", ">", "-",
}

# v4 canonical codes (Phase 1 collapse). Legacy codes still appear in old
# sidecars — the rename/drop maps below fold them into this set on read.
_RESPONSE_CLASSES = (
    "hedge",
    "truncated",
    "unrecoverable",
    "false_positive",
)

# v3 + v4 rename map — applied when reading annotations. Covers both the
# original v3 renames (verbose_correct / parser_false_positive) and the v4
# collapse that folded three model-failure modes into "unrecoverable".
_CLASS_RENAME: dict[str, str] = {
    "parser_false_positive": "false_positive",
    "gibberish": "unrecoverable",
    "refusal": "unrecoverable",
    "language_error": "unrecoverable",
}

# Codes that were dropped entirely — auto-inferred or made implicit.
_CLASS_DROP: frozenset[str] = frozenset({"parser_ok", "verbose", "verbose_correct"})

_NON_RESOLVABLE_CLASSES = {"hedge", "truncated", "unrecoverable"}


def _get_response_classes(ann: dict) -> list[str]:
    """Read response classes from annotation dict, supporting both old
    (``response_class: str``) and new (``response_classes: list``) schema.
    Applies v3+v4 renames and drops ``parser_ok`` / ``verbose`` codes."""
    rcs = ann.get("response_classes")
    if rcs is None:
        rc = ann.get("response_class")
        rcs = [rc] if rc else []
    elif isinstance(rcs, str):
        rcs = [rcs] if rcs else []
    renamed = [_CLASS_RENAME.get(c, c) for c in rcs if c not in _CLASS_DROP]
    # Deduplicate while preserving order (multiple legacy codes can collapse
    # to the same new code).
    seen: set = set()
    out: list[str] = []
    for c in renamed:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out

_PARSER_MATCH_TYPES = ("correct", "parse_error", "mismatch", "localized_match", "unknown")

_CONTEXT_WINDOW_CHARS = 120
_SENTENCE_BOUNDARIES = set(".!?\n")

# v2.5 — span groups below this count are statistically useless for pattern
# derivation (single-digit sample, typically 1–3 cases). Collapsed into a
# compact `long_tail_groups` stub so the agent still sees they exist without
# having to wade through per-group rollups that carry no signal.
_LONG_TAIL_THRESHOLD = 4

# A 3-word maximum for the cross-group anchor frequency — keeps the table
# scannable and avoids over-fitting to a single example phrase.
_ANCHOR_MAX_WORDS = 3

# Precompiled structural-signal matchers (v2.1).
_LIST_MARKER_RE = re.compile(r"(?:^|\n)\s*(?:[-*]|\d+\.)\s$")
_LABEL_COLON_RE = re.compile(r":\s*$")

# Lazy cache of `build_answer_label_re(language)` compiled patterns.
_ANSWER_LABEL_RE_CACHE: Dict[str, re.Pattern] = {}


def _answer_label_re(language: str) -> re.Pattern:
    lang = (language or "en").lower()
    compiled = _ANSWER_LABEL_RE_CACHE.get(lang)
    if compiled is None:
        pattern = build_answer_label_re(lang)
        compiled = re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)
        _ANSWER_LABEL_RE_CACHE[lang] = compiled
    return compiled


REPORT_FORMAT_VERSION = "2.7"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> List[str]:
    """Lowercase + whitespace-split. Empty/whitespace-only text → []."""
    return [t for t in re.split(r"\s+", text.strip().lower()) if t]


def _normalize_answer(value: Any) -> str:
    """String form for parser_extracted / expected — used as a dict key."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


# ---------------------------------------------------------------------------
# Auto-regex generation (PRD §6b) — preserved from v1, returns plain strings
# so the caller can wrap with weight/confidence metadata.
# ---------------------------------------------------------------------------


def _longest_common_word_prefix(token_lists: List[List[str]]) -> List[str]:
    if not token_lists:
        return []
    first = token_lists[0]
    prefix: List[str] = []
    for i, word in enumerate(first):
        if all(len(tl) > i and tl[i] == word for tl in token_lists):
            prefix.append(word)
        else:
            break
    return prefix


def _escape_phrase(words: List[str]) -> str:
    return r"\s+".join(re.escape(w) for w in words)


def _auto_regex(example_spans: List[str]) -> List[str]:
    """Up to 3 candidate regexes — anchor + bigram-disjunction fallback."""
    cleaned = [s for s in example_spans if s and s.strip()]
    if not cleaned:
        return []

    token_lists = [_tokenize(s) for s in cleaned]
    token_lists = [tl for tl in token_lists if tl]
    if not token_lists:
        return []

    candidates: List[str] = []

    anchor = _longest_common_word_prefix(token_lists)
    if anchor and sum(len(w) for w in anchor) >= 2:
        candidates.append(f"{_escape_phrase(anchor)}\\s+(\\w+)")

    bigrams: Counter = Counter()
    for tl in token_lists:
        if len(tl) >= 2:
            bigrams[(tl[0], tl[1])] += 1
    top = [bg for bg, _ in bigrams.most_common(3)]
    if anchor and len(anchor) >= 2:
        top = [bg for bg in top if list(bg) != anchor[:2]]
    if len(top) >= 2:
        alt = "|".join(_escape_phrase(list(bg)) for bg in top[:2])
        candidates.append(f"(?:{alt})\\s+(\\w+)")
    elif len(top) == 1 and not candidates:
        candidates.append(f"{_escape_phrase(list(top[0]))}\\s+(\\w+)")

    seen: set[str] = set()
    uniq: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
        if len(uniq) >= 3:
            break
    return uniq


def _auto_regex_with_meta(example_spans: List[str]) -> Tuple[List[Dict[str, Any]], str]:
    """Same generation as `_auto_regex` but returns each candidate with its
    `kind` (anchor / disjunction) and `support` (how many examples it covers).

    Also returns a group-level `confidence` label:
      - `high` — anchor regex emitted (longest common prefix held across examples)
      - `medium` — only bigram disjunction emitted
      - `low` — neither anchor nor disjunction (single-example or all distinct)
    """
    cleaned = [s for s in example_spans if s and s.strip()]
    if not cleaned:
        return [], "low"

    token_lists = [_tokenize(s) for s in cleaned]
    token_lists = [tl for tl in token_lists if tl]
    if not token_lists:
        return [], "low"

    candidates: List[Dict[str, Any]] = []

    anchor = _longest_common_word_prefix(token_lists)
    if anchor and sum(len(w) for w in anchor) >= 2:
        candidates.append({
            "pattern": f"{_escape_phrase(anchor)}\\s+(\\w+)",
            "kind": "anchor",
            "support": len(token_lists),
            "anchor_words": anchor,
        })

    bigrams: Counter = Counter()
    for tl in token_lists:
        if len(tl) >= 2:
            bigrams[(tl[0], tl[1])] += 1
    top = [(bg, cnt) for bg, cnt in bigrams.most_common(3)]
    if anchor and len(anchor) >= 2:
        top = [(bg, c) for bg, c in top if list(bg) != anchor[:2]]
    if len(top) >= 2:
        alt = "|".join(_escape_phrase(list(bg)) for bg, _ in top[:2])
        support = sum(c for _, c in top[:2])
        candidates.append({
            "pattern": f"(?:{alt})\\s+(\\w+)",
            "kind": "disjunction",
            "support": support,
            "anchor_words": None,
        })
    elif len(top) == 1 and not candidates:
        bg, cnt = top[0]
        candidates.append({
            "pattern": f"{_escape_phrase(list(bg))}\\s+(\\w+)",
            "kind": "disjunction",
            "support": cnt,
            "anchor_words": list(bg),
        })

    has_anchor = any(c["kind"] == "anchor" for c in candidates)
    has_disjunction = any(c["kind"] == "disjunction" for c in candidates)
    if has_anchor:
        confidence = "high"
    elif has_disjunction:
        confidence = "medium"
    else:
        confidence = "low"

    return candidates[:3], confidence


# ---------------------------------------------------------------------------
# Case projection — back-fill legacy sidecar fields from result payloads
# ---------------------------------------------------------------------------


def _result_index(result_payloads_by_file: Optional[Dict[str, Any]]):
    """Build a (filename, case_id) → result-entry index for back-fill lookups."""
    if not result_payloads_by_file:
        return {}
    idx: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for fname, payload in result_payloads_by_file.items():
        for r in (payload or {}).get("results") or []:
            tid = r.get("test_id")
            if tid:
                idx[(fname, tid)] = r
    return idx


def _backfill_case(
    case: Dict[str, Any],
    file_id: str,
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Return a shallow-copy of `case` with missing context fields back-filled
    from the source result entry, when one is available."""
    needed = ("language", "user_style", "system_style", "parse_strategy", "model_name")
    if all(k in case and case[k] is not None for k in needed):
        return case  # already enriched

    src = result_idx.get((file_id, case.get("case_id", "")))
    if src is None:
        return case

    enriched = dict(case)
    inp = src.get("input") or {}
    pm = inp.get("prompt_metadata") or {}
    out = src.get("output") or {}

    enriched.setdefault("language", pm.get("language") or "en")
    enriched.setdefault("user_style", pm.get("user_style"))
    enriched.setdefault("system_style", pm.get("system_style"))
    if not enriched.get("parse_strategy"):
        enriched["parse_strategy"] = out.get("parse_strategy") or "unknown"
    if not enriched.get("parse_confidence"):
        enriched["parse_confidence"] = out.get("parse_confidence")

    # `context_windows` — synthesize from the source response if missing.
    if not enriched.get("context_windows"):
        raw = out.get("raw_response") or ""
        ann = enriched.get("annotation") or {}
        enriched["context_windows"] = _build_context_windows(raw, ann.get("spans") or [])

    return enriched


def _extract_sentence(raw_response: str, start: int, end: int) -> str:
    """Return the sentence of `raw_response` containing [start, end)."""
    if not raw_response:
        return ""
    n = len(raw_response)
    start = max(0, min(start, n))
    end = max(start, min(end, n))
    s_begin = start
    while s_begin > 0 and raw_response[s_begin - 1] not in _SENTENCE_BOUNDARIES:
        s_begin -= 1
    s_end = end
    while s_end < n and raw_response[s_end] not in _SENTENCE_BOUNDARIES:
        s_end += 1
    return raw_response[s_begin:s_end].strip()


def _build_context_windows(raw_response: str, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mirror of `_extract_context_windows` in api/human_review.py — kept here
    so legacy back-fill doesn't need to import the API module."""
    out: List[Dict[str, Any]] = []
    if not isinstance(raw_response, str) or not raw_response:
        return out
    n = len(raw_response)
    for s in spans:
        try:
            start = max(0, int(s.get("char_start", 0)))
            end = min(n, int(s.get("char_end", 0)))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        out.append({
            "text": raw_response[start:end],
            "char_start": start,
            "char_end": end,
            "before": raw_response[max(0, start - _CONTEXT_WINDOW_CHARS):start],
            "after": raw_response[end:min(n, end + _CONTEXT_WINDOW_CHARS)],
            "sentence": _extract_sentence(raw_response, start, end),
        })
    return out


def _iter_enriched_cases(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield (file_id, enriched_case) tuples across all annotation files."""
    for af in annotation_files:
        file_id = (af.get("meta") or {}).get("result_file") or ""
        for case in (af.get("cases") or {}).values():
            yield file_id, _backfill_case(case, file_id, result_idx)


def _verdict_of(case: Dict[str, Any]) -> str:
    """Single-string verdict label used by breakdowns. Falls back to a
    descriptive sentinel for cases with spans but no class, etc.
    When multiple classes are set, returns the first one (most specific)."""
    ann = case.get("annotation") or {}
    rcs = _get_response_classes(ann)
    spans = ann.get("spans") or []
    if rcs:
        return rcs[0]
    if spans:
        return "_with_spans"
    return "_no_class"


# ---------------------------------------------------------------------------
# Section: session summary + false_positive_rate
# ---------------------------------------------------------------------------


def _session_summary(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Tuple[Dict[str, Any], float]:
    total = 0
    annotated_meta = 0
    skipped = 0
    parser_false_positive = 0  # annotator flagged parser as wrong
    parser_missed_extractable = 0  # spans present, parser missed
    true_unparseable = 0  # hedge/gibberish/refusal/language_error

    # v2.3: within parser_missed_extractable, split by whether the parser's
    # output aligned with the annotator's first span. "Aligned miss" means the
    # parser DID extract the right token but the annotator didn't bother
    # marking parser_ok; "misaligned miss" is a true parser failure.
    missed_aligned = 0
    missed_misaligned = 0
    missed_no_parser_output = 0

    for af in annotation_files:
        meta = af.get("meta") or {}
        annotated_meta += int(meta.get("annotated_count") or 0)
        skipped += int(meta.get("skipped_count") or 0)

    parser_was_correct = 0
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        total += 1
        ann = case.get("annotation") or {}
        rcs = _get_response_classes(ann)
        spans = ann.get("spans") or []
        pe = case.get("parser_extracted")
        if "false_positive" in rcs:
            parser_false_positive += 1
        elif spans:
            # Auto-infer parser_ok: if parser_extracted aligns with any span,
            # count as parser-correct (replaces the manual parser_ok class).
            if pe and any(_is_aligned(pe, (s.get("text") or "")) for s in spans):
                parser_was_correct += 1
            else:
                parser_missed_extractable += 1
                pe_norm = _normalize_answer_text(pe)
                if not pe_norm:
                    missed_no_parser_output += 1
                elif any(_is_aligned(pe, (s.get("text") or "")) for s in spans):
                    missed_aligned += 1
                else:
                    missed_misaligned += 1
        elif any(c in _NON_RESOLVABLE_CLASSES for c in rcs):
            true_unparseable += 1

    annotated = annotated_meta if annotated_meta > 0 else total

    # Accuracy-inflation estimate: of cases the parser proudly labelled correct,
    # what fraction were actually wrong (annotator flagged false-positive)?
    parser_claimed_correct = parser_was_correct + parser_false_positive
    false_positive_rate = (
        parser_false_positive / parser_claimed_correct if parser_claimed_correct else 0.0
    )

    summary = {
        "total_cases": total,
        "annotated": annotated,
        "skipped": skipped,
        "parser_was_correct": parser_was_correct,
        "parser_false_positive": parser_false_positive,
        # `parser_missed_extractable` historically meant "miss with extractable
        # evidence" — false-positives also fit that definition (the right answer
        # is the annotated span, the parser landed elsewhere). Keep the v1 sum
        # so legacy consumers see a consistent number.
        "parser_missed_extractable": parser_missed_extractable + parser_false_positive,
        "true_unparseable": true_unparseable,
        "false_positive_rate": round(false_positive_rate, 4),
        # v2.3 — split the "miss" bucket. See `parser_span_alignment` top-level
        # section for the same numbers in a more discoverable shape.
        "parser_missed_aligned": missed_aligned,
        "parser_missed_misaligned": missed_misaligned,
        "parser_missed_no_output": missed_no_parser_output,
    }
    return summary, false_positive_rate


def _parser_span_alignment(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Top-level summary of how often the parser's extracted token agrees with
    the annotator's span. Surfaces the distinction between "parser is actually
    broken" (misaligned) and "parser extracted correctly but annotator used
    the spans-only workflow instead of marking parser_ok" (aligned).

    Computed only over cases with annotated spans (the only cases where this
    comparison is well-defined).
    """
    aligned = 0
    misaligned = 0
    no_parser_output = 0
    sample_misaligned: List[Dict[str, Any]] = []
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        spans = ann.get("spans") or []
        if not spans:
            continue
        pe = case.get("parser_extracted")
        pe_norm = _normalize_answer_text(pe)
        if not pe_norm:
            no_parser_output += 1
            continue
        if any(_is_aligned(pe, s.get("text") or "") for s in spans):
            aligned += 1
        else:
            misaligned += 1
            if len(sample_misaligned) < 5:
                sample_misaligned.append({
                    "case_id": case.get("case_id") or "",
                    "parser_extracted": pe,
                    "annotated_spans": [s.get("text") or "" for s in spans],
                    "parser_match_type": case.get("parser_match_type") or "",
                })

    total_comparable = aligned + misaligned + no_parser_output
    return {
        "total_comparable": total_comparable,
        "aligned_with_parser": aligned,
        "misaligned_with_parser": misaligned,
        "no_parser_output": no_parser_output,
        "alignment_ratio": round(aligned / total_comparable, 4) if total_comparable else 0.0,
        # Concrete examples of misalignment — the actual cases where the parser
        # latched onto a distractor token. Exactly what a refactor agent wants.
        "sample_misaligned": sample_misaligned,
    }


# ---------------------------------------------------------------------------
# Section: confusion matrix (parser_match_type × annotator_verdict)
# ---------------------------------------------------------------------------


def _confusion_matrix(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        pmt = str(case.get("parser_match_type") or "unknown")
        verdict = _verdict_of(case)
        matrix[pmt][verdict] += 1
    # Convert nested defaultdicts to plain dicts for JSON serialization.
    return {pmt: dict(verdicts) for pmt, verdicts in matrix.items()}


# ---------------------------------------------------------------------------
# Section: per-axis breakdowns (language, system_style, user_style, strategy)
# ---------------------------------------------------------------------------


def _axis_breakdown(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
    axis_key: str,
    default: str = "unknown",
) -> Dict[str, Dict[str, Any]]:
    """Group cases by an arbitrary axis (e.g. `language`, `system_style`) and
    compute verdict-class counts plus a `miss_rate` summary."""
    buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: Dict[str, int] = defaultdict(int)

    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        key = case.get(axis_key) or default
        if not isinstance(key, str):
            key = str(key)
        ann = case.get("annotation") or {}
        rcs = _get_response_classes(ann)
        spans = ann.get("spans") or []
        pe = case.get("parser_extracted")
        totals[key] += 1
        if "false_positive" in rcs:
            buckets[key]["parser_false_positive"] += 1
        elif spans:
            # Auto-infer parser_ok from span-parser alignment
            if pe and any(_is_aligned(pe, (s.get("text") or "")) for s in spans):
                buckets[key]["parser_was_correct"] += 1
            else:
                buckets[key]["parser_missed_extractable"] += 1
        elif any(c in _NON_RESOLVABLE_CLASSES for c in rcs):
            buckets[key]["true_unparseable"] += 1
        elif "verbose" in rcs:
            buckets[key]["verbose_correct"] += 1

    out: Dict[str, Dict[str, Any]] = {}
    for key, counts in buckets.items():
        total = totals[key]
        misses = counts.get("parser_missed_extractable", 0) + counts.get("parser_false_positive", 0)
        out[key] = {
            "total": total,
            "parser_was_correct": counts.get("parser_was_correct", 0),
            "parser_missed_extractable": counts.get("parser_missed_extractable", 0),
            "parser_false_positive": counts.get("parser_false_positive", 0),
            "true_unparseable": counts.get("true_unparseable", 0),
            "verbose_correct": counts.get("verbose_correct", 0),
            "miss_rate": round(misses / total, 4) if total else 0.0,
        }
    return out


def _strategy_breakdown(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Per-`parse_strategy` attribution. Especially useful for the
    `parser_false_positive` count — tells the coding agent exactly which
    parser strategy is producing distractor answers."""
    buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        strategy = case.get("parse_strategy") or "unknown"
        if not isinstance(strategy, str):
            strategy = str(strategy)
        ann = case.get("annotation") or {}
        rcs = _get_response_classes(ann)
        spans = ann.get("spans") or []
        buckets[strategy]["total_fired"] += 1
        if "false_positive" in rcs:
            buckets[strategy]["parser_false_positive"] += 1
        elif spans and "false_positive" not in rcs:
            buckets[strategy]["recoverable_miss"] += 1

    out: Dict[str, Dict[str, Any]] = {}
    for strategy, counts in buckets.items():
        total_fired = counts.get("total_fired", 0)
        fp = counts.get("parser_false_positive", 0)
        ok = counts.get("parser_ok", 0)
        annotator_verdicts = ok + fp
        out[strategy] = {
            "total_fired": total_fired,
            "parser_ok": ok,
            "parser_false_positive": fp,
            "recoverable_miss": counts.get("recoverable_miss", 0),
            # Conditional false-positive rate within this strategy. Only
            # meaningful when the annotator verified at least one case.
            "false_positive_rate": round(fp / annotator_verdicts, 4) if annotator_verdicts else 0.0,
        }
    return out


# ---------------------------------------------------------------------------
# Section: answer_when_missed
# ---------------------------------------------------------------------------


def _answer_when_missed(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    """For every case where the annotator marked spans (i.e. the parser missed
    a recoverable answer), aggregate:

      - by_expected: distribution of the *correct* answer label
      - by_extracted_distractor: distribution of what the parser extracted
        (only populated for parser_false_positive cases)
      - expected_distractor_pairs: cross-tab of (expected → extracted) pairs

    The pair view is the single most actionable diagnostic — a parser that
    consistently grabs `walk` when the answer is `drive` has a known bias.
    """
    by_expected: Counter = Counter()
    by_distractor: Counter = Counter()
    pair_counts: Counter = Counter()
    pair_examples: Dict[Tuple[str, str], List[str]] = defaultdict(list)

    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        spans = ann.get("spans") or []
        if not spans:
            continue
        expected = _normalize_answer(case.get("expected"))
        if expected:
            by_expected[expected] += 1

        rcs = _get_response_classes(ann)
        if "false_positive" in rcs:
            extracted = _normalize_answer(case.get("parser_extracted"))
            if extracted and expected and extracted != expected:
                by_distractor[extracted] += 1
                key = (expected, extracted)
                pair_counts[key] += 1
                if len(pair_examples[key]) < 5:
                    pair_examples[key].append(case.get("case_id", ""))

    pairs = [
        {
            "expected": exp,
            "parser_extracted": ext,
            "count": cnt,
            "example_case_ids": pair_examples[(exp, ext)],
        }
        for (exp, ext), cnt in pair_counts.most_common()
    ]

    return {
        "by_expected": dict(by_expected.most_common()),
        "by_extracted_distractor": dict(by_distractor.most_common()),
        "expected_distractor_pairs": pairs,
    }


# ---------------------------------------------------------------------------
# Section: span analysis (with confidence + weighted regex + context windows)
# ---------------------------------------------------------------------------


def _collect_span_records(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Flatten all (case, span) pairs into a list with full context attached."""
    out: List[Dict[str, Any]] = []
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        spans = ann.get("spans") or []
        if not spans:
            continue
        windows = case.get("context_windows") or []
        # Map char_start → context window for fast lookup when zipping spans.
        win_by_start = {w.get("char_start"): w for w in windows}
        case_id = case.get("case_id", "")
        parser_match_type = str(case.get("parser_match_type") or "")
        missed = parser_match_type in {"parse_error", "mismatch"}
        parser_extracted = case.get("parser_extracted")
        for s in spans:
            cw = win_by_start.get(s.get("char_start")) or {}
            out.append({
                "case_id": case_id,
                "language": case.get("language") or "en",
                "position": str(s.get("position") or "middle"),
                "format": str(s.get("format") or "plain"),
                "text": (s.get("text") or "").strip(),
                "before": cw.get("before", ""),
                "after": cw.get("after", ""),
                "sentence": cw.get("sentence", ""),
                "parser_extracted": parser_extracted,
                "parser_match_type": parser_match_type,
                "missed_by_existing": missed,
            })
    return out


# ---------------------------------------------------------------------------
# v2.1 — structural signals, prefix anchors, and regex test harness
# ---------------------------------------------------------------------------


def _structural_signals(before: str, after: str, text: str, language: str) -> Dict[str, bool]:
    """Return seven boolean signals describing the immediate context of a span.

    These are per-span facts; `_span_analysis` averages them over a group to
    produce `structural_ratios`.
    """
    before = before or ""
    after = after or ""
    text = text or ""

    line_start = before.endswith("\n") or before == ""
    paragraph_start = before.endswith("\n\n") or before == ""
    list_marker = bool(_LIST_MARKER_RE.search(before))
    label_colon = bool(_LABEL_COLON_RE.search(before))
    bold_wrap = before.rstrip(" ").endswith("**") and after.lstrip(" ").startswith("**")

    stripped_before = before.rstrip()
    stripped_after = after.lstrip()
    quote_wrap = False
    for open_ch, close_ch in (('"', '"'), ("'", "'"), ("`", "`")):
        if stripped_before.endswith(open_ch) and stripped_after.startswith(close_ch):
            quote_wrap = True
            break

    # Answer-label match: does `before` contain a known answer-label word
    # (answer / respuesta / réponse / відповідь / …) close to the span?
    label_re = _answer_label_re(language)
    answer_label_match = bool(label_re.search(before[-60:])) if before else False

    return {
        "line_start": line_start,
        "paragraph_start": paragraph_start,
        "list_marker": list_marker,
        "label_colon": label_colon,
        "bold_wrap": bold_wrap,
        "quote_wrap": quote_wrap,
        "answer_label_match": answer_label_match,
    }


_ANCHOR_TYPE_RANK: Dict[str, int] = {"label": 0, "format": 1, "phrase": 2}

# Distinctive trailing glyphs that count as a "format" anchor — emoji check-marks
# and arrow shapes commonly used by models right before the answer token.
_FORMAT_ANCHOR_GLYPHS: Tuple[str, ...] = ("✅", "✓", "➜", "→", "▶", "➤", "•")
_FORMAT_ANCHOR_MARKERS: Tuple[str, ...] = ("**", "__", "~~", "*", "_", "`")


def _classify_anchor(phrase: str) -> str:
    """Classify a prefix-anchor phrase for sorting + merging.

      - `label`  — ends with `:` or `：` (labelled answer — prime regex target)
      - `format` — ends with a markdown/emoji format marker (bold, italic, ✅, →)
      - `phrase` — flowing text mid-sentence, no locating cue (less useful)
    """
    if not phrase:
        return "phrase"
    stripped = phrase.rstrip()
    if stripped.endswith(":") or stripped.endswith("："):
        return "label"
    for marker in _FORMAT_ANCHOR_MARKERS + _FORMAT_ANCHOR_GLYPHS:
        if stripped.endswith(marker):
            return "format"
    return "phrase"


def _prefix_anchors_per_group(group_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Top trailing-token phrases of `before` for a single span group.

    Mirrors `_anchor_frequency`'s logic (contribute 1/2/3-gram suffixes per span
    + suppress shorter anchors subsumed by longer anchors at equal count) but
    scoped to a single (position, format) group. Emits up to 5 rows with a
    `ratio = count / group_size` so the coding agent sees what fraction of the
    group this anchor covers.

    Single-word stop-word anchors (`to`, `is`, `the`, raw `**`, …) are dropped
    as noise — they carry no locating information on their own.

    v2.4 — each anchor carries a `type` (`label` / `format` / `phrase`) and
    the output is sorted primarily by count desc, secondarily by anchor type
    (label > format > phrase) so meaningful anchors rise first at equal count.
    """
    if not group_records:
        return []

    counts: Counter = Counter()
    for rec in group_records:
        before_tokens = _tokenize(rec.get("before") or "")
        if not before_tokens:
            continue
        max_n = min(_ANCHOR_MAX_WORDS, len(before_tokens))
        for n in range(1, max_n + 1):
            anchor = tuple(before_tokens[-n:])
            if n == 1 and len(anchor[0]) <= 1:
                continue
            counts[anchor] += 1

    if not counts:
        return []

    # Suppress shorter anchors whose count equals a longer anchor containing
    # them (prefer specificity — e.g. "final answer" beats "answer" at tie).
    by_count_desc = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    suppressed: set[Tuple[str, ...]] = set()
    for anchor, cnt in by_count_desc:
        for shorter_n in range(1, len(anchor)):
            shorter = anchor[-shorter_n:]
            if counts.get(shorter) == cnt:
                suppressed.add(shorter)

    group_size = len(group_records)
    rows: List[Dict[str, Any]] = []
    for anchor, cnt in by_count_desc:
        if cnt < 2 or anchor in suppressed:
            continue
        # Drop single-word anchors that are just stop-words / markdown artifacts.
        if len(anchor) == 1 and anchor[0] in _PREFIX_STOP_WORDS:
            continue
        phrase = " ".join(anchor)
        rows.append({
            "phrase": phrase,
            "count": cnt,
            "ratio": round(cnt / group_size, 4) if group_size else 0.0,
            "type": _classify_anchor(phrase),
        })

    # Secondary sort: label > format > phrase at equal count. `sorted` is
    # stable, so primary count-desc order is preserved where counts differ.
    rows.sort(key=lambda r: (-r["count"], _ANCHOR_TYPE_RANK.get(r["type"], 3)))
    return rows[:5]


# ---------------------------------------------------------------------------
# Context-anchored regex generation (v2.2) — builds a locate-anchor regex
# from the shared `before` context + the group's markdown format, instead of
# treating the span text itself as the anchor. This is the regex the parser
# should actually use: "find the label, capture the answer that follows".
# ---------------------------------------------------------------------------


def _format_capture(fmt: str) -> str:
    """Return the regex capture group shape appropriate for a span format.

    The captured value ends up in group 1 so the parser can slot it into its
    existing plumbing without caring which format fired.
    """
    if fmt == "bold":
        # Match `**answer**` (non-greedy inside the markers).
        return r"\*\*([^*\n]+?)\*\*"
    if fmt == "italic":
        # Match `_answer_` OR `*answer*` (single-char markers).
        return r"(?:_([^_\n]+?)_|\*([^*\n]+?)\*)"
    if fmt == "strikethrough":
        return r"~~([^~\n]+?)~~"
    if fmt == "header":
        # A full header line: `#..# heading text`.
        return r"(?:^|\n)#{1,6}\s+([^\n]+)"
    if fmt == "boxed":
        return r"\\boxed\{([^{}\n]+)\}"
    if fmt == "label":
        # Labels are handled via the prefix anchor already; capture until EOL
        # or period, whichever comes first.
        return r"([^.\n]+?)(?:[.\n]|$)"
    # plain / other — capture one word (safe default).
    return r"(\w+)"


def _label_atom(phrase: str) -> str:
    """Given a label-type anchor phrase (ends with `:`), return the atomic
    label word used for disjunction deduplication.

      - `recommendation:` → `recommendation`
      - `choice. recommendation:` → `recommendation` (anchor's final token
        minus the trailing `:`, after the last sentence/line boundary)
      - `recommended action:` → `action` (conservative: last whitespace token)

    The "last whitespace token" heuristic intentionally avoids over-merging
    multi-word labels like `recommended action` with single-word `action` —
    they'll be treated as separate atoms, which is the cautious choice.
    """
    if not phrase:
        return ""
    stripped = phrase.rstrip().rstrip(":：").rstrip()
    # Split on sentence/list boundaries so `choice. recommendation` → `recommendation`.
    for sep in (". ", "\n", "- ", "* "):
        idx = stripped.rfind(sep)
        if idx >= 0:
            stripped = stripped[idx + len(sep):]
    # Use the last whitespace token as the final atom.
    parts = stripped.split()
    return parts[-1] if parts else ""


def _merged_label_disjunction(
    prefix_anchors: List[Dict[str, Any]],
    fmt: str,
    group_size: int,
) -> Optional[Dict[str, Any]]:
    """Synthesize a disjunction across label-type anchors sharing a `:`
    terminator. Turns two separate 50%-coverage regexes like

        (?i)recommendation:\\s*(...)
        (?i)conclusion:\\s*(...)

    into a single 100%-coverage regex:

        (?i)(?:recommendation|conclusion)\\s*[:：]\\s*(...)

    Returns None when fewer than 2 distinct label atoms are available —
    falls back to the existing per-anchor `context_anchor` candidates.
    """
    label_anchors = [a for a in prefix_anchors if a.get("type") == "label"]
    if len(label_anchors) < 2:
        return None

    # Dedupe atoms while preserving anchor counts.
    atom_counts: Dict[str, int] = {}
    for a in label_anchors:
        atom = _label_atom(a.get("phrase") or "")
        if not atom:
            continue
        atom_counts[atom] = atom_counts.get(atom, 0) + int(a.get("count") or 0)

    if len(atom_counts) < 2:
        return None

    # Order atoms by their contribution, so the regex reads logically.
    atoms_sorted = sorted(atom_counts.items(), key=lambda kv: -kv[1])
    atoms = [a for a, _ in atoms_sorted]
    disjunction = "|".join(re.escape(a) for a in atoms)

    capture = _format_capture(fmt)
    pattern = rf"(?i)(?:{disjunction})\s*[:：]\s*{capture}"
    total_support = sum(atom_counts.values())
    return {
        "pattern": pattern,
        "kind": "merged_label_disjunction",
        "support": min(total_support, group_size),
        "anchor_phrase": None,
        "anchor_words": atoms,
        "participating_atoms": atoms,
    }


def _filter_candidates(
    harness_rows: List[Dict[str, Any]],
    group_size: int,
) -> List[Dict[str, Any]]:
    """Post-harness filter: drop candidates that neither fire nor capture.

    Rules:
      - `format_only` — always keep (safety-net for distinctive formats)
      - compile errors (`match_rate == -1.0`) — keep (bug signal for agent)
      - support / group_size < 0.1 AND support < 2 — drop
      - match_rate < 0.1 AND capture_contains_rate < 0.1 — drop (no signal)
    """
    min_support_ratio = 0.1
    min_absolute_support = 2
    min_match_or_capture = 0.1

    kept: List[Dict[str, Any]] = []
    for r in harness_rows:
        kind = r.get("kind") or ""
        if kind == "format_only" or r.get("match_rate") == -1.0:
            kept.append(r)
            continue
        support = int(r.get("support") or 0)
        if support < min_absolute_support and (group_size == 0 or support / group_size < min_support_ratio):
            continue
        match_rate = float(r.get("match_rate") or 0.0)
        capture_rate = float(r.get("capture_contains_rate") or 0.0)
        if match_rate < min_match_or_capture and capture_rate < min_match_or_capture:
            continue
        kept.append(r)
    return kept


def _context_anchored_regex(
    prefix_anchors: List[Dict[str, Any]],
    fmt: str,
    group_size: int,
    example_texts: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Build up to 3 regex candidates for a span group.

    Produces, in priority order:
      1. **context_anchor** — anchored on `before` prefix + format-aware
         capture. The preferred shape: "find the label, grab the answer."
      2. **format_only** — bare format wrapper (for distinctive formats only).
      3. **text_pattern** — legacy-style anchor derived from the longest
         common word prefix of span texts. Fallback for when `before` context
         is absent (e.g. synthetic test data, sparse annotations).

    All patterns use the inline `(?i)` flag so they match case-insensitively —
    the model may write "Answer:" or "answer:" and the parser shouldn't care.
    """
    capture = _format_capture(fmt)
    candidates: List[Dict[str, Any]] = []

    # v2.4 — try a merged-label-disjunction first. When a group has 2+ distinct
    # label atoms (e.g. `recommendation:` + `conclusion:`), a single disjunction
    # regex covers the union at ~100% where each individual anchor tops out at
    # ~50%. If only one atom is available we fall through to per-anchor
    # context_anchor candidates below.
    merged = _merged_label_disjunction(prefix_anchors, fmt, group_size)
    if merged is not None:
        candidates.append(merged)

    # When the capture already embeds its own opening marker (e.g. bold's
    # `\*\*(...)\*\*`), and the anchor's trailing token is literally that
    # same opening marker (because the prefix_anchor logic includes the
    # `**` that immediately precedes the span), strip it from the anchor
    # so we don't require the marker twice in a row.
    opening_markers_by_fmt = {
        "bold": {"**"},
        "italic": {"_", "*"},
        "strikethrough": {"~~"},
    }
    trailing_markers_to_strip = opening_markers_by_fmt.get(fmt, set())

    for anchor_row in prefix_anchors[:2]:
        phrase = anchor_row.get("phrase") or ""
        count = int(anchor_row.get("count") or 0)
        if not phrase or count < 2:
            continue
        tokens = phrase.split()
        while tokens and tokens[-1] in trailing_markers_to_strip:
            tokens.pop()
        if not tokens:
            continue
        anchor_pattern = r"\s+".join(re.escape(t) for t in tokens)
        pattern = rf"(?i){anchor_pattern}\s*{capture}"
        candidates.append({
            "pattern": pattern,
            "kind": "context_anchor",
            "support": count,
            "anchor_phrase": " ".join(tokens),
            "anchor_words": tokens,
        })

    # Format-only safety net for distinctive formats.
    if fmt in {"bold", "italic", "strikethrough", "boxed", "header"}:
        candidates.append({
            "pattern": f"(?i){capture}",
            "kind": "format_only",
            "support": group_size,
            "anchor_phrase": None,
            "anchor_words": None,
        })

    # Text-pattern fallback: longest common word prefix of the span texts.
    # Useful for multi-word annotations like `"you should drive"` where the
    # phrase itself carries the anchor.
    if example_texts:
        legacy, _ = _auto_regex_with_meta(example_texts)
        for cand in legacy:
            # Tag as text_pattern so the agent can tell it apart from a true
            # locate-then-capture regex.
            pattern = cand.get("pattern") or ""
            if pattern and not pattern.startswith("(?i)"):
                pattern = f"(?i){pattern}"
            candidates.append({
                "pattern": pattern,
                "kind": "text_pattern",
                "support": cand.get("support", 0),
                "anchor_phrase": None,
                "anchor_words": cand.get("anchor_words"),
            })

    # Cap at 4 — leaves room for: merged_label_disjunction + 2×context_anchor
    # + format_only OR text_pattern fallback.
    return candidates[:4]


# ---------------------------------------------------------------------------
# Label taxonomy — for each group, tally which answer-label words appear in
# `before`. Breaks down `answer_label_match_ratio` into actionable detail.
# ---------------------------------------------------------------------------


def _label_taxonomy(group_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return `[{label: "answer", count: 6}, {label: "recommendation", count: 3}, ...]`
    sorted by count desc. Multiple labels in one `before` all contribute.
    """
    counts: Counter = Counter()
    for rec in group_records:
        before = rec.get("before") or ""
        if not before:
            continue
        for m in _LABEL_WORDS_RE.finditer(before):
            counts[m.group(1).lower()] += 1
    return [{"label": lab, "count": cnt} for lab, cnt in counts.most_common(8)]


# ---------------------------------------------------------------------------
# Model answer distribution — histogram of normalized span texts. Shows what
# the *model* chose, not what was expected. Essential when `by_expected` is
# uniform (e.g. carwash: all 100 expect "drive").
# ---------------------------------------------------------------------------


def _strip_markdown(text: str) -> str:
    """Strip common markdown wrappers so `Walk`, `**Walk**`, `_Walk_` collapse
    to the same histogram bucket."""
    t = (text or "").strip()
    # Iteratively peel matching wrapper pairs.
    for _ in range(4):
        changed = False
        for open_m, close_m in (("**", "**"), ("__", "__"), ("*", "*"),
                                ("_", "_"), ("~~", "~~"), ("`", "`")):
            if t.startswith(open_m) and t.endswith(close_m) and len(t) > len(open_m) + len(close_m):
                t = t[len(open_m):-len(close_m)].strip()
                changed = True
        if not changed:
            break
    return t.lower()


def _normalize_answer_text(text: Any) -> str:
    """Lowercase + strip markdown + trim — used to compare parser output to
    annotated span text. Returns "" for None / empty input."""
    if text is None:
        return ""
    return _strip_markdown(str(text)).strip()


def _is_aligned(parser_extracted: Any, span_text: Any) -> bool:
    """Whether the parser's output agrees with the annotator's answer span.

    Alignment semantics (v2.3):
      - Exact normalize match → aligned.
      - Single-word parser output that appears as a whole word in the
        (multi-word) annotated span → aligned. Handles the common case where
        the annotator marks `Walk to the carwash` and the parser reports
        `walk`.
      - Symmetric: single-word annotated span appearing in the parser's
        (multi-word) output → aligned. Handles the case where the parser
        returns `walk or drive` and the annotator has isolated `walk`.
      - Otherwise misaligned. Notably: different stems (`walking` vs `walk`)
        DO count as misaligned here — surfacing those differences is the whole
        point of the metric.
    """
    p = _normalize_answer_text(parser_extracted)
    s = _normalize_answer_text(span_text)
    if not p or not s:
        return False
    if p == s:
        return True
    p_words = p.split()
    s_words = s.split()
    if len(p_words) == 1 and p in s_words:
        return True
    if len(s_words) == 1 and s in p_words:
        return True
    return False


def _model_answer_stats(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Tuple[Dict[str, int], Dict[str, Dict[str, Any]]]:
    """Return a `(distribution, variants)` tuple over every annotated span.

      - `distribution`: `{normalized_answer: count}` — markdown stripped and
        lowercased, collapses `Walk`/`**Walk**`/`WALK` into a single `walk`
        bucket. Matches the legacy v2.2 shape.
      - `variants`: `{normalized_answer: {total, variants: [{text, count}]}}` —
        preserves the raw span texts (case + markdown intact) per bucket, top
        10 variants by count. Lets a parser-refactor agent see whether the
        bucket needs case-normalization, markdown-stripping, or phrase-trim
        before matching.
    """
    normalized_counts: Counter = Counter()
    variant_counts: Dict[str, Counter] = {}
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        for s in ann.get("spans") or []:
            raw = (s.get("text") or "").strip()
            if not raw:
                continue
            norm = _strip_markdown(raw)
            if not norm:
                continue
            normalized_counts[norm] += 1
            variant_counts.setdefault(norm, Counter())[raw] += 1

    distribution = dict(normalized_counts.most_common())
    variants: Dict[str, Dict[str, Any]] = {}
    for norm, total in normalized_counts.most_common():
        variant_counter = variant_counts.get(norm) or Counter()
        variants[norm] = {
            "total": total,
            "variants": [
                {"text": text, "count": count}
                for text, count in variant_counter.most_common(10)
            ],
        }
    return distribution, variants


def _model_answer_distribution(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, int]:
    """Backwards-compat wrapper returning only the flat distribution."""
    distribution, _ = _model_answer_stats(annotation_files, result_idx)
    return distribution


# ---------------------------------------------------------------------------
# Parser-vs-annotator diff — surface `parser_extracted` next to each example
# span so the agent sees what the parser said vs what the annotator marked.
# ---------------------------------------------------------------------------


def _regex_test_harness(
    examples: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Score each candidate regex against the full set of example contexts.

    Each example's test string is `before + text + after`, with a fallback to
    the containing `sentence` when present. For every candidate emits:

      - `match_rate` / `matched_count` / `total` — the regex fires *at all*
      - `capture_exact_rate` — fraction of matches where the capture group
        equals the annotated span text (after markdown + case normalization)
      - `capture_contains_rate` — fraction where capture aligns with the span
        (same alignment semantics as `_is_aligned`: exact or single-word
        inclusion). This is the REAL usefulness measure — "match_rate high,
        capture_contains_rate low" means the regex fires but grabs the wrong
        substring.
      - `sample_captures` — up to 3 concrete `{case_id, captured, annotated,
        aligned}` rows so the agent can eyeball the regex's output without
        running it.

    Compile errors produce `match_rate = -1.0`.
    """
    total = len(examples)
    out: List[Dict[str, Any]] = []
    if total == 0 or not candidates:
        return out

    test_data: List[Tuple[str, Dict[str, Any]]] = []
    for e in examples:
        ctx = f"{e.get('before', '')}{e.get('text', '')}{e.get('after', '')}"
        sentence = e.get("sentence") or ""
        test_string = sentence if len(sentence) > len(ctx) else ctx
        test_data.append((test_string, e))

    for c in candidates:
        pattern = c.get("pattern") or ""
        try:
            compiled = re.compile(pattern)
        except re.error:
            out.append({
                **c,
                "match_rate": -1.0,
                "matched_count": 0,
                "total": total,
                "capture_exact_rate": 0.0,
                "capture_contains_rate": 0.0,
                "sample_captures": [],
            })
            continue

        matched = 0
        exact = 0
        contains = 0
        samples: List[Dict[str, Any]] = []
        for test_string, ex in test_data:
            m = compiled.search(test_string)
            if not m:
                continue
            matched += 1
            annotated = ex.get("text") or ""
            # Capture is group 1 when the regex defines one; fall back to the
            # whole match (group 0) so `(\w+)`-less patterns still produce a
            # sensible captured value for diagnostics.
            try:
                captured = m.group(1) if m.lastindex else m.group(0)
            except (IndexError, re.error):
                captured = m.group(0)
            captured = captured or ""
            exact_match = _normalize_answer_text(captured) == _normalize_answer_text(annotated)
            contains_match = _is_aligned(captured, annotated)
            if exact_match:
                exact += 1
            if contains_match:
                contains += 1
            # Try to include one misaligned sample so the agent sees failure
            # modes, not just successes.
            if len(samples) < 3:
                samples.append({
                    "case_id": ex.get("case_id") or "",
                    "captured": captured,
                    "annotated": annotated,
                    "exact_match": exact_match,
                    "aligned": contains_match,
                })

        out.append({
            **c,
            "match_rate": round(matched / total, 4) if total else 0.0,
            "matched_count": matched,
            "total": total,
            "capture_exact_rate": round(exact / total, 4) if total else 0.0,
            "capture_contains_rate": round(contains / total, 4) if total else 0.0,
            "sample_captures": samples,
        })
    return out


def _span_analysis(span_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group spans by (position, format) and produce per-group regex
    candidates with confidence + per-span context windows + v2.1 structural
    signals / prefix anchors / regex test harness."""
    groups: Dict[Tuple[str, str], Dict[str, Any]] = {}
    group_records: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    signal_tallies: Dict[Tuple[str, str], Counter] = defaultdict(Counter)

    for rec in span_records:
        key = (rec["position"], rec["format"])
        bucket = groups.setdefault(key, {
            "position": rec["position"],
            "format": rec["format"],
            "count": 0,
            "examples": [],
            "languages": set(),
            "missed_by_existing": False,
        })
        bucket["count"] += 1
        bucket["languages"].add(rec["language"])
        if rec["missed_by_existing"]:
            bucket["missed_by_existing"] = True
        if rec["text"] and len(bucket["examples"]) < 5:
            bucket["examples"].append({
                "text": rec["text"],
                "before": rec["before"],
                "after": rec["after"],
                "sentence": rec.get("sentence") or "",
                "case_id": rec["case_id"],
                "language": rec["language"],
                # v2.2: expose what the parser extracted for this case, so the
                # agent can see annotator-vs-parser disagreement inline.
                "parser_extracted": rec.get("parser_extracted"),
                "parser_match_type": rec.get("parser_match_type") or "",
            })

        # Collect every record (not just the 5 exemplars) so structural ratios,
        # prefix anchors, and the regex harness reflect the full population.
        group_records[key].append(rec)
        signals = _structural_signals(
            rec.get("before") or "",
            rec.get("after") or "",
            rec.get("text") or "",
            rec.get("language") or "en",
        )
        for k, v in signals.items():
            if v:
                signal_tallies[key][k] += 1

    ordered = sorted(groups.values(), key=lambda g: (-g["count"], g["position"], g["format"]))

    out: List[Dict[str, Any]] = []
    for g in ordered:
        key = (g["position"], g["format"])
        total = g["count"]

        # Structural ratios — averaged across every record in the group.
        tally = signal_tallies[key]
        structural_ratios = {
            sig: round(tally.get(sig, 0) / total, 4) if total else 0.0
            for sig in (
                "line_start",
                "paragraph_start",
                "list_marker",
                "label_colon",
                "bold_wrap",
                "quote_wrap",
                "answer_label_match",
            )
        }

        prefix_anchors = _prefix_anchors_per_group(group_records[key])
        label_taxonomy = _label_taxonomy(group_records[key])

        # v2.2: context-anchored regex generation. The OLD generator used the
        # span text itself as the prefix (e.g. `walk\s+(\w+)`), which captures
        # what comes AFTER the answer — useless. The new generator anchors on
        # the shared `before` phrase (e.g. `**Answer:**\s*\*\*([^*]+)\*\*`)
        # with a format-aware capture, so the parser gets a locate-then-extract
        # pattern that actually finds answers. Text-pattern fallback kicks in
        # when `before` context is sparse.
        example_texts_for_fallback = [r.get("text") or "" for r in group_records[key]]
        regex_candidates = _context_anchored_regex(
            prefix_anchors, g["format"], total, example_texts=example_texts_for_fallback,
        )

        # Confidence:
        #   - high   — top anchor ratio ≥ 0.5 AND group size ≥ 3
        #   - medium — top anchor ratio ≥ 0.25 OR format-only candidate emitted
        #   - low    — otherwise
        top_ratio = prefix_anchors[0]["ratio"] if prefix_anchors else 0.0
        if total >= 3 and top_ratio >= 0.5:
            confidence = "high"
        elif total >= 3 and (top_ratio >= 0.25 or any(c["kind"] == "format_only" for c in regex_candidates)):
            confidence = "medium"
        else:
            confidence = "low"

        # Regex test harness: score every candidate against every example's
        # wider context so we surface real-world match rates, not just the
        # 5 exemplars used to derive the anchor.
        harness_examples: List[Dict[str, Any]] = [
            {
                "text": r.get("text") or "",
                "before": r.get("before") or "",
                "after": r.get("after") or "",
                "sentence": r.get("sentence") or "",
                "case_id": r.get("case_id") or "",
            }
            for r in group_records[key]
        ]
        regex_test = _regex_test_harness(harness_examples, regex_candidates)
        # Sort candidates by match_rate so the best-performing regex is first.
        regex_test_sorted = sorted(regex_test, key=lambda r: (-r["match_rate"], -r.get("support", 0)))
        # v2.4 — drop candidates that neither fire nor capture. Keeps the
        # regex list signal-dense for the agent.
        regex_test_sorted = _filter_candidates(regex_test_sorted, total)

        out.append({
            "position": g["position"],
            "format": g["format"],
            "count": total,
            "languages": sorted(g["languages"]),
            "example_spans": g["examples"],
            "suggested_strategy": FORMAT_TO_STRATEGY.get(g["format"], "full_text"),
            "suggested_regex": regex_candidates,
            "confidence": confidence,
            "missed_by_existing": g["missed_by_existing"],
            # v2.1 additions ---------------------------------------------
            "structural_ratios": structural_ratios,
            "prefix_anchors": prefix_anchors,
            "regex_test": regex_test_sorted,
            # v2.2 additions ---------------------------------------------
            "label_taxonomy": label_taxonomy,
        })
    return out


def _split_long_tail(
    span_groups: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """v2.5 — partition span groups into rich (count ≥ threshold) + long-tail
    (count < threshold). Long-tail entries drop per-group rollups and keep
    only `position` / `format` / `count` plus a single representative example,
    since n ≤ 3 carries no statistical signal for structural_ratios /
    prefix_anchors / regex_test.

    Guard: the collapse only applies when at least one rich group exists.
    When every group is below threshold, those small groups ARE the signal
    (small sessions, focused testsets) and collapsing them would erase the
    entire report. The "long tail" concept requires a head to compare against.
    """
    has_rich = any(g.get("count", 0) >= _LONG_TAIL_THRESHOLD for g in span_groups)
    if not has_rich:
        return list(span_groups), []

    rich: List[Dict[str, Any]] = []
    long_tail: List[Dict[str, Any]] = []
    for g in span_groups:
        if g.get("count", 0) >= _LONG_TAIL_THRESHOLD:
            rich.append(g)
            continue
        examples = g.get("example_spans") or []
        long_tail.append({
            "position": g["position"],
            "format": g["format"],
            "count": g.get("count", 0),
            "example": examples[0] if examples else None,
        })
    return rich, long_tail


def _ordering_hints(span_groups: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    hints: List[Dict[str, str]] = []
    for g in span_groups:
        if (
            g["position"] == "end"
            and g["format"] == "plain"
            and g["count"] >= 4
            and g.get("missed_by_existing")
        ):
            hints.append({
                "observation": (
                    f"{g['count']} missed answers were at position 'end', format 'plain'. "
                    "Current strategy 'full_text' scans start-to-end and may hit wrong tokens first."
                ),
                "recommendation": "Promote end_sentences strategy above full_text for this plugin.",
            })
            break
    return hints


# ---------------------------------------------------------------------------
# Section: anchor frequency (cross-group)
# ---------------------------------------------------------------------------


def _anchor_frequency(span_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tally which short phrases (1–3 trailing words of `before`) most often
    immediately precede an annotated answer. Cross-cuts (position, format) so
    the coding agent can see anchors that work regardless of formatting.

    Algorithm: each span contributes its 1-gram, 2-gram, and 3-gram trailing
    suffixes (so common anchors aren't masked by varying outer prefixes — e.g.
    "After thought, you should" and "I think you should" both contribute
    "you should" at the bigram level). We then suppress shorter anchors whose
    count exactly equals a longer anchor that contains them — prefers
    specificity ("you should" beats "should" when both have count=3).
    """
    counts: Counter = Counter()
    languages: Dict[Tuple[str, ...], set] = defaultdict(set)
    answers: Dict[Tuple[str, ...], list] = defaultdict(list)

    for rec in span_records:
        before_tokens = _tokenize(rec["before"])
        if not before_tokens:
            continue
        max_n = min(_ANCHOR_MAX_WORDS, len(before_tokens))
        for n in range(1, max_n + 1):
            anchor = tuple(before_tokens[-n:])
            # Skip lone single-character anchors — too noisy.
            if n == 1 and len(anchor[0]) <= 1:
                continue
            counts[anchor] += 1
            languages[anchor].add(rec["language"])
            ans = (rec["text"] or "").strip().lower()
            if ans and ans not in answers[anchor]:
                answers[anchor].append(ans)

    # Suppress shorter anchors whose count equals a longer anchor that contains
    # them — keeps the table focused on the most specific phrasing.
    by_count_desc = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    suppressed: set[Tuple[str, ...]] = set()
    for anchor, cnt in by_count_desc:
        for shorter_n in range(1, len(anchor)):
            shorter = anchor[-shorter_n:]
            if counts.get(shorter) == cnt:
                suppressed.add(shorter)

    rows: List[Dict[str, Any]] = []
    for anchor, cnt in by_count_desc:
        if cnt < 2 or anchor in suppressed:
            continue
        rows.append({
            "anchor": " ".join(anchor),
            "count": cnt,
            "languages": sorted(languages[anchor]),
            "spans_seen_in": answers[anchor][:6],
        })
        if len(rows) >= 20:
            break
    return rows


# ---------------------------------------------------------------------------
# Section: response classes + annotator notes
# ---------------------------------------------------------------------------


def _response_class_counts(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, int]:
    """v2.5 — folded into `summary.response_class_counts`. Returns only the
    non-zero buckets so downstream `Object.entries()` consumers render a
    dense list without filtering. The synthetic `parser_missed` bucket
    (count of cases that carry spans) is preserved since it's the only
    number not otherwise present in `summary`.
    """
    counts: Dict[str, int] = {}
    parser_missed = 0
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        rcs = _get_response_classes(ann)
        spans = ann.get("spans") or []
        for cls in rcs:
            counts[cls] = counts.get(cls, 0) + 1
        if spans:
            parser_missed += 1
    if parser_missed:
        counts["parser_missed"] = parser_missed
    return {k: v for k, v in counts.items() if v > 0}


def _data_quality(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
    breakdowns: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Top-level diagnostic about the report's own input quality.

    - Flags missing/uniform fields that silently degrade analysis
    - Lists which axis breakdowns were suppressed (single-bucket → no signal)
    - Gives the agent a concrete TODO list for unlocking richer diagnostics
    """
    warnings: List[Dict[str, str]] = []
    suppressed_sections: List[str] = []

    total = 0
    strategy_unknown = 0
    languages: set[str] = set()
    system_styles: set[str] = set()
    user_styles: set[str] = set()
    expected_answers: set[str] = set()

    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        total += 1
        strat = case.get("parse_strategy")
        if not strat or strat == "unknown":
            strategy_unknown += 1
        languages.add(case.get("language") or "unknown")
        ss = case.get("system_style")
        system_styles.add(ss if ss is not None else "unspecified")
        us = case.get("user_style")
        user_styles.add(us if us is not None else "unspecified")
        exp = _normalize_answer_text(case.get("expected"))
        if exp:
            expected_answers.add(exp)

    if total > 0 and strategy_unknown / total >= 0.9:
        warnings.append({
            "code": "no_parse_strategy",
            "detail": (
                f"{strategy_unknown}/{total} cases have parse_strategy='unknown'. "
                "Strategy_breakdown can't attribute false-positives to specific "
                "parser strategies. Emit parse_strategy from your plugin parser."
            ),
        })
        # v2.5 — without parse_strategy the breakdown collapses to a single
        # `unknown` row carrying no signal. Suppress it so the JSON stays
        # dense and the agent isn't tempted to read it.
        suppressed_sections.append("strategy_breakdown")

    # Suppress single-bucket axis breakdowns — they repeat the session-level
    # totals and clutter the JSON.
    for name, label in (
        ("language_breakdown", "language"),
        ("config_breakdown", "system_style"),
        ("user_style_breakdown", "user_style"),
    ):
        buckets = breakdowns.get(name) or {}
        if len(buckets) <= 1:
            suppressed_sections.append(name)
            warnings.append({
                "code": f"uniform_{label}",
                "detail": (
                    f"all cases share a single {label} ({next(iter(buckets)) if buckets else '—'}). "
                    f"{name} suppressed — add variety to the testset to unlock this axis."
                ),
            })

    if len(expected_answers) <= 1:
        warnings.append({
            "code": "uniform_expected",
            "detail": (
                f"all cases expect the same answer "
                f"({next(iter(expected_answers)) if expected_answers else '—'}). "
                "`answer_when_missed.by_expected` carries no signal."
            ),
        })
        # v2.5 — `by_expected` tautologically reports `{single_answer: N}` and
        # the sibling distractor/pair blocks go empty; report that the whole
        # section is suppressed rather than emitting an inert stub.
        suppressed_sections.append("answer_when_missed.by_expected")

    return {
        "warnings": warnings,
        "suppressed_sections": suppressed_sections,
    }


def _collect_notes(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Surface non-empty annotator notes — these often contain the meta-pattern
    insight that no aggregator can derive on its own."""
    out: List[Dict[str, Any]] = []
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        note = (ann.get("annotator_note") or "").strip()
        if not note:
            continue
        out.append({
            "case_id": case.get("case_id", ""),
            "language": case.get("language") or "en",
            "verdict": _verdict_of(case),
            "note": note,
        })
    return out


# ---------------------------------------------------------------------------
# v2.6 — new mark-type aggregation (context_anchors, answer_keywords,
# negative_spans, negative_keywords)
# ---------------------------------------------------------------------------


def _collect_negative_records(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Flatten all negative marks into a list of records.

    v2.7 (Phase 1): the `negative_span` vs `negative_keyword` distinction is
    gone at the semantic level. Legacy sidecars that still carry
    ``negative_keywords`` entries (e.g. loaded from the DB between a schema
    migration and the next save) are folded on-the-fly so the report shape
    stays single-typed regardless of in-flight migration state.

    Each record carries the mark text, surrounding context, and a pointer back
    to the annotated correct span (if any) so the agent can see what the parser
    should have extracted instead.
    """
    out: List[Dict[str, Any]] = []
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        case_id = case.get("case_id", "")
        language = case.get("language") or "en"
        parse_strategy = case.get("parse_strategy") or "unknown"
        spans = ann.get("spans") or []
        correct_span = (spans[0].get("text") or "").strip() if spans else ""
        windows = case.get("context_windows") or []
        win_by_start = {w.get("char_start"): w for w in windows}
        # v2.7: defensive fold of both arrays into a single negative list. Old
        # annotations that haven't been re-saved yet may still have entries in
        # `negative_keywords`; new annotations only populate `negative_spans`.
        negatives = list(ann.get("negative_spans") or []) + list(ann.get("negative_keywords") or [])
        for mark in negatives:
            text = (mark.get("text") or "").strip()
            if not text:
                continue
            char_start = int(mark.get("char_start") or 0)
            char_end = int(mark.get("char_end") or 0)
            cw = win_by_start.get(char_start) or {}
            # Phase 2: preserve the optional `source` discriminator so
            # downstream tooling can filter auto-inferred vs manual marks.
            # Absent on pre-Phase-2 sidecars → implicit "manual".
            source = mark.get("source") or "manual"
            out.append({
                "text": text,
                "char_start": char_start,
                "char_end": char_end,
                "before": cw.get("before", ""),
                "after": cw.get("after", ""),
                "case_id": case_id,
                "language": language,
                "parse_strategy": parse_strategy,
                "correct_span": correct_span,
                "source": source,
            })
    return out


def _negative_span_analysis(negative_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group negative records by normalized text, return a list of group dicts.

    v2.7: no longer emits a `mark_type` field — the single-type collapse in
    Phase 1 made it redundant. Legacy v2.6 reports on disk keep their
    `mark_type` field; the TS type has narrowed it to optional.
    """
    from collections import defaultdict

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in negative_records:
        key = _normalize_answer_text(rec["text"]) or rec["text"].lower()
        groups[key].append(rec)

    out: List[Dict[str, Any]] = []
    for norm_text, records in sorted(groups.items(), key=lambda x: -len(x[1])):
        rep_text = records[0]["text"]  # representative raw text
        out.append({
            "text": rep_text,
            "normalized_text": norm_text,
            "count": len(records),
            "example_negatives": [
                {
                    "text": r["text"],
                    "before": r["before"],
                    "after": r["after"],
                    "case_id": r["case_id"],
                    "language": r["language"],
                    "correct_span": r["correct_span"],
                    "parse_strategy": r["parse_strategy"],
                    # Phase 2: tag each example with its source so downstream
                    # agents can filter auto-inferred marks if they want
                    # manual-only signal (default behaviour is to merge).
                    "source": r.get("source", "manual"),
                }
                for r in records[:5]
            ],
        })
    return out


def _answer_keyword_distribution(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, int]:
    """Return frequency distribution of manually-tagged answer keywords.

    Only populated when at least one annotation has `answer_keywords`. When
    present, this is higher-confidence signal than the auto-inferred
    `model_answer_distribution` (which is derived from span text).
    """
    counts: Dict[str, int] = {}
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        for kw in (ann.get("answer_keywords") or []):
            text = (kw.get("text") or "").strip()
            if not text:
                continue
            norm = _normalize_answer_text(text) or text.lower()
            counts[norm] = counts.get(norm, 0) + 1
    return counts


def _context_anchor_groups(
    annotation_files: List[Dict[str, Any]],
    result_idx: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Group manually-marked context anchors by normalized text."""
    from collections import defaultdict

    # Map norm → (representative_text, [case_ids])
    groups: Dict[str, tuple] = {}
    for _, case in _iter_enriched_cases(annotation_files, result_idx):
        ann = case.get("annotation") or {}
        case_id = case.get("case_id", "")
        for anchor in (ann.get("context_anchors") or []):
            text = (anchor.get("text") or "").strip()
            if not text:
                continue
            norm = text.lower().strip("*_: ")
            if norm not in groups:
                groups[norm] = (text, [])
            groups[norm][1].append(case_id)

    return [
        {
            "text": rep_text,
            "count": len(case_ids),
            "example_cases": list(dict.fromkeys(case_ids))[:3],
        }
        for rep_text, case_ids in sorted(groups.values(), key=lambda v: -len(v[1]))
    ]


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def build_report(
    annotation_files: List[Dict[str, Any]],
    source_files: Optional[List[str]] = None,
    result_payloads_by_file: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the full v2 improvement report.

    Args:
        annotation_files: Loaded annotation sidecar payloads.
        source_files: Filenames the annotations came from — echoed in the
            report for traceability.
        result_payloads_by_file: Optional `{filename: result_payload}` map used
            to back-fill legacy sidecars that lack the per-case context fields
            (`language`, `parse_strategy`, `context_windows`, etc.). Without
            it, missing fields degrade to `unknown` buckets.
    """
    result_idx = _result_index(result_payloads_by_file)

    summary, false_positive_rate = _session_summary(annotation_files, result_idx)
    # v2.5 — fold non-zero response-class counts into summary instead of a
    # separate top-level section. Sibling numbers live in `summary` already;
    # this keeps the class breakdown where agents already look.
    response_class_counts = _response_class_counts(annotation_files, result_idx)
    if response_class_counts:
        summary["response_class_counts"] = response_class_counts

    span_records = _collect_span_records(annotation_files, result_idx)
    span_groups_all = _span_analysis(span_records)
    # v2.5 — groups with count < 4 are statistically useless; move them to a
    # compact `long_tail_groups` section so the agent still sees what was
    # observed but isn't swamped by low-signal per-group rollups.
    span_groups, long_tail_groups = _split_long_tail(span_groups_all)

    # Compute every axis breakdown first so data_quality can decide which to
    # suppress.
    language_breakdown = _axis_breakdown(annotation_files, result_idx, "language", default="unknown")
    config_breakdown = _axis_breakdown(annotation_files, result_idx, "system_style", default="unspecified")
    user_style_breakdown = _axis_breakdown(annotation_files, result_idx, "user_style", default="unspecified")

    data_quality = _data_quality(
        annotation_files,
        result_idx,
        {
            "language_breakdown": language_breakdown,
            "config_breakdown": config_breakdown,
            "user_style_breakdown": user_style_breakdown,
        },
    )
    suppressed = set(data_quality.get("suppressed_sections") or [])

    # v2.4 — compute distribution + variants in one pass
    model_answer_distribution, model_answer_variants = _model_answer_stats(
        annotation_files, result_idx,
    )

    ordering_hints = _ordering_hints(span_groups_all)
    annotator_notes = _collect_notes(annotation_files, result_idx)

    report: Dict[str, Any] = {
        "format_version": REPORT_FORMAT_VERSION,
        "source_files": list(source_files or []),
        "summary": summary,
        "false_positive_rate": round(false_positive_rate, 4),
        # v2.3 — top-level parser-vs-annotator alignment metric. Resolves the
        # "parser_missed: 100" framing when many of those cases actually had
        # the parser extracting the right token (just unmarked as parser_ok).
        "parser_span_alignment": _parser_span_alignment(annotation_files, result_idx),
        # v2.3 — data quality diagnostics + list of suppressed sections.
        "data_quality": data_quality,
        # v2.2 — histogram of what the MODEL actually chose.
        # v2.4 — also emit raw variants per normalized bucket so the agent
        # sees case / markdown / phrasing variation inside each answer class.
        "model_answer_distribution": model_answer_distribution,
        "model_answer_variants": model_answer_variants,
        "span_groups": span_groups,
    }

    # v2.5 — `answer_when_missed.by_expected` collapses to a single tautology
    # under `uniform_expected`; skip the whole section in that case since the
    # sibling distractor/pair blocks also go empty.
    if "answer_when_missed.by_expected" not in suppressed:
        report["answer_when_missed"] = _answer_when_missed(annotation_files, result_idx)

    # v2.5 — only emit when the block carries signal. `no_parse_strategy`
    # flattens the breakdown to one `unknown` row; data_quality marks it
    # suppressed and we honour that here.
    if "strategy_breakdown" not in suppressed:
        report["strategy_breakdown"] = _strategy_breakdown(annotation_files, result_idx)

    # v2.5 — long-tail groups only shown when present.
    if long_tail_groups:
        report["long_tail_groups"] = long_tail_groups

    # v2.5 — ordering_hints / annotator_notes now omit-when-empty. Keeps the
    # JSON free of inert `[]` entries the retrospective called out.
    if ordering_hints:
        report["ordering_hints"] = ordering_hints
    if annotator_notes:
        report["annotator_notes"] = annotator_notes

    # v2.6 — new mark-type aggregations (omit-when-empty)
    neg_records = _collect_negative_records(annotation_files, result_idx)
    if neg_records:
        negative_span_groups = _negative_span_analysis(neg_records)
        if negative_span_groups:
            report["negative_span_groups"] = negative_span_groups

    manual_kw_dist = _answer_keyword_distribution(annotation_files, result_idx)
    if manual_kw_dist:
        report["manual_keyword_distribution"] = manual_kw_dist

    anchor_groups = _context_anchor_groups(annotation_files, result_idx)
    if anchor_groups:
        report["context_anchor_groups"] = anchor_groups

    # Single-bucket axis breakdowns get omitted from the output; data_quality
    # warnings explain why. Keeps the JSON signal-dense.
    if "language_breakdown" not in suppressed:
        report["language_breakdown"] = language_breakdown
    if "config_breakdown" not in suppressed:
        report["config_breakdown"] = config_breakdown
    if "user_style_breakdown" not in suppressed:
        report["user_style_breakdown"] = user_style_breakdown

    return report
