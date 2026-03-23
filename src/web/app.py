"""FastAPI application — serves API endpoints and HTMX templates."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.api import api_router
from src.web.partials import router as partials_router

_WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(title="GoL Benchmark", version="3.0.0")

# --- Static files & templates ------------------------------------------------
app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))

# --- API routes ---------------------------------------------------------------
app.include_router(api_router, prefix="/api")

# --- HTMX partial routes (no prefix — mixed /api/ and /partials/) -------------
app.include_router(partials_router)


# --- Page routes (serve HTMX templates) ---------------------------------------
@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/configure")
async def configure(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})


@app.get("/testsets")
async def testsets_page(request: Request):
    return templates.TemplateResponse("testsets.html", {"request": request})


@app.get("/execute")
async def execute_page(request: Request):
    return templates.TemplateResponse("execute.html", {"request": request})


@app.get("/results")
async def results_page(request: Request):
    return templates.TemplateResponse("results.html", {"request": request})
