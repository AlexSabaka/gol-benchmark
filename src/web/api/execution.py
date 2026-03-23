"""Job execution endpoints (Stage 2)."""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.web.config import web_config
from src.web.jobs import job_manager

router = APIRouter()


class RunRequest(BaseModel):
    testset_path: Optional[str] = None
    testset_filename: Optional[str] = None
    models: List[str] = Field(min_length=1)
    provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 2048
    no_think: bool = True
    output_dir: Optional[str] = None
    api_key: str = ""
    api_base: str = ""


@router.post("/run")
async def submit_run(req: RunRequest):
    """Launch benchmark execution as background jobs — one per model."""
    # Resolve testset path from either full path or filename
    if req.testset_path:
        ts_path = req.testset_path
    elif req.testset_filename:
        ts_path = str(Path(web_config.testsets_dir) / req.testset_filename)
    else:
        raise HTTPException(400, "Provide either testset_path or testset_filename")

    if not Path(ts_path).exists():
        raise HTTPException(404, f"Test set not found: {ts_path}")

    output_dir = req.output_dir or web_config.results_dir
    job_ids = []
    for model_name in req.models:
        jid = job_manager.submit(
            testset_path=ts_path,
            model_name=model_name,
            provider=req.provider,
            ollama_host=req.ollama_host,
            output_dir=output_dir,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            no_think=req.no_think,
            api_key=req.api_key,
            api_base=req.api_base,
        )
        job_ids.append({"job_id": jid, "model": model_name})
    return {"jobs": job_ids}


@router.get("")
async def list_jobs():
    """List all recent jobs."""
    return job_manager.list_jobs()


@router.get("/{job_id}/status")
async def job_status(job_id: str):
    """Get current status of a job."""
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(404, f"Job not found: {job_id}")
    return status


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending/running job."""
    if job_manager.cancel(job_id):
        return {"status": "cancelled", "job_id": job_id}
    raise HTTPException(400, f"Cannot cancel job {job_id} (may already be finished)")
