"""Human Review & annotation endpoints.

Annotations are stored in the SQLite ``annotations`` table (see
``db_migrations/002_annotations.sql``). The store module
(:mod:`src.web.annotation_store`) projects rows back into the sidecar-shaped
dict the aggregator expects, so the API payloads and the improvement-report
format haven't changed.

Route order: specific routes come before any `{filename}` catch-all so the
FastAPI router doesn't accidentally capture `cases` / `annotate` / `report` as
filenames — same rule as `src/web/api/analysis.py`.
"""
from __future__ import annotations

import hashlib
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.web import annotation_store as _annotation_store_module
from src.web.api.analysis import _find_result_file, _load_result, _resolve_result_files
from src.web.human_review_aggregator import build_report
from src.web.translation import TranslationError, translate as translate_text

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Sidecar helpers --------------------------------------------------


# v4 (Phase 1): collapsed to four canonical codes. `unrecoverable` absorbs
# the old `gibberish` / `refusal` / `language_error` codes. `verbose` /
# `verbose_correct` are dropped entirely (extractable with spans is the
# default — no class needed). `parser_ok` stays dropped (auto-inferred).
_RESPONSE_CLASSES = {
    "hedge",
    "truncated",
    "unrecoverable",
    # Renamed in v3: `parser_false_positive` → `false_positive`.
    # Annotator verified the parser extracted the wrong token. Crucially,
    # this verdict MAY coexist with `spans` so the annotation carries both
    # the evidence (where the real answer is) and the diagnosis.
    "false_positive",
}

# Old codes → new codes. Applied on sidecar load + save for backwards compat.
_CLASS_RENAME: Dict[str, str] = {
    # v3 legacy renames.
    "parser_false_positive": "false_positive",
    # v4 collapse: model-failure modes all fold into "unrecoverable".
    "gibberish": "unrecoverable",
    "refusal": "unrecoverable",
    "language_error": "unrecoverable",
}

# Codes that should be silently dropped during migration. `parser_ok` is
# auto-inferred at aggregation time. `verbose` / `verbose_correct` are
# redundant with "annotation has spans" (Extractable is implicit).
_CLASS_DROP: set[str] = {"parser_ok", "verbose", "verbose_correct"}


def _migrate_annotation(ann: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate a single annotation dict from the old schema to the new one.

    - ``response_class`` (string) → ``response_classes`` (array)
    - Rename old codes (``gibberish``/``refusal``/``language_error`` →
      ``unrecoverable``, ``parser_false_positive`` → ``false_positive``)
    - Drop ``parser_ok`` / ``verbose`` / ``verbose_correct`` (redundant)
    - Fold legacy ``negative_keywords`` entries into ``negative_spans``
    - Ensure new mark-type arrays exist (empty defaults)
    """
    # response_class (string) → response_classes (array)
    rc = ann.get("response_class")
    rcs = ann.get("response_classes")
    if rcs is None:
        rcs = [rc] if rc else []
    elif isinstance(rcs, str):
        rcs = [rcs] if rcs else []
    # Remove the old scalar field so downstream code never reads it.
    ann.pop("response_class", None)

    # Rename old codes + drop dropped codes
    rcs = [_CLASS_RENAME.get(c, c) for c in rcs if c not in _CLASS_DROP]
    # Deduplicate while preserving order (multiple legacy codes may collapse
    # to the same new code — e.g. `gibberish` + `refusal` → `unrecoverable`).
    seen: set = set()
    deduped: list = []
    for c in rcs:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    ann["response_classes"] = deduped

    # Ensure new mark-type arrays exist (empty defaults for new mark types)
    for field in ("context_anchors", "answer_keywords", "negative_spans", "negative_keywords"):
        ann.setdefault(field, [])

    # v4 fold: negative_keywords → negative_spans. Kept as an empty list so
    # the DB column stays populated; the distinction is gone at the semantic
    # level (spec §5.1). Idempotent on already-migrated annotations.
    legacy_kw = ann.get("negative_keywords") or []
    if legacy_kw:
        ann["negative_spans"] = (ann.get("negative_spans") or []) + list(legacy_kw)
        ann["negative_keywords"] = []

    return ann


def _load_annotations_from_store(result_file_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the sidecar-shaped annotation payload from the DB store, applying
    schema migrations to every case's annotation dict on read."""
    payload = _annotation_store_module.get_store().load_for_file(result_file_id)
    if not payload:
        return payload
    for case in (payload.get("cases") or {}).values():
        ann = case.get("annotation")
        if isinstance(ann, dict):
            _migrate_annotation(ann)
    return payload


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _response_hash(raw_response: str) -> str:
    """16-hex-char SHA256 prefix over the first 128 chars of a response.

    Used to uniquely identify a response variant across same-``case_id`` rows
    (different languages / user styles / system styles) and to detect
    contaminated sidecar entries saved against a different response. 64 bits
    of collision resistance — safe for any realistic testset cardinality.

    TD-096 (resolved): the original implementation used 8 hex chars of MD5
    over the same prefix (32-bit space). The annotation-store migrator
    re-hashes legacy sidecars against their source result files; entries
    whose source has disappeared keep the legacy hash as an opaque
    identifier.
    """
    prefix = (raw_response or "")[:128].encode("utf-8", errors="replace")
    return hashlib.sha256(prefix).hexdigest()[:16]


def _response_hash_legacy(raw_response: str) -> str:
    """Pre-TD-096 hash. Kept solely so the annotation-store migrator can
    match legacy sidecar entries against result-file responses during
    rehash. Do NOT call from runtime paths."""
    prefix = (raw_response or "")[:128].encode("utf-8", errors="replace")
    return hashlib.md5(prefix).hexdigest()[:8]


def _infer_plugin(results: List[Dict[str, Any]]) -> str:
    """Majority task_type among successful results in a single result file."""
    from src.stages.analyze_results import _infer_task_type_from_id

    task_types: List[str] = []
    for r in results or []:
        tp = (r.get("input") or {}).get("task_params") or {}
        task_type = tp.get("task_type") or _infer_task_type_from_id(r.get("test_id", ""))
        if task_type:
            task_types.append(task_type)
    if not task_types:
        return "unknown"
    return Counter(task_types).most_common(1)[0][0]


def _recount_meta(cases: Dict[str, Any]) -> Dict[str, int]:
    annotated = 0
    skipped = 0
    for case in cases.values():
        ann = case.get("annotation") or {}
        has_spans = bool(ann.get("spans"))
        # Support both old (`response_class`) and new (`response_classes`) schema.
        has_class = bool(ann.get("response_classes")) or bool(ann.get("response_class"))
        if has_spans or has_class:
            annotated += 1
        else:
            skipped += 1
    return {"annotated_count": annotated, "skipped_count": skipped}


# ---------- Case projection --------------------------------------------------


def _project_case(
    result_file_id: str,
    r: Dict[str, Any],
    existing_annotation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Flatten a result entry into a ReviewCase payload."""
    from src.stages.analyze_results import _infer_task_type_from_id

    inp = r.get("input") or {}
    out = r.get("output") or {}
    ev = r.get("evaluation") or {}
    pm = inp.get("prompt_metadata") or {}
    tp = inp.get("task_params") or {}

    task_type = tp.get("task_type") or _infer_task_type_from_id(r.get("test_id", ""))
    raw_response = out.get("raw_response") or ""
    return {
        "result_file_id": result_file_id,
        "case_id": r.get("test_id", ""),
        "response_hash": _response_hash(raw_response),
        "task_type": task_type or "unknown",
        "language": pm.get("language") or "en",
        "user_style": pm.get("user_style"),
        "system_style": pm.get("system_style"),
        "user_prompt": inp.get("user_prompt") or "",
        "system_prompt": inp.get("system_prompt") or "",
        "raw_response": raw_response,
        "parsed_answer": out.get("parsed_answer"),
        # v2.7 (Phase 2): parser-highlight anchors from the result entry.
        # Absent on legacy files — frontend falls back to substring search.
        "parsed_char_start": out.get("parsed_char_start"),
        "parsed_char_end": out.get("parsed_char_end"),
        # Phase 3: inference-time was_truncated flag. The /review workspace
        # pre-toggles the Truncated chip when set. Absent on legacy files —
        # frontend leaves the chip inactive (existing behaviour).
        "was_truncated": out.get("was_truncated"),
        "expected": tp.get("expected_answer") if "expected_answer" in tp else ev.get("expected"),
        "parser_match_type": ev.get("match_type") or ("correct" if ev.get("correct") else "unknown"),
        "parser_correct": bool(ev.get("correct")),
        "existing_annotation": existing_annotation,
    }


def _is_empty_response(text: Any) -> bool:
    if text is None:
        return True
    if isinstance(text, str):
        return not text.strip()
    return False


_CONTEXT_WINDOW_CHARS = 120
_SENTENCE_BOUNDARIES = set(".!?\n")


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


def _extract_context_windows(raw_response: str, annotation_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """For each annotated span, capture a short window of surrounding text.

    The aggregator uses these to build anchor-frequency tables and lets the
    coding agent see the immediate context that should drive a regex anchor —
    no need to round-trip back to the source result file.
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(raw_response, str) or not raw_response:
        return out
    spans = (annotation_dict or {}).get("spans") or []
    n = len(raw_response)
    for s in spans:
        try:
            start = max(0, int(s.get("char_start", 0)))
            end = min(n, int(s.get("char_end", 0)))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        before = raw_response[max(0, start - _CONTEXT_WINDOW_CHARS):start]
        after = raw_response[end:min(n, end + _CONTEXT_WINDOW_CHARS)]
        out.append({
            "text": raw_response[start:end],
            "char_start": start,
            "char_end": end,
            "before": before,
            "after": after,
            "sentence": _extract_sentence(raw_response, start, end),
        })
    return out


# ---------- Pydantic I/O -----------------------------------------------------


class AnnotationSpan(BaseModel):
    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    position: str  # start | middle | end
    format: str    # bold | boxed | label | plain | other
    confidence: Optional[str] = None  # high | medium | low


class MarkSpan(BaseModel):
    """Lightweight char-range mark used for context anchors, answer keywords,
    negative spans, and negative keywords."""
    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class Annotation(BaseModel):
    spans: List[AnnotationSpan] = Field(default_factory=list)
    # v3: array of response classes (was scalar `response_class` pre-v3).
    response_classes: List[str] = Field(default_factory=list)
    # Legacy field — accepted for backwards compat but converted to
    # `response_classes` on save.  Frontend should send `response_classes`.
    response_class: Optional[str] = None
    annotator_note: str = ""
    timestamp: Optional[str] = None
    # v3 mark types
    context_anchors: List[MarkSpan] = Field(default_factory=list)
    answer_keywords: List[MarkSpan] = Field(default_factory=list)
    negative_spans: List[MarkSpan] = Field(default_factory=list)
    negative_keywords: List[MarkSpan] = Field(default_factory=list)


class AnnotateRequest(BaseModel):
    result_file_id: str
    case_id: str
    annotation: Annotation
    # v2.6+: response_hash uniquely identifies the exact result entry across all
    # dimensions (language × user_style × system_style). More reliable than
    # language alone.
    response_hash: Optional[str] = None
    # Kept for backwards compat / fallback.
    language: Optional[str] = None


class ReportRequest(BaseModel):
    result_file_ids: List[str] = Field(min_length=1)


class TranslateRequest(BaseModel):
    text: str
    source_lang: Optional[str] = None
    target_lang: str = "en"


# ---------- Endpoints --------------------------------------------------------


@router.get("/cases")
async def get_review_cases(
    file_ids: str = Query(..., description="Comma-separated result filenames"),
    skip_correct: bool = Query(False),
    skip_empty: bool = Query(True),
    match_types: Optional[str] = Query(
        None,
        description=(
            "Optional comma-separated list of parser match_type values to include "
            "(e.g. `parse_error,mismatch`). When omitted, all types are included."
        ),
    ),
) -> Dict[str, Any]:
    """Load a flat, ordered list of review cases for the given result files."""
    filenames = [x for x in (p.strip() for p in file_ids.split(",")) if x]
    if not filenames:
        raise HTTPException(400, "file_ids is required")

    match_filter: Optional[set[str]] = None
    if match_types:
        match_filter = {m.strip() for m in match_types.split(",") if m.strip()}
        if not match_filter:
            match_filter = None

    resolved_paths = _resolve_result_files(filenames)

    cases_out: List[Dict[str, Any]] = []
    plugins_seen: List[str] = []
    # Sum of `meta.annotated_count` across all loaded sidecars — this is the
    # authoritative total that includes cases hidden by the current filter.
    total_annotated_in_sidecars: int = 0

    for fp in resolved_paths:
        try:
            data = _load_result(fp)
        except Exception as exc:
            raise HTTPException(500, f"Failed to load {fp.name}: {exc}")

        results = data.get("results") or []
        plugin = _infer_plugin(results)
        plugins_seen.append(plugin)

        annotation_payload = _load_annotations_from_store(fp.name) or {}
        annotations_by_case = annotation_payload.get("cases") or {}
        total_annotated_in_sidecars += int(
            (annotation_payload.get("meta") or {}).get("annotated_count", 0)
        )

        for r in results:
            if r.get("status") != "success":
                continue
            raw_response = (r.get("output") or {}).get("raw_response")
            if skip_empty and _is_empty_response(raw_response):
                continue
            evaluation = r.get("evaluation") or {}
            if skip_correct and evaluation.get("correct"):
                continue
            if match_filter is not None:
                mt = evaluation.get("match_type") or (
                    "correct" if evaluation.get("correct") else "unknown"
                )
                if mt not in match_filter:
                    continue
            case_id = r.get("test_id", "")
            # v2.6+: sidecar key is case_id::response_hash — unique across all
            # dimensions (language × user_style × system_style × run index).
            # Fall back through progressively less-specific legacy key formats.
            resp_hash = _response_hash(raw_response or "")
            sidecar_key = f"{case_id}::{resp_hash}"
            pm = (r.get("input") or {}).get("prompt_metadata") or {}
            lang = pm.get("language") or "en"
            case_record = (
                annotations_by_case.get(sidecar_key)
                or annotations_by_case.get(f"{case_id}::{lang}")
                or annotations_by_case.get(case_id, {})
            )
            existing = case_record.get("annotation")
            # v2.6: drop contaminated annotations whose response_hash doesn't
            # match the current case's response — these were written by a
            # pre-fix version of the code against a different response.
            if existing and case_record.get("response_hash"):
                actual_hash = _response_hash(raw_response or "")
                if case_record["response_hash"] != actual_hash:
                    logger.info(
                        "Dropping contaminated annotation for %s in %s "
                        "(hash %s != %s)",
                        case_id, fp.name,
                        case_record["response_hash"], actual_hash,
                    )
                    existing = None
            cases_out.append(_project_case(fp.name, r, existing))

    distinct_plugins = [p for p in set(plugins_seen) if p and p != "unknown"]
    session_plugin = distinct_plugins[0] if len(distinct_plugins) == 1 else "mixed"

    return {
        "plugin": session_plugin,
        "plugins": sorted(set(plugins_seen)),
        "mixed_plugins": len(distinct_plugins) > 1,
        "total": len(cases_out),
        "total_annotated_in_sidecars": total_annotated_in_sidecars,
        "cases": cases_out,
    }


@router.post("/annotate")
async def save_annotation(req: AnnotateRequest) -> Dict[str, Any]:
    """Upsert a single case annotation into the sidecar, atomically."""
    ann = req.annotation

    # Migrate legacy scalar `response_class` → `response_classes` array.
    if ann.response_class and not ann.response_classes:
        ann.response_classes = [ann.response_class]
    ann.response_class = None  # clear legacy field
    # Apply renames + drop parser_ok for incoming saves too.
    ann.response_classes = [
        _CLASS_RENAME.get(c, c) for c in ann.response_classes if c not in _CLASS_DROP
    ]

    # Invariant (relaxed in v2.20.0, extended v3): at least one of
    # `spans` / `response_classes` must be populated. Both may coexist —
    # `false_positive` in particular carries both span evidence and diagnosis.
    has_spans = len(ann.spans) > 0
    has_class = len(ann.response_classes) > 0
    if not has_spans and not has_class:
        raise HTTPException(400, "Annotation must have either spans or response_classes")
    for cls in ann.response_classes:
        if cls not in _RESPONSE_CLASSES:
            raise HTTPException(400, f"Unknown response_class: {cls}")

    fp = _find_result_file(req.result_file_id)
    if fp is None:
        raise HTTPException(404, f"Result file not found: {req.result_file_id}")

    data = _load_result(fp)
    # Find the exact result entry. When a file has multiple variants of the
    # same test_id (different languages, user/system styles), match on the
    # response_hash first (most specific), then fall back to language,
    # then accept the first match.
    target = None
    for r in data.get("results") or []:
        if r.get("test_id") != req.case_id:
            continue
        if req.response_hash:
            resp = (r.get("output") or {}).get("raw_response") or ""
            if _response_hash(resp) == req.response_hash:
                target = r
                break
        elif req.language:
            pm = (r.get("input") or {}).get("prompt_metadata") or {}
            if pm.get("language") == req.language:
                target = r
                break
        else:
            target = r
            break
    if target is None:
        raise HTTPException(404, f"Case not found in {req.result_file_id}: {req.case_id}")

    store = _annotation_store_module.get_store()
    existing_payload = store.load_for_file(fp.name)
    now = _now_iso()

    # Build the case record.
    raw_response = (target.get("output") or {}).get("raw_response") or ""
    output = target.get("output") or {}
    evaluation = target.get("evaluation") or {}
    task_params = (target.get("input") or {}).get("task_params") or {}
    prompt_meta = (target.get("input") or {}).get("prompt_metadata") or {}
    model_info = data.get("model_info") or {}

    annotation_dict = ann.model_dump(exclude_none=True)
    # Ensure the legacy `response_class` scalar is never written — only the
    # `response_classes` array is persisted.
    annotation_dict.pop("response_class", None)
    annotation_dict["timestamp"] = annotation_dict.get("timestamp") or now

    response_hash = _response_hash(raw_response)
    case_record = {
        "case_id": req.case_id,
        "response_length": len(raw_response) if isinstance(raw_response, str) else 0,
        "response_hash": response_hash,
        "parser_match_type": evaluation.get("match_type")
        or ("correct" if evaluation.get("correct") else "unknown"),
        "parser_extracted": output.get("parsed_answer"),
        "expected": task_params.get("expected_answer") if "expected_answer" in task_params else evaluation.get("expected"),
        "language": prompt_meta.get("language") or "en",
        "user_style": prompt_meta.get("user_style"),
        "system_style": prompt_meta.get("system_style"),
        "parse_strategy": output.get("parse_strategy") or "unknown",
        "parse_confidence": output.get("parse_confidence"),
        "model_name": model_info.get("model_name"),
        "context_windows": _extract_context_windows(raw_response, annotation_dict),
        "annotation": annotation_dict,
    }

    # File-level meta propagates onto every row of the file. Preserve the
    # original created_at when a sidecar predates this annotation.
    existing_meta = (existing_payload or {}).get("meta") or {}
    case_record["_meta"] = {
        "plugin": existing_meta.get("plugin") or _infer_plugin(data.get("results") or []),
        "annotated_by": existing_meta.get("annotated_by") or "human",
        "file_created_at": existing_meta.get("created_at") or now,
        "file_updated_at": now,
    }

    store.save_case(fp.name, req.case_id, response_hash, case_record)
    return {"status": "ok", "case_id": req.case_id, "result_file_id": fp.name}


@router.get("/annotations/{result_file_id}")
async def get_annotations(result_file_id: str) -> Dict[str, Any]:
    """Return the full annotation record for a given result file, or empty."""
    fp = _find_result_file(result_file_id)
    if fp is None:
        raise HTTPException(404, f"Result file not found: {result_file_id}")
    payload = _load_annotations_from_store(fp.name)
    if payload is None:
        return {"meta": {}, "cases": {}}
    return payload


@router.delete("/annotations/{result_file_id}")
async def delete_annotations(result_file_id: str) -> Dict[str, Any]:
    """Remove every annotation for a result file.

    Idempotent: if nothing is stored, returns `{deleted: false}` with 200.
    A missing *result file* itself still 404s since the caller probably
    passed a typo.
    """
    fp = _find_result_file(result_file_id)
    if fp is None:
        raise HTTPException(404, f"Result file not found: {result_file_id}")
    removed = _annotation_store_module.get_store().delete_file(fp.name)
    return {"status": "ok", "deleted": removed > 0, "removed_count": removed}


@router.delete("/annotations/{result_file_id}/{case_id}/{response_hash}")
async def delete_annotation_case(
    result_file_id: str, case_id: str, response_hash: str
) -> Dict[str, Any]:
    """Remove a single annotated case (resolves TD-095).

    Idempotent: returns `{deleted: false}` when the row doesn't exist.
    """
    fp = _find_result_file(result_file_id)
    if fp is None:
        raise HTTPException(404, f"Result file not found: {result_file_id}")
    removed = _annotation_store_module.get_store().delete_case(
        fp.name, case_id, response_hash
    )
    return {
        "status": "ok",
        "deleted": removed,
        "case_id": case_id,
        "response_hash": response_hash,
    }


@router.post("/translate")
async def translate_endpoint(req: TranslateRequest) -> Dict[str, Any]:
    """Translate arbitrary text via the configured provider (see translation.py)."""
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "`text` must be non-empty")
    try:
        result = translate_text(
            req.text,
            source_lang=req.source_lang,
            target_lang=req.target_lang or "en",
        )
    except TranslationError as exc:
        raise HTTPException(503, str(exc))
    return {
        "translated": result.translated,
        "provider": result.provider,
        "source_lang": result.source_lang,
        "target_lang": result.target_lang,
    }


@router.post("/report")
async def improvement_report(req: ReportRequest) -> Dict[str, Any]:
    """Aggregate annotations into an improvement report (PRD §6).

    Loads both the annotation sidecars *and* the source result payloads so the
    aggregator can back-fill per-case context (`language`, `parse_strategy`,
    `context_windows`, ...) for legacy sidecars written before v2.20.1.
    Without this, fields that didn't exist in older sidecars would degrade to
    `unknown` buckets even when the source result file has the data.
    """
    resolved = _resolve_result_files(req.result_file_ids)
    annotation_payloads: List[Dict[str, Any]] = []
    result_payloads_by_file: Dict[str, Any] = {}
    for fp in resolved:
        payload = _load_annotations_from_store(fp.name)
        if payload is not None:
            annotation_payloads.append(payload)
            try:
                result_payloads_by_file[fp.name] = _load_result(fp)
            except Exception as exc:
                logger.warning("Could not load source result for backfill %s: %s", fp.name, exc)

    if not annotation_payloads:
        raise HTTPException(404, "No annotation files found for the selected result files")

    return build_report(
        annotation_payloads,
        source_files=req.result_file_ids,
        result_payloads_by_file=result_payloads_by_file,
    )
