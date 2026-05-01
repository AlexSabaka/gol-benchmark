"""FastAPI application — serves API endpoints and React SPA."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.web import annotation_store as annotation_store_module
from src.web import prompt_store as prompt_store_module
from src.web.annotation_store import AnnotationStore
from src.web.annotation_store_migrator import migrate_sidecar_files_to_db
from src.web.api import api_router
from src.web.config import web_config
from src.web.db import connect
from src.web.job_store import JobStore
from src.web.job_store_migrator import migrate_json_jobs_to_db
from src.web.jobs import job_manager
from src.web.prompt_store import PromptStore

_WEB_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _WEB_DIR.resolve().parent.parent
_SPA_DIR = _PROJECT_ROOT / "frontend" / "dist"

_logger = logging.getLogger(__name__)

# DB lifecycle lives entirely inside ``lifespan``. Nothing at module-import
# time touches the filesystem so test harnesses that ``from src.web.app
# import app`` don't accidentally migrate real ``data/`` contents.
_db_conn = None
_job_store: JobStore | None = None
_annotation_store: AnnotationStore | None = None
_prompt_store: PromptStore | None = None


def _startup() -> None:
    """Open the DB connection, run migrations, and ingest any legacy files."""
    global _db_conn, _job_store, _annotation_store, _prompt_store

    _db_conn = connect(web_config.db_path)
    _job_store = JobStore(_db_conn)
    _annotation_store = AnnotationStore(_db_conn)
    _prompt_store = PromptStore(_db_conn)

    # Wire singletons.
    job_manager._store = _job_store
    annotation_store_module.set_store(_annotation_store)
    prompt_store_module.set_store(_prompt_store)

    # Built-in system prompts are seeded idempotently — first boot inserts the
    # four canonical entries; subsequent boots are no-ops.
    try:
        seeded = _prompt_store.seed_builtins()
        if seeded:
            _logger.info("Seeded %d built-in system prompts", seeded)
    except Exception as exc:
        _logger.warning("Built-in prompt seeding failed: %s", exc)

    # ── Legacy-file migrators (one-shot, idempotent) ─────────────────────────

    # GOL_JOBS_FILE is retained as a deprecated alias — if set, its parent
    # directory is scanned for legacy per-job JSONs.
    legacy_jobs_file = os.environ.get("GOL_JOBS_FILE")
    if legacy_jobs_file:
        _logger.warning(
            "GOL_JOBS_FILE is deprecated; jobs now live in %s. Legacy JSONs "
            "under %s's parent will be migrated once then moved aside.",
            web_config.db_path,
            legacy_jobs_file,
        )
        legacy_jobs_dir = Path(legacy_jobs_file).parent
    else:
        legacy_jobs_dir = Path(web_config.jobs_dir)

    try:
        migrated_jobs = migrate_json_jobs_to_db(
            _job_store, legacy_jobs_dir, web_config.jobs_backup_dir
        )
        if migrated_jobs:
            _logger.info("Migrated %d legacy job records into SQLite", migrated_jobs)
    except Exception as exc:
        _logger.warning("Legacy job migration failed: %s", exc)

    try:
        from src.web.api.analysis import _find_result_file as _resolve_result

        migrated_annots = migrate_sidecar_files_to_db(
            _annotation_store,
            web_config.annotations_dir,
            str(Path(web_config.annotations_dir).parent / "annotations.bak"),
            results_lookup=_resolve_result,
        )
        if migrated_annots:
            _logger.info(
                "Migrated %d legacy annotation sidecar(s) into SQLite",
                migrated_annots,
            )
    except Exception as exc:
        _logger.warning("Legacy annotation migration failed: %s", exc)


def _shutdown() -> None:
    """Persist job state, drop singletons, close the connection."""
    job_manager.save_to_store()
    annotation_store_module.set_store(None)
    prompt_store_module.set_store(None)
    job_manager._store = None
    global _db_conn, _job_store, _annotation_store, _prompt_store
    if _db_conn is not None:
        try:
            _db_conn.close()
        except Exception:
            pass
    _db_conn = None
    _job_store = None
    _annotation_store = None
    _prompt_store = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open DB + migrate on startup; persist + close on shutdown."""
    _startup()
    job_manager.load_from_store()
    yield
    _shutdown()


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
