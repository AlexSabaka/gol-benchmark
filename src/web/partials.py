"""HTMX partial routes — small HTML fragments returned for dynamic page sections."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.web.config import web_config
from src.web.api.testsets import _testsets_dir, _peek_testset
from src.web.api.analysis import _find_result_files, _summarize_result
from src.web.jobs import job_manager

_WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))

router = APIRouter()


@router.get("/api/dashboard-summary")
async def dashboard_summary(request: Request):
    testset_count = len(list(_testsets_dir().glob("*.json.gz")))
    result_count = len(_find_result_files())
    active_jobs = sum(1 for j in job_manager.list_jobs() if j and j.get("state") in ("pending", "running"))
    return templates.TemplateResponse("partials/dashboard_summary.html", {
        "request": request,
        "testset_count": testset_count,
        "result_count": result_count,
        "active_jobs": active_jobs,
    })


@router.get("/partials/recent-testsets")
async def recent_testsets(request: Request):
    d = _testsets_dir()
    files = sorted(d.glob("*.json.gz"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    items = [_peek_testset(f) for f in files]
    return templates.TemplateResponse("partials/recent_testsets.html", {
        "request": request, "items": items,
    })


@router.get("/partials/recent-results")
async def recent_results(request: Request):
    files = _find_result_files()[:5]
    items = [_summarize_result(f) for f in files]
    return templates.TemplateResponse("partials/recent_results.html", {
        "request": request, "items": items,
    })


@router.get("/partials/active-jobs")
async def active_jobs(request: Request):
    jobs = [j for j in job_manager.list_jobs() if j and j.get("state") in ("pending", "running")]
    return templates.TemplateResponse("partials/active_jobs.html", {
        "request": request, "jobs": jobs,
    })


@router.get("/partials/testsets-table")
async def testsets_table(request: Request):
    d = _testsets_dir()
    files = sorted(d.glob("*.json.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = [_peek_testset(f) for f in files]
    return templates.TemplateResponse("partials/testsets_table.html", {
        "request": request, "items": items,
    })


@router.get("/partials/results-table")
async def results_table(request: Request):
    files = _find_result_files()
    items = [_summarize_result(f) for f in files]
    return templates.TemplateResponse("partials/results_table.html", {
        "request": request, "items": items,
    })
