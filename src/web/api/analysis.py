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
        model_info = data.get("model_info", {})
        exec_info = data.get("execution_info", {})
        ts_meta = data.get("testset_metadata", {})
        num_results = len(data.get("results", []))

        # Extract task types from results
        task_types = list({r.get("input", {}).get("task_params", {}).get("task_type", r.get("test_id", "").split("_")[0])
                          for r in data.get("results", []) if r.get("status") == "success"})

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
            "task_types": task_types,
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

        return {
            "status": "ok",
            "model_count": len(model_stats),
            "models": model_stats,
            "summaries": summaries,
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
        charts_dir = str(Path(web_config.charts_dir))
        os.makedirs(charts_dir, exist_ok=True)

        # Generate chart PNGs first so the HTML report can embed them.
        # Visualization may fail partially (e.g. some chart types need more data)
        # — that's fine, we still generate the HTML report with whatever charts exist.
        try:
            generate_visualizations(loaded, charts_dir)
        except Exception:
            pass  # partial chart generation is OK

        generate_html_report(loaded, report_path, charts_dir=charts_dir, grouped_by_model=req.comparison)
        return {"status": "ok", "report_path": report_path, "filename": os.path.basename(report_path)}
    except Exception as exc:
        raise HTTPException(500, f"Report generation failed: {exc}")


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
