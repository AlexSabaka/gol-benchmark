"""Results & analysis endpoints (Stage 3)."""
from __future__ import annotations

import gzip
import json
import os
import tempfile
import time
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.web.config import web_config

router = APIRouter()


# ---------- Helpers -----------------------------------------------------------

def _results_dirs() -> List[Path]:
    """Return all directories that may contain result files."""
    root = Path(web_config.results_dir)
    dirs = [root]
    if root.exists():
        for child in root.iterdir():
            if child.is_dir():
                dirs.append(child)
    return dirs


def _find_result_files() -> List[Path]:
    """Find all result .json.gz files across result directories."""
    files = []
    for d in _results_dirs():
        if d.exists():
            files.extend(d.glob("results_*.json.gz"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _load_result(filepath: Path) -> dict:
    with gzip.open(str(filepath), "rt", encoding="utf-8") as f:
        return json.load(f)


def _summarize_result(filepath: Path) -> dict:
    """Quick summary without loading all individual results."""
    try:
        data = _load_result(filepath)
        stats = data.get("summary_statistics", {})
        metadata = data.get("metadata", {})
        model_info = data.get("model_info", {})
        exec_info = data.get("execution_info", {})
        ts_meta = data.get("testset_metadata", {})
        num_results = len(data.get("results", []))

        # Extract task types, languages, and prompt styles from results
        from src.stages.analyze_results import _infer_task_type_from_id
        success = [r for r in data.get("results", []) if r.get("status") == "success"]
        task_types = list({
            r.get("input", {}).get("task_params", {}).get("task_type", "") or _infer_task_type_from_id(r.get("test_id", ""))
            for r in success
        })
        languages = list({r.get("input", {}).get("prompt_metadata", {}).get("language", "en") for r in success})
        user_styles = list({r.get("input", {}).get("prompt_metadata", {}).get("user_style", "") for r in success} - {""})
        system_styles = list({r.get("input", {}).get("prompt_metadata", {}).get("system_style", "") for r in success} - {""})

        return {
            "filename": filepath.name,
            "path": str(filepath),
            "size_bytes": filepath.stat().st_size,
            "model_name": model_info.get("model_name", "unknown"),
            "provider": model_info.get("provider", "unknown"),
            "accuracy": stats.get("accuracy", 0),
            "correct": stats.get("correct_responses", 0),
            "total_tests": num_results,
            "parse_error_rate": stats.get("parse_error_rate", 0),
            "duration_seconds": exec_info.get("duration_seconds", 0),
            "total_tokens": stats.get("total_input_tokens", 0) + stats.get("total_output_tokens", 0),
            "testset_name": ts_meta.get("name", ts_meta.get("testset_name", "")),
            "run_group_id": metadata.get("run_group_id"),
            "matrix_batch_id": ts_meta.get("matrix_batch_id"),
            "matrix_cell_id": ts_meta.get("matrix_cell_id"),
            "matrix_label": ts_meta.get("matrix_label"),
            "matrix_plugin": ts_meta.get("matrix_plugin"),
            "matrix_axes": ts_meta.get("matrix_axes"),
            "task_types": task_types,
            "languages": languages,
            "user_styles": user_styles,
            "system_styles": system_styles,
            "created": time.ctime(filepath.stat().st_mtime),
        }
    except Exception as exc:
        return {"filename": filepath.name, "error": str(exc)}


# ---------- Endpoints ---------------------------------------------------------

@router.get("")
async def list_results():
    """List all result files with summary stats."""
    files = _find_result_files()
    return [_summarize_result(f) for f in files]


@router.get("/reports")
async def list_reports():
    """List all generated HTML reports."""
    reports_dir = Path(web_config.reports_dir)
    if not reports_dir.exists():
        return []
    items = []
    for f in sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = f.stat()
        items.append({
            "filename": f.name,
            "size_bytes": stat.st_size,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime)),
        })
    return items


@router.get("/report/{filename}")
async def serve_report(filename: str):
    """Serve a generated HTML report."""
    filepath = Path(web_config.reports_dir) / filename
    if not filepath.exists():
        raise HTTPException(404, f"Report not found: {filename}")
    return FileResponse(str(filepath), media_type="text/html")


@router.get("/charts/{filename}")
async def serve_chart(filename: str):
    """Serve a generated chart image."""
    filepath = Path(web_config.charts_dir) / filename
    if not filepath.exists():
        raise HTTPException(404, f"Chart not found: {filename}")
    return FileResponse(str(filepath))


# ── LLM-as-a-Judge endpoints (MUST be before /{filename} catch-all) ──────

from typing import Optional


class JudgeRequest(BaseModel):
    result_filenames: List[str] = Field(min_length=1)
    provider: str = "openai_compatible"
    model: str = ""
    api_base: str = ""
    api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    system_prompt: str = ""
    user_prompt_template: str = ""
    temperature: float = 0.1
    max_tokens: int = 500
    only_incorrect: bool = True


@router.post("/judge")
async def submit_judge(req: JudgeRequest):
    """Launch an LLM-as-a-Judge background job."""
    if not req.model:
        raise HTTPException(400, "Model name is required")

    resolved = []
    for fname in req.result_filenames:
        found = False
        for d in _results_dirs():
            fp = d / fname
            if fp.exists():
                resolved.append(str(fp))
                found = True
                break
        if not found:
            raise HTTPException(404, f"Result file not found: {fname}")

    from src.web.jobs import job_manager

    job_id = job_manager.submit_judge(
        result_paths=resolved,
        model_name=req.model,
        provider=req.provider,
        system_prompt=req.system_prompt,
        user_prompt_template=req.user_prompt_template,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        only_incorrect=req.only_incorrect,
        api_key=req.api_key,
        api_base=req.api_base,
        ollama_host=req.ollama_host,
        output_dir=web_config.results_dir,
    )
    return {"status": "ok", "job_id": job_id, "model": req.model}


@router.get("/judge-results")
async def list_judge_results():
    """List all judge result files."""
    files = []
    for d in _results_dirs():
        if d.exists():
            files.extend(d.glob("judge_*.json.gz"))
    results = []
    for f in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = _load_result(f)
            meta = data.get("metadata", {})
            summary = data.get("summary", {})
            results.append({
                "filename": f.name,
                "judge_model": meta.get("judge_model", "unknown"),
                "judge_provider": meta.get("judge_provider", "unknown"),
                "total_judged": summary.get("total_judged", 0),
                "true_incorrect": summary.get("true_incorrect", 0),
                "false_negative": summary.get("false_negative", 0),
                "parser_failure": summary.get("parser_failure", 0),
                "source_results": data.get("source_results", []),
                "created": time.ctime(f.stat().st_mtime),
                "duration_seconds": meta.get("duration_seconds", 0),
            })
        except Exception:
            continue
    return results


@router.get("/judge-results/{filename}")
async def get_judge_result(filename: str):
    """Load a full judge result file."""
    for d in _results_dirs():
        fp = d / filename
        if fp.exists():
            return _load_result(fp)
    raise HTTPException(404, f"Judge result file not found: {filename}")


# ── Catch-all result file endpoints (MUST be last) ──────────────────────

@router.delete("/{filename}")
async def delete_result(filename: str):
    """Delete a result file."""
    for d in _results_dirs():
        filepath = d / filename
        if filepath.exists():
            filepath.unlink()
            return {"status": "deleted", "filename": filename}
    raise HTTPException(404, f"Result file not found: {filename}")


@router.get("/{filename}")
async def get_result(filename: str):
    """Load a full result file."""
    for d in _results_dirs():
        filepath = d / filename
        if filepath.exists():
            data = _load_result(filepath)
            return {
                "filename": filename,
                "metadata": data.get("metadata", {}),
                "model_info": data.get("model_info", {}),
                "testset_metadata": data.get("testset_metadata", {}),
                "execution_info": data.get("execution_info", {}),
                "summary_statistics": data.get("summary_statistics", {}),
                "results_count": len(data.get("results", [])),
                "results": data.get("results", []),
            }
    raise HTTPException(404, f"Result file not found: {filename}")


class ReanalyzeResponse(BaseModel):
    status: str
    filename: str
    total_results: int
    changes: int
    new_accuracy: float
    old_accuracy: float


@router.post("/{filename}/reanalyze")
async def reanalyze_result(filename: str):
    """Re-parse and re-evaluate a result file using current plugin parsers."""
    for d in _results_dirs():
        filepath = d / filename
        if filepath.exists():
            try:
                from src.web.reanalyze import reanalyze_result_file
                stats = reanalyze_result_file(filepath)
                return ReanalyzeResponse(status="ok", **stats)
            except Exception as exc:
                raise HTTPException(500, f"Reanalysis failed: {exc}")
    raise HTTPException(404, f"Result file not found: {filename}")


# ── Analysis endpoints ───────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    result_filenames: List[str] = Field(min_length=1)
    comparison: bool = True


@router.post("/analyze")
async def analyze_results(req: AnalyzeRequest):
    """Run Stage 3 analysis on selected result files."""
    # Resolve file paths
    resolved = []
    for fname in req.result_filenames:
        found = False
        for d in _results_dirs():
            fp = d / fname
            if fp.exists():
                resolved.append(str(fp))
                found = True
                break
        if not found:
            raise HTTPException(404, f"Result file not found: {fname}")

    try:
        from src.stages.analyze_results import load_result_file, extract_summary_stats, extract_task_breakdown

        loaded = [load_result_file(p) for p in resolved]
        summaries = [extract_summary_stats(r) for r in loaded]

        # Per-model breakdown
        model_stats = {}
        for s in summaries:
            model = s.get("model_name", "unknown")
            model_stats[model] = {
                "accuracy": s.get("accuracy", 0),
                "total_tests": s.get("total_tests", 0),
                "correct": s.get("correct_responses", 0),
                "parse_error_rate": s.get("parse_error_rate", 0),
                "duration": s.get("duration_seconds", 0),
                "task_breakdown": s.get("task_breakdown", {}),
            }

        # Build dimension breakdowns (language, user_style, system_style)
        dimension_breakdowns: dict = {"language": {}, "user_style": {}, "system_style": {}}
        for data in loaded:
            for r in data.get("results", []):
                if r.get("status") != "success":
                    continue
                pm = r.get("input", {}).get("prompt_metadata", {})
                correct = r.get("evaluation", {}).get("correct", False)
                for dim in ("language", "user_style", "system_style"):
                    val = pm.get(dim, "")
                    if not val:
                        continue
                    bucket = dimension_breakdowns[dim].setdefault(val, {"total": 0, "correct": 0})
                    bucket["total"] += 1
                    if correct:
                        bucket["correct"] += 1
        # Compute accuracy per bucket
        for dim_data in dimension_breakdowns.values():
            for bucket in dim_data.values():
                bucket["accuracy"] = bucket["correct"] / bucket["total"] if bucket["total"] > 0 else 0

        return {
            "status": "ok",
            "model_count": len(model_stats),
            "models": model_stats,
            "summaries": summaries,
            "dimension_breakdowns": dimension_breakdowns,
        }
    except Exception as exc:
        raise HTTPException(500, f"Analysis failed: {exc}")


@router.post("/generate-report")
async def generate_report(req: AnalyzeRequest):
    """Generate an HTML report and return its path."""
    resolved = []
    for fname in req.result_filenames:
        for d in _results_dirs():
            fp = d / fname
            if fp.exists():
                resolved.append(str(fp))
                break

    if not resolved:
        raise HTTPException(404, "No result files found")

    try:
        from src.stages.analyze_results import (
            load_result_file, generate_html_report, generate_visualizations,
        )

        loaded = [load_result_file(p) for p in resolved]
        reports_dir = Path(web_config.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        report_path = str(reports_dir / f"report_{ts}.html")

        # Use a per-report charts directory so each report only embeds its
        # own charts — no stale PNGs from earlier runs can leak in.
        charts_dir = str(reports_dir / "charts" / ts)
        os.makedirs(charts_dir, exist_ok=True)

        # Generate chart PNGs first so the HTML report can embed them.
        # Visualization may fail partially (e.g. some chart types need more data)
        # — that's fine, we still generate the HTML report with whatever charts exist.
        viz_error = None
        try:
            generate_visualizations(loaded, charts_dir)
        except Exception as viz_exc:
            viz_error = str(viz_exc)  # non-fatal — report still generates without charts

        generate_html_report(loaded, report_path, charts_dir=charts_dir, grouped_by_model=req.comparison)

        # Charts are now embedded as base64 in the HTML — clean up the
        # per-report directory since the PNGs are no longer needed.
        try:
            import shutil
            shutil.rmtree(charts_dir, ignore_errors=True)
        except Exception:
            pass
        resp = {"status": "ok", "report_path": report_path, "filename": os.path.basename(report_path)}
        if viz_error:
            resp["viz_warning"] = viz_error
        return resp
    except Exception as exc:
        raise HTTPException(500, f"Report generation failed: {exc}")
