"""Human Review & annotation endpoints.

Annotations are stored as gzipped JSON sidecars next to their result files
(`{stem}_annotations.json.gz`), following the convention used by the
LLM-as-a-Judge feature. Writes are atomic (temp file + rename).

Route order: specific routes come before any `{filename}` catch-all so the
FastAPI router doesn't accidentally capture `cases` / `annotate` / `report` as
filenames — same rule as `src/web/api/analysis.py`.
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.web.api.analysis import _find_result_file, _load_result, _resolve_result_files
from src.web.human_review_aggregator import build_report
from src.web.translation import TranslationError, translate as translate_text

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Sidecar helpers --------------------------------------------------


_RESPONSE_CLASSES = {
    "hedge",
    "gibberish",
    "refusal",
    "language_error",
    "verbose_correct",
    "parser_ok",
    # `parser_false_positive` — annotator verified the parser extracted the
    # wrong token. Crucially, this verdict MAY coexist with `spans` so the
    # annotation carries both the evidence (where the real answer is) and the
    # diagnosis (parser got lucky on a distractor).
    "parser_false_positive",
}


def _annotation_path(result_file: Path) -> Path:
    """Return the annotation sidecar path for a given result file."""
    name = result_file.name
    if name.endswith(".json.gz"):
        stem = name[: -len(".json.gz")]
    elif name.endswith(".json"):
        stem = name[: -len(".json")]
    else:
        stem = result_file.stem
    return result_file.parent / f"{stem}_annotations.json.gz"


def _load_annotations(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with gzip.open(str(path), "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Unreadable annotation file %s: %s", path, exc)
        return None


def _atomic_write_annotations(path: Path, payload: Dict[str, Any]) -> None:
    """Write an annotation file atomically using a temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".annot-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.open(raw, "wt", encoding="utf-8") as gz:
                json.dump(payload, gz, ensure_ascii=False, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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
        if (ann.get("spans") or []) or ann.get("response_class"):
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
    return {
        "result_file_id": result_file_id,
        "case_id": r.get("test_id", ""),
        "task_type": task_type or "unknown",
        "language": pm.get("language") or "en",
        "user_style": pm.get("user_style"),
        "system_style": pm.get("system_style"),
        "user_prompt": inp.get("user_prompt") or "",
        "system_prompt": inp.get("system_prompt") or "",
        "raw_response": out.get("raw_response") or "",
        "parsed_answer": out.get("parsed_answer"),
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


class Annotation(BaseModel):
    spans: List[AnnotationSpan] = Field(default_factory=list)
    response_class: Optional[str] = None
    annotator_note: str = ""
    timestamp: Optional[str] = None


class AnnotateRequest(BaseModel):
    result_file_id: str
    case_id: str
    annotation: Annotation


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

    for fp in resolved_paths:
        try:
            data = _load_result(fp)
        except Exception as exc:
            raise HTTPException(500, f"Failed to load {fp.name}: {exc}")

        results = data.get("results") or []
        plugin = _infer_plugin(results)
        plugins_seen.append(plugin)

        annotation_payload = _load_annotations(_annotation_path(fp)) or {}
        annotations_by_case = annotation_payload.get("cases") or {}

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
            existing = annotations_by_case.get(case_id, {}).get("annotation")
            cases_out.append(_project_case(fp.name, r, existing))

    distinct_plugins = [p for p in set(plugins_seen) if p and p != "unknown"]
    session_plugin = distinct_plugins[0] if len(distinct_plugins) == 1 else "mixed"

    return {
        "plugin": session_plugin,
        "plugins": sorted(set(plugins_seen)),
        "mixed_plugins": len(distinct_plugins) > 1,
        "total": len(cases_out),
        "cases": cases_out,
    }


@router.post("/annotate")
async def save_annotation(req: AnnotateRequest) -> Dict[str, Any]:
    """Upsert a single case annotation into the sidecar, atomically."""
    ann = req.annotation

    # Invariant (relaxed in v2.20.0): at least one of `spans` / `response_class`
    # must be populated. Both may coexist — `parser_false_positive` in
    # particular is designed to carry both the span evidence and the diagnosis.
    has_spans = len(ann.spans) > 0
    has_class = ann.response_class is not None and ann.response_class != ""
    if not has_spans and not has_class:
        raise HTTPException(400, "Annotation must have either spans or a response_class")
    if has_class and ann.response_class not in _RESPONSE_CLASSES:
        raise HTTPException(400, f"Unknown response_class: {ann.response_class}")

    fp = _find_result_file(req.result_file_id)
    if fp is None:
        raise HTTPException(404, f"Result file not found: {req.result_file_id}")

    data = _load_result(fp)
    results_by_id = {r.get("test_id"): r for r in data.get("results") or []}
    target = results_by_id.get(req.case_id)
    if target is None:
        raise HTTPException(404, f"Case not found in {req.result_file_id}: {req.case_id}")

    annot_path = _annotation_path(fp)
    payload = _load_annotations(annot_path) or {
        "meta": {
            "result_file": fp.name,
            "plugin": _infer_plugin(data.get("results") or []),
            "annotated_by": "human",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "annotated_count": 0,
            "skipped_count": 0,
        },
        "cases": {},
    }

    # Build the case record.
    raw_response = (target.get("output") or {}).get("raw_response") or ""
    output = target.get("output") or {}
    evaluation = target.get("evaluation") or {}
    task_params = (target.get("input") or {}).get("task_params") or {}
    prompt_meta = (target.get("input") or {}).get("prompt_metadata") or {}
    model_info = data.get("model_info") or {}

    annotation_dict = ann.model_dump()
    annotation_dict["timestamp"] = annotation_dict.get("timestamp") or _now_iso()

    case_record = {
        "case_id": req.case_id,
        "response_length": len(raw_response) if isinstance(raw_response, str) else 0,
        "parser_match_type": evaluation.get("match_type")
        or ("correct" if evaluation.get("correct") else "unknown"),
        "parser_extracted": output.get("parsed_answer"),
        "expected": task_params.get("expected_answer") if "expected_answer" in task_params else evaluation.get("expected"),
        # Context fields used by the improvement-report aggregator. All are
        # optional — the aggregator falls back to reading the source result
        # file for legacy sidecars that were written before v2.20.1.
        "language": prompt_meta.get("language") or "en",
        "user_style": prompt_meta.get("user_style"),
        "system_style": prompt_meta.get("system_style"),
        "parse_strategy": output.get("parse_strategy") or "unknown",
        "parse_confidence": output.get("parse_confidence"),
        "model_name": model_info.get("model_name"),
        "context_windows": _extract_context_windows(raw_response, annotation_dict),
        "annotation": annotation_dict,
    }
    payload.setdefault("cases", {})[req.case_id] = case_record

    # Refresh meta counters + timestamp.
    counters = _recount_meta(payload["cases"])
    payload.setdefault("meta", {}).update(counters)
    payload["meta"]["updated_at"] = _now_iso()
    # In case this is the first write and `meta.result_file` is missing:
    payload["meta"].setdefault("result_file", fp.name)
    payload["meta"].setdefault("annotated_by", "human")
    payload["meta"].setdefault("created_at", payload["meta"]["updated_at"])
    payload["meta"].setdefault("plugin", _infer_plugin(data.get("results") or []))

    _atomic_write_annotations(annot_path, payload)
    return {"status": "ok", "case_id": req.case_id, "annotation_file": annot_path.name}


@router.get("/annotations/{result_file_id}")
async def get_annotations(result_file_id: str) -> Dict[str, Any]:
    """Return the full annotation sidecar for a given result file, or empty."""
    fp = _find_result_file(result_file_id)
    if fp is None:
        raise HTTPException(404, f"Result file not found: {result_file_id}")
    payload = _load_annotations(_annotation_path(fp))
    if payload is None:
        return {"meta": {}, "cases": {}}
    return payload


@router.delete("/annotations/{result_file_id}")
async def delete_annotations(result_file_id: str) -> Dict[str, Any]:
    """Remove the annotation sidecar for a result file.

    Idempotent: if no sidecar exists, returns `{deleted: false}` with 200.
    A missing *result file* itself still 404s, since the caller probably
    passed a typo.
    """
    fp = _find_result_file(result_file_id)
    if fp is None:
        raise HTTPException(404, f"Result file not found: {result_file_id}")
    ap = _annotation_path(fp)
    if not ap.exists():
        return {"status": "ok", "deleted": False, "filename": ap.name}
    try:
        ap.unlink()
    except OSError as exc:
        raise HTTPException(500, f"Failed to remove annotations: {exc}")
    return {"status": "ok", "deleted": True, "filename": ap.name}


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
        ap = _load_annotations(_annotation_path(fp))
        if ap is not None:
            annotation_payloads.append(ap)
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
