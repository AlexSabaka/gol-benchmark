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


TERMINAL_JOB_STATES = {
    JobState.COMPLETED,
    JobState.FAILED,
    JobState.CANCELLED,
}


@dataclass
class Job:
    id: str
    model_name: str
    testset_path: str
    run_group_id: Optional[str] = None
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
            "run_group_id": self.run_group_id,
            "state": self.state.value,
            "progress_current": self.progress_current,
            "progress_total": self.progress_total,
            "result_path": self.result_path,
            "error": self.error,
            "created_at": self.created_at,
            "elapsed_seconds": elapsed,
        }


def _read_progress(progress_dict: dict, job_id: str) -> Dict[str, Any]:
    return dict(progress_dict.get(job_id, {}))


def _write_progress(progress_dict: dict, job_id: str, **updates: Any) -> None:
    current = _read_progress(progress_dict, job_id)
    cancel_requested = bool(current.get("cancel_requested")) or bool(updates.get("cancel_requested"))
    merged = {**current, **updates, "cancel_requested": cancel_requested}
    if cancel_requested and merged.get("state") in (None, "pending", "running"):
        merged["state"] = "cancelled"
    progress_dict[job_id] = merged


def _cancel_requested(progress_dict: dict, job_id: str) -> bool:
    current = _read_progress(progress_dict, job_id)
    return bool(current.get("cancel_requested")) or current.get("state") == "cancelled"


def _run_testset_worker(
    testset_path: str,
    model_name: str,
    run_group_id: Optional[str],
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
) -> Dict[str, Optional[str]]:
    """Worker function executed in a subprocess.

    Returns a status payload so the parent can distinguish normal completion
    from cooperative cancellation.
    """
    import json, gzip, time as _time, os

    # Load test set
    with gzip.open(testset_path, "rt", encoding="utf-8") as f:
        testset = json.load(f)

    test_cases = testset.get("test_cases", [])
    total = len(test_cases)
    _write_progress(progress_dict, job_id, current=0, total=total, state="running")

    # Build model interface — canonical implementations in src.models
    from src.models import OllamaInterface, HuggingFaceInterface, OpenAICompatibleInterface
    if provider == "ollama":
        model = OllamaInterface(model_name, base_url=ollama_host)
    elif provider == "openai_compatible":
        base = api_base or ollama_host  # fall back to ollama host
        model = OpenAICompatibleInterface(model_name, base_url=base, api_key=api_key)
    elif provider == "huggingface":
        if api_key:
            os.environ["HF_TOKEN"] = api_key
        model = HuggingFaceInterface(model_name)
    else:
        model = HuggingFaceInterface(model_name)

    from src.stages.run_testset import parse_answer_via_plugin, evaluate_via_plugin

    results_list = []
    correct = 0
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = _time.time()

    for i, tc in enumerate(test_cases):
        if _cancel_requested(progress_dict, job_id):
            _write_progress(progress_dict, job_id, current=i, total=total, state="cancelled")
            return {"status": "cancelled", "result_path": None}

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

            if _cancel_requested(progress_dict, job_id):
                _write_progress(progress_dict, job_id, current=i, total=total, state="cancelled")
                return {"status": "cancelled", "result_path": None}

            raw_response = resp.get("response", resp.get("error", ""))
            task_type = tc.get("task_type", "")
            task_params = tc.get("task_params", {})

            # Merge prompt_metadata into task_params so parser gets language
            prompt_meta = tc.get("prompt_metadata", {})
            enriched_params = dict(task_params)
            for key in ("language", "user_style", "system_style"):
                if key in prompt_meta and key not in enriched_params:
                    enriched_params[key] = prompt_meta[key]

            parsed = parse_answer_via_plugin(raw_response, task_type, enriched_params)
            expected = task_params.get("expected_answer", task_params.get("correct_answer"))
            evaluation = evaluate_via_plugin(parsed, expected, task_type, enriched_params)

            is_correct = evaluation.get("correct", False) if evaluation else False
            if is_correct:
                correct += 1

            input_tok = resp.get("tokens_input", 0)
            output_tok = resp.get("tokens_generated", 0)
            total_input_tokens += input_tok
            total_output_tokens += output_tok

            results_list.append({
                "test_id": tc.get("test_id", f"test_{i}"),
                "config_name": tc.get("config_name", ""),
                "status": "success",
                "input": {
                    "user_prompt": prompts.get("user", ""),
                    "system_prompt": prompts.get("system", ""),
                    "task_params": task_params,
                    "prompt_metadata": tc.get("prompt_metadata", {}),
                },
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

        _write_progress(progress_dict, job_id, current=i + 1, total=total, state="running")

    if _cancel_requested(progress_dict, job_id):
        _write_progress(progress_dict, job_id, current=total, total=total, state="cancelled")
        return {"status": "cancelled", "result_path": None}

    duration = _time.time() - start_time

    # Build result structure
    result_data = {
        "format_version": "1.0.0",
        "metadata": {
            "result_id": job_id,
            "timestamp": _time.strftime("%Y%m%d_%H%M%S"),
            "run_group_id": run_group_id,
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

    if _cancel_requested(progress_dict, job_id):
        _write_progress(progress_dict, job_id, current=total, total=total, state="cancelled")
        return {"status": "cancelled", "result_path": None}

    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, default=str)

    _write_progress(progress_dict, job_id, current=total, total=total, state="completed", result_path=out_path)
    return {"status": "completed", "result_path": out_path}


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
        run_group_id: Optional[str] = None,
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
        job = Job(id=job_id, model_name=model_name, testset_path=testset_path, run_group_id=run_group_id)
        self._jobs[job_id] = job
        _write_progress(self._progress, job_id, current=0, total=0, state="pending", cancel_requested=False)

        future = self._pool.submit(
            _run_testset_worker,
            testset_path, model_name, run_group_id, provider, ollama_host,
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
        try:
            worker_result = future.result()
        except Exception as exc:
            if job.state == JobState.CANCELLED:
                job.finished_at = job.finished_at or time.time()
                return
            job.state = JobState.FAILED
            job.error = str(exc)
            job.finished_at = time.time()
            return

        status = worker_result.get("status") if isinstance(worker_result, dict) else "completed"
        result_path = worker_result.get("result_path") if isinstance(worker_result, dict) else worker_result

        if status == "cancelled" or job.state == JobState.CANCELLED:
            job.state = JobState.CANCELLED
            job.finished_at = job.finished_at or time.time()
            return

        job.state = JobState.COMPLETED
        job.result_path = result_path
        job.finished_at = time.time()

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        # Sync progress from shared dict
        prog = self._progress.get(job_id, {})
        job.progress_current = prog.get("current", job.progress_current)
        job.progress_total = prog.get("total", job.progress_total)
        progress_state = prog.get("state")
        if progress_state == "cancelled":
            job.state = JobState.CANCELLED
            job.finished_at = job.finished_at or time.time()
        elif progress_state == "running" and job.state == JobState.PENDING:
            job.state = JobState.RUNNING
            job.started_at = job.started_at or time.time()
        if prog.get("result_path") and job.state not in TERMINAL_JOB_STATES:
            job.state = JobState.COMPLETED
            job.result_path = prog["result_path"]
            job.finished_at = job.finished_at or time.time()
        return job.to_dict()

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [self.get_status(jid) for jid in sorted(self._jobs, key=lambda k: self._jobs[k].created_at, reverse=True)]

    def submit_judge(
        self,
        result_paths: List[str],
        model_name: str,
        provider: str = "openai_compatible",
        system_prompt: str = "",
        user_prompt_template: str = "",
        temperature: float = 0.1,
        max_tokens: int = 500,
        only_incorrect: bool = True,
        api_key: str = "",
        api_base: str = "",
        ollama_host: str = "http://localhost:11434",
        output_dir: str = "results",
    ) -> str:
        from src.web.judge import run_judge_worker, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_TEMPLATE

        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            model_name=f"judge:{model_name}",
            testset_path=",".join(result_paths),
        )
        self._jobs[job_id] = job
        _write_progress(self._progress, job_id, current=0, total=0, state="pending", cancel_requested=False)

        future = self._pool.submit(
            run_judge_worker,
            result_paths, model_name, provider,
            system_prompt or DEFAULT_SYSTEM_PROMPT,
            user_prompt_template or DEFAULT_USER_TEMPLATE,
            temperature, max_tokens, only_incorrect,
            api_key, api_base, ollama_host, output_dir,
            job_id, self._progress,
        )
        self._futures[job_id] = future

        def _done(fut: Future):
            j = self._jobs.get(job_id)
            if not j:
                return
            try:
                worker_result = fut.result()
            except Exception as exc:
                if j.state == JobState.CANCELLED:
                    j.finished_at = j.finished_at or time.time()
                    return
                j.state = JobState.FAILED
                j.error = str(exc)
                j.finished_at = time.time()
                return

            status = worker_result.get("status") if isinstance(worker_result, dict) else "completed"
            result_path = worker_result.get("result_path") if isinstance(worker_result, dict) else worker_result

            if status == "cancelled" or j.state == JobState.CANCELLED:
                j.state = JobState.CANCELLED
            else:
                j.result_path = result_path
                j.state = JobState.COMPLETED
            j.finished_at = time.time()

        future.add_done_callback(_done)
        return job_id

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        future = self._futures.get(job_id)
        if not job or not future:
            return False
        if job.state in TERMINAL_JOB_STATES or future.done():
            return False

        # Signal cancellation regardless of whether the future was already
        # picked up by a worker; the worker polls _cancel_requested().
        future.cancel()
        job.state = JobState.CANCELLED
        job.finished_at = time.time()
        _write_progress(self._progress, job_id, state="cancelled", cancel_requested=True)
        return True

    def shutdown(self):
        self._pool.shutdown(wait=False)


# Module-level singleton
job_manager = JobManager(max_workers=2)
