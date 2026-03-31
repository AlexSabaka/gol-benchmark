"""FastAPI application — serves API endpoints and React SPA."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.web.api import api_router

_WEB_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _WEB_DIR.resolve().parent.parent
_SPA_DIR = _PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(title="GoL Benchmark", version="3.0.0")

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
