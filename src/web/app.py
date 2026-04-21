"""FastAPI application — serves API endpoints and React SPA."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.web.api import api_router
from src.web.config import web_config
from src.web.job_store import JobStore
from src.web.jobs import job_manager

_WEB_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _WEB_DIR.resolve().parent.parent
_SPA_DIR = _PROJECT_ROOT / "frontend" / "dist"

_logger = logging.getLogger(__name__)

# Job persistence — per-job files under web_config.jobs_dir.
# `GOL_JOBS_FILE` is retained as a deprecated alias: if set, its parent directory
# is used as the jobs dir (per-job files live alongside the old monolithic file).
_legacy_jobs_file = os.environ.get("GOL_JOBS_FILE")
if _legacy_jobs_file:
    _logger.warning(
        "GOL_JOBS_FILE is deprecated; use GOL_DATA_ROOT or move the parent "
        "directory. Falling back to %s's parent as jobs_dir.",
        _legacy_jobs_file,
    )
    _jobs_dir = Path(_legacy_jobs_file).parent
else:
    _jobs_dir = Path(web_config.jobs_dir)
_job_store = JobStore(_jobs_dir)

# Wire store into the singleton manager so it can persist/load jobs.
job_manager._store = _job_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load historical jobs on startup; save all jobs on shutdown."""
    job_manager.load_from_store()
    yield
    job_manager.save_to_store()


app = FastAPI(title="GoL Benchmark", version=__version__, lifespan=lifespan)

# --- API routes ---------------------------------------------------------------
app.include_router(api_router, prefix="/api")

# --- React SPA (client-side routing fallback) ---------------------------------
if _SPA_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_SPA_DIR / "assets")), name="spa-assets")

    @app.get("/{full_path:path}")
    async def spa_catchall(full_path: str):
        """Serve React SPA — fall back to index.html for client-side routing."""
        file = _SPA_DIR / full_path
        if full_path and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_SPA_DIR / "index.html"))
