"""Test set management & generation endpoints (Stage 1)."""
from __future__ import annotations

import gzip
import json
import os
import tempfile
import time
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from src.web.config import web_config

router = APIRouter()


# ---------- Pydantic models for request bodies --------------------------------

class PromptConfig(BaseModel):
    user_style: str = "minimal"
    system_style: str = "analytical"
    language: str = "en"


class TaskConfig(BaseModel):
    type: str
    generation: dict = Field(default_factory=dict)
    prompt_configs: List[PromptConfig] = Field(default_factory=lambda: [PromptConfig()])


class GenerateRequest(BaseModel):
    """Mirrors the multi-task YAML config structure."""
    name: str = "web_benchmark"
    description: str = ""
    tasks: List[TaskConfig]
    temperature: float = 0.1
    max_tokens: int = 2048
    no_thinking: bool = True
    cell_markers: List[str] = Field(default_factory=lambda: ["1", "0"])
    seed: int = 42


# ---------- Helpers -----------------------------------------------------------

def _testsets_dir() -> Path:
    p = Path(web_config.testsets_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _peek_testset(filepath: Path) -> dict:
    """Load metadata from a .json.gz test set without reading all test cases."""
    try:
        with gzip.open(str(filepath), "rt", encoding="utf-8") as f:
            data = json.load(f)
        cases = data.get("test_cases", [])
        return {
            "filename": filepath.name,
            "path": str(filepath),
            "size_bytes": filepath.stat().st_size,
            "metadata": data.get("metadata", {}),
            "generation_params": data.get("generation_params", {}),
            "statistics": data.get("statistics", {}),
            "test_count": len(cases),
            "task_types": list({tc.get("task_type", "unknown") for tc in cases}),
            "created": time.ctime(filepath.stat().st_mtime),
        }
    except Exception as exc:
        return {"filename": filepath.name, "error": str(exc)}


# ---------- Endpoints ---------------------------------------------------------

@router.get("")
async def list_testsets():
    """List all .json.gz test set files with metadata summaries."""
    d = _testsets_dir()
    files = sorted(d.glob("*.json.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_peek_testset(f) for f in files]


@router.get("/{filename}")
async def get_testset(filename: str):
    """Load full test set metadata + sample test cases."""
    filepath = _testsets_dir() / filename
    if not filepath.exists():
        raise HTTPException(404, f"Test set not found: {filename}")
    with gzip.open(str(filepath), "rt", encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("test_cases", [])
    return {
        "filename": filename,
        "metadata": data.get("metadata", {}),
        "generation_params": data.get("generation_params", {}),
        "sampling_params": data.get("sampling_params", {}),
        "execution_params": data.get("execution_params", {}),
        "statistics": data.get("statistics", {}),
        "test_count": len(cases),
        "task_types": list({tc.get("task_type", "unknown") for tc in cases}),
        "sample_cases": cases[:5],
    }


@router.delete("/{filename}")
async def delete_testset(filename: str):
    """Delete a test set file."""
    filepath = _testsets_dir() / filename
    if not filepath.exists():
        raise HTTPException(404, f"Test set not found: {filename}")
    filepath.unlink()
    return {"status": "deleted", "filename": filename}


@router.post("/generate")
async def generate_testset(req: GenerateRequest):
    """Generate a test set from configuration (wraps Stage 1)."""
    # Build YAML config dict
    ts = time.strftime("%Y%m%d_%H%M%S")
    config = {
        "metadata": {
            "name": f"{req.name}_{ts}",
            "version": "1.0",
            "schema_version": "1.0.0",
            "description": req.description or f"Web-generated: {req.name}",
            "task_type": "multi-task" if len(req.tasks) > 1 else req.tasks[0].type,
        },
        "sampling": {
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        },
        "execution": {
            "no_thinking": req.no_thinking,
            "cell_markers": req.cell_markers,
        },
    }

    # Single-task vs multi-task
    tasks_yaml = []
    for t in req.tasks:
        gen = dict(t.generation)
        gen.setdefault("seed", req.seed)

        # Normalize generation params: convert comma-separated strings to lists
        for key in ("target_values", "complexity", "difficulties"):
            if key in gen and isinstance(gen[key], str):
                gen[key] = [int(x.strip()) for x in gen[key].split(",") if x.strip()]

        task_entry = {
            "type": t.type,
            "generation": gen,
            "prompt_configs": [
                {"name": f"{pc.user_style}_{pc.system_style}", "user_style": pc.user_style, "system_style": pc.system_style, "language": pc.language}
                for pc in t.prompt_configs
            ],
        }
        tasks_yaml.append(task_entry)

    if len(tasks_yaml) == 1:
        config["task"] = tasks_yaml[0]
    else:
        config["tasks"] = tasks_yaml

    # Write temp YAML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, prefix="web_cfg_") as tmp:
        yaml.dump(config, tmp, default_flow_style=False)
        tmp_path = tmp.name

    try:
        from src.stages.generate_testset import generate_testset as _generate
        output_dir = str(_testsets_dir())
        result_path = _generate(tmp_path, output_dir)
        return {
            "status": "ok",
            "testset_path": result_path,
            "filename": os.path.basename(result_path),
        }
    except Exception as exc:
        raise HTTPException(500, f"Generation failed: {exc}")
    finally:
        os.unlink(tmp_path)


@router.post("/upload-yaml")
async def upload_yaml_config(file: UploadFile = File(...)):
    """Upload a YAML config file and generate a test set from it."""
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(400, "File must be a .yaml or .yml file")

    content = await file.read()
    # Validate it's parseable YAML
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise HTTPException(400, f"Invalid YAML: {exc}")

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".yaml", delete=False, prefix="upload_cfg_") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from src.stages.generate_testset import generate_testset as _generate
        output_dir = str(_testsets_dir())
        result_path = _generate(tmp_path, output_dir)
        return {"status": "ok", "testset_path": result_path, "filename": os.path.basename(result_path)}
    except Exception as exc:
        raise HTTPException(500, f"Generation failed: {exc}")
    finally:
        os.unlink(tmp_path)


@router.post("/upload-gz")
async def upload_testset_gz(file: UploadFile = File(...)):
    """Upload a pre-generated .json.gz test set file."""
    if not file.filename or not file.filename.endswith(".json.gz"):
        raise HTTPException(400, "File must be a .json.gz file")

    dest = _testsets_dir() / file.filename
    content = await file.read()

    # Validate it's a valid gzipped JSON
    try:
        json.loads(gzip.decompress(content))
    except Exception as exc:
        raise HTTPException(400, f"Invalid .json.gz file: {exc}")

    dest.write_bytes(content)
    return {"status": "ok", "filename": file.filename, "path": str(dest)}
