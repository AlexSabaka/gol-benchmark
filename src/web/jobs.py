"""Background job manager for benchmark execution (Stage 2).

Uses concurrent.futures.ProcessPoolExecutor for CPU/GPU-bound model inference.
Jobs are stored in-memory only (no persistence across server restarts).
"""
from __future__ import annotations

import multiprocessing
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    model_name: str
    testset_path: str
    state: JobState = JobState.PENDING
    progress_current: int = 0
    progress_total: int = 0
    result_path: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        elapsed = None
        if self.started_at:
            end = self.finished_at or time.time()
            elapsed = round(end - self.started_at, 1)
        return {
            "id": self.id,
            "model_name": self.model_name,
            "testset_path": self.testset_path,
            "state": self.state.value,
            "progress_current": self.progress_current,
            "progress_total": self.progress_total,
            "result_path": self.result_path,
            "error": self.error,
            "created_at": self.created_at,
            "elapsed_seconds": elapsed,
        }


def _run_testset_worker(
    testset_path: str,
    model_name: str,
    provider: str,
    ollama_host: str,
    output_dir: str,
    temperature: float,
    max_tokens: int,
    no_think: bool,
    progress_dict: dict,
    job_id: str,
    api_key: str = "",
    api_base: str = "",
) -> str:
    """Worker function executed in a subprocess. Returns result file path."""
    import json, gzip, time as _time, os, traceback
    from pathlib import Path

    # Load test set
    with gzip.open(testset_path, "rt", encoding="utf-8") as f:
        testset = json.load(f)

    test_cases = testset.get("test_cases", [])
    total = len(test_cases)
    progress_dict[job_id] = {"current": 0, "total": total, "state": "running"}

    # Build model interface
    if provider == "ollama":
        from src.stages.run_testset import OllamaInterface
        model = OllamaInterface(model_name, base_url=ollama_host)
    elif provider == "openai_compatible":
        from src.stages.run_testset import OpenAICompatibleInterface
        base = api_base or ollama_host  # fall back to ollama host
        model = OpenAICompatibleInterface(model_name, base_url=base, api_key=api_key)
    elif provider == "huggingface":
        if api_key:
            os.environ["HF_TOKEN"] = api_key
        from src.stages.run_testset import HuggingFaceInterface
        model = HuggingFaceInterface(model_name)
    else:
        from src.stages.run_testset import HuggingFaceInterface
        model = HuggingFaceInterface(model_name)

    from src.stages.run_testset import parse_answer_via_plugin, evaluate_via_plugin

    results_list = []
    correct = 0
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = _time.time()

    for i, tc in enumerate(test_cases):
        try:
            prompts = tc.get("prompts", {})
            params = {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_prompt": prompts.get("system", ""),
            }
            if no_think:
                params["no_think"] = True

            resp = model.query(prompts.get("full", prompts.get("user", "")), params)

            raw_response = resp.get("response", resp.get("error", ""))
            task_type = tc.get("task_type", "")
            task_params = tc.get("task_params", {})

            parsed = parse_answer_via_plugin(raw_response, task_type, task_params)
            expected = task_params.get("expected_answer", task_params.get("correct_answer"))
            evaluation = evaluate_via_plugin(parsed, expected, task_type, task_params)

            is_correct = evaluation.get("correct", False) if evaluation else False
            if is_correct:
                correct += 1

            input_tok = resp.get("tokens_input", 0)
            output_tok = resp.get("tokens_generated", 0)
            total_input_tokens += input_tok
            total_output_tokens += output_tok

            results_list.append({
                "test_id": tc.get("test_id", f"test_{i}"),
                "status": "success",
                "input": {"user_prompt": prompts.get("user", ""), "system_prompt": prompts.get("system", ""), "task_params": task_params},
                "output": {"raw_response": raw_response, "parsed_answer": str(parsed) if parsed is not None else None},
                "evaluation": evaluation or {"correct": False, "match_type": "parse_error"},
                "tokens": {"input_tokens": input_tok, "output_tokens": output_tok},
                "duration": resp.get("duration", 0),
            })
        except Exception as exc:
            results_list.append({
                "test_id": tc.get("test_id", f"test_{i}"),
                "status": "error",
                "error": str(exc),
            })

        progress_dict[job_id] = {"current": i + 1, "total": total, "state": "running"}

    duration = _time.time() - start_time

    # Build result structure
    result_data = {
        "format_version": "1.0.0",
        "metadata": {
            "result_id": job_id,
            "timestamp": _time.strftime("%Y%m%d_%H%M%S"),
        },
        "model_info": {"model_name": model_name, "provider": provider},
        "testset_metadata": testset.get("metadata", {}),
        "execution_info": {
            "successful_tests": sum(1 for r in results_list if r["status"] == "success"),
            "failed_tests": sum(1 for r in results_list if r["status"] == "error"),
            "duration_seconds": round(duration, 2),
        },
        "summary_statistics": {
            "accuracy": round(correct / max(total, 1), 4),
            "correct_responses": correct,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        "results": results_list,
    }

    # Save
    os.makedirs(output_dir, exist_ok=True)
    safe_model = model_name.replace("/", "_").replace(":", "_")
    ts = _time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_dir, f"results_{safe_model}_{ts}.json.gz")
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, default=str)

    progress_dict[job_id] = {"current": total, "total": total, "state": "completed", "result_path": out_path}
    return out_path


class JobManager:
    """In-memory job manager backed by ProcessPoolExecutor."""

    def __init__(self, max_workers: int = 2):
        self._manager = multiprocessing.Manager()
        self._progress: dict = self._manager.dict()
        self._jobs: Dict[str, Job] = {}
        self._futures: Dict[str, Future] = {}
        self._pool = ProcessPoolExecutor(max_workers=max_workers)

    def submit(
        self,
        testset_path: str,
        model_name: str,
        provider: str = "ollama",
        ollama_host: str = "http://localhost:11434",
        output_dir: str = "results",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        no_think: bool = True,
        api_key: str = "",
        api_base: str = "",
    ) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, model_name=model_name, testset_path=testset_path)
        self._jobs[job_id] = job
        self._progress[job_id] = {"current": 0, "total": 0, "state": "pending"}

        future = self._pool.submit(
            _run_testset_worker,
            testset_path, model_name, provider, ollama_host,
            output_dir, temperature, max_tokens, no_think,
            self._progress, job_id,
            api_key, api_base,
        )
        self._futures[job_id] = future
        future.add_done_callback(lambda f, jid=job_id: self._on_done(jid, f))
        return job_id

    def _on_done(self, job_id: str, future: Future):
        job = self._jobs.get(job_id)
        if not job:
            return
        job.finished_at = time.time()
        try:
            result_path = future.result()
            job.state = JobState.COMPLETED
            job.result_path = result_path
        except Exception as exc:
            job.state = JobState.FAILED
            job.error = str(exc)

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        # Sync progress from shared dict
        prog = self._progress.get(job_id, {})
        job.progress_current = prog.get("current", job.progress_current)
        job.progress_total = prog.get("total", job.progress_total)
        if prog.get("state") == "running" and job.state == JobState.PENDING:
            job.state = JobState.RUNNING
            job.started_at = job.started_at or time.time()
        if prog.get("result_path") and job.state != JobState.COMPLETED:
            job.state = JobState.COMPLETED
            job.result_path = prog["result_path"]
            job.finished_at = job.finished_at or time.time()
        return job.to_dict()

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [self.get_status(jid) for jid in sorted(self._jobs, key=lambda k: self._jobs[k].created_at, reverse=True)]

    def cancel(self, job_id: str) -> bool:
        future = self._futures.get(job_id)
        if future and future.cancel():
            job = self._jobs.get(job_id)
            if job:
                job.state = JobState.CANCELLED
                job.finished_at = time.time()
            return True
        return False

    def shutdown(self):
        self._pool.shutdown(wait=False)


# Module-level singleton
job_manager = JobManager(max_workers=2)
