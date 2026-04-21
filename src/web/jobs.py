"""Background job manager for benchmark execution (Stage 2).

Uses concurrent.futures.ProcessPoolExecutor for CPU/GPU-bound model inference.
Job records are persisted to a JSON file via JobStore so history survives restarts.
"""
from __future__ import annotations

import logging
import multiprocessing
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.web.crypto import decrypt_str, encrypt_str
from src.web.job_store import JobStore

logger = logging.getLogger(__name__)

# Bumped when the stored-dict shape changes in a way that requires differentiated
# deserialization. v2 introduces Fernet-encrypted credential fields (TD-085):
# ``api_key_enc`` / ``api_base_enc`` replace the plaintext ``api_key`` / ``api_base``.
JOB_SCHEMA_VERSION = 2


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# States from which a job cannot transition further (except PAUSED, which can resume).
TERMINAL_JOB_STATES = {
    JobState.COMPLETED,
    JobState.FAILED,
    JobState.CANCELLED,
}


@dataclass
class Job:
    # Identity
    id: str
    model_name: str
    testset_path: str
    run_group_id: Optional[str] = None

    # Runtime state
    state: JobState = JobState.PENDING
    progress_current: int = 0
    progress_total: int = 0
    result_path: Optional[str] = None
    error: Optional[str] = None

    # Timestamps
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    # Pause / resume support
    paused_at_index: Optional[int] = None
    partial_result_path: Optional[str] = None

    # Execution parameters — stored so the job can be resumed with the same settings
    provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    output_dir: str = "results"
    temperature: float = 0.1
    max_tokens: int = 2048
    no_think: bool = True
    api_key: str = ""
    api_base: str = ""

    # Cumulative elapsed from all previous paused segments (carried over on resume)
    accumulated_elapsed_seconds: float = 0.0
    # Test index this job started from (0 for fresh; paused_at_index for resumed)
    start_index: int = 0

    # Internal housekeeping — not exposed in to_dict()
    hidden: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for the REST API (includes computed elapsed_seconds and eta_seconds)."""
        now = time.time()
        # Cumulative duration = prior segments + current segment
        elapsed = None
        if self.started_at is not None:
            end = self.finished_at or now
            elapsed = round(self.accumulated_elapsed_seconds + (end - self.started_at), 1)

        # ETA: rate is based only on tests processed in THIS segment so resumed jobs
        # don't dilute the rate with the prior (paused) segment's throughput.
        eta_seconds = None
        if (self.state == JobState.RUNNING and self.started_at is not None
                and self.progress_current > self.start_index
                and self.progress_total > self.progress_current):
            current_segment_elapsed = now - self.started_at
            if current_segment_elapsed > 0:
                tests_in_segment = self.progress_current - self.start_index
                rate = tests_in_segment / current_segment_elapsed  # tests/sec
                remaining = self.progress_total - self.progress_current
                eta_seconds = round(remaining / rate, 1)

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
            "eta_seconds": eta_seconds,
            "paused_at_index": self.paused_at_index,
            "partial_result_path": self.partial_result_path,
        }

    def to_storable_dict(self) -> Dict[str, Any]:
        """Serialize all persistent fields for the JobStore (no computed fields).

        Credentials (``api_key`` / ``api_base``) are Fernet-encrypted at rest
        under keys ``api_key_enc`` / ``api_base_enc`` — see ``src/web/crypto.py``.
        The plaintext keys are intentionally never written by v2 records.
        """
        return {
            "schema_version": JOB_SCHEMA_VERSION,
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
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "paused_at_index": self.paused_at_index,
            "partial_result_path": self.partial_result_path,
            "provider": self.provider,
            "ollama_host": self.ollama_host,
            "output_dir": self.output_dir,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "no_think": self.no_think,
            "api_key_enc": encrypt_str(self.api_key),
            "api_base_enc": encrypt_str(self.api_base),
            "accumulated_elapsed_seconds": self.accumulated_elapsed_seconds,
            "start_index": self.start_index,
            "hidden": self.hidden,
        }

    @classmethod
    def from_stored_dict(cls, d: Dict[str, Any]) -> "Job":
        """Reconstruct a Job from a stored dict (ignores unknown keys).

        Accepts both v2 (encrypted credential envelope) and legacy plaintext
        records. Legacy records upgrade to v2 on the next ``_persist_job()``
        call naturally — no migration script needed.
        """
        known = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in known}
        # Coerce state string back to enum
        if "state" in filtered and isinstance(filtered["state"], str):
            filtered["state"] = JobState(filtered["state"])

        # Credential resolution: encrypted fields take precedence when present,
        # so a v2 record with stale plaintext leftovers prefers the ciphertext.
        if "api_key_enc" in d:
            filtered["api_key"] = decrypt_str(d.get("api_key_enc"))
        if "api_base_enc" in d:
            filtered["api_base"] = decrypt_str(d.get("api_base_enc"))
        if d.get("schema_version") is None and ("api_key" in d or "api_base" in d):
            logger.debug(
                "Legacy plaintext credentials in job %s — will be encrypted on next save.",
                d.get("id"),
            )

        return cls(**filtered)


# ── Progress-dict helpers (used by both the manager and subprocess workers) ──

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


def _pause_requested(progress_dict: dict, job_id: str) -> bool:
    current = _read_progress(progress_dict, job_id)
    return bool(current.get("pause_requested"))


def _stop_dump_requested(progress_dict: dict, job_id: str) -> bool:
    current = _read_progress(progress_dict, job_id)
    return bool(current.get("stop_dump_requested"))


# ── Subprocess worker ─────────────────────────────────────────────────────────

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
    start_index: int = 0,
    partial_result_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Worker function executed in a subprocess.

    Returns a status payload so the parent can distinguish normal completion,
    cooperative cancellation, and cooperative pause (with checkpoint index).
    """
    import json, gzip, time as _time, os

    # Load test set
    with gzip.open(testset_path, "rt", encoding="utf-8") as f:
        testset = json.load(f)

    test_cases = testset.get("test_cases", [])
    total = len(test_cases)
    _write_progress(progress_dict, job_id, current=start_index, total=total, state="running")

    # Build model interface
    from src.models import OllamaInterface, HuggingFaceInterface, OpenAICompatibleInterface
    if provider == "ollama":
        model = OllamaInterface(model_name, base_url=ollama_host)
    elif provider == "openai_compatible":
        base = api_base or ollama_host
        model = OpenAICompatibleInterface(model_name, base_url=base, api_key=api_key)
    elif provider == "huggingface":
        if api_key:
            os.environ["HF_TOKEN"] = api_key
        model = HuggingFaceInterface(model_name)
    else:
        model = HuggingFaceInterface(model_name)

    from src.stages.run_testset import parse_answer_via_plugin, evaluate_via_plugin

    # Load partial results from a previous paused run (if any)
    results_list = []
    prev_correct = 0
    prev_input_tokens = 0
    prev_output_tokens = 0
    if partial_result_path and os.path.exists(partial_result_path):
        try:
            with gzip.open(partial_result_path, "rt", encoding="utf-8") as f:
                prev_data = json.load(f)
            results_list = prev_data.get("results", [])
            prev_stats = prev_data.get("summary_statistics", {})
            prev_correct = prev_stats.get("correct_responses", 0)
            prev_input_tokens = prev_stats.get("total_input_tokens", 0)
            prev_output_tokens = prev_stats.get("total_output_tokens", 0)
        except Exception:
            results_list = []

    correct = prev_correct
    total_input_tokens = prev_input_tokens
    total_output_tokens = prev_output_tokens
    start_time = _time.time()

    for i, tc in enumerate(test_cases):
        # Skip already-processed test cases from a previous run
        if i < start_index:
            continue

        if _cancel_requested(progress_dict, job_id):
            _write_progress(progress_dict, job_id, current=i, total=total, state="cancelled")
            return {"status": "cancelled", "result_path": None}

        if _stop_dump_requested(progress_dict, job_id):
            # Save a complete result file from current results and mark completed
            out_path = _finalize_and_save(
                results_list, testset, model_name, provider, run_group_id,
                job_id, output_dir, len(results_list), correct,
                total_input_tokens, total_output_tokens, partial_result_path, start_time,
            )
            _write_progress(progress_dict, job_id, current=i, total=total, state="completed", result_path=out_path)
            return {"status": "completed", "result_path": out_path}

        if _pause_requested(progress_dict, job_id):
            # Save partial results and report paused checkpoint
            partial_path = _save_partial_results(
                results_list, testset, model_name, provider, run_group_id,
                job_id, output_dir, i, correct, total_input_tokens, total_output_tokens,
            )
            _write_progress(progress_dict, job_id, current=i, total=total, state="paused")
            return {"status": "paused", "paused_at_index": i, "partial_result_path": partial_path}

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
            reasoning = resp.get("reasoning") or None
            task_type = tc.get("task_type", "")
            task_params = tc.get("task_params", {})

            # Merge prompt_metadata into task_params so parser gets language
            prompt_meta = tc.get("prompt_metadata", {})
            enriched_params = dict(task_params)
            for key in ("language", "user_style", "system_style"):
                if key in prompt_meta and key not in enriched_params:
                    enriched_params[key] = prompt_meta[key]

            # `parse_answer_via_plugin` returns the full `ParsedAnswer`; we
            # split the raw value (downstream evaluators + JSON serialization)
            # from the strategy / confidence (persisted into `output.*` so the
            # Human Review aggregator can attribute parser_false_positive cases
            # to the strategy that fired).
            parsed_result = parse_answer_via_plugin(raw_response, task_type, enriched_params)
            if parsed_result is None:
                parsed = None
                parse_strategy = None
                parse_confidence = None
            else:
                parsed = parsed_result.value
                parse_strategy = parsed_result.parse_strategy
                parse_confidence = parsed_result.confidence
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
                "output": {
                    "raw_response": raw_response,
                    "reasoning": reasoning,
                    "parsed_answer": str(parsed) if parsed is not None else None,
                    "parse_strategy": parse_strategy,
                    "parse_confidence": parse_confidence,
                },
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

    out_path = _finalize_and_save(
        results_list, testset, model_name, provider, run_group_id,
        job_id, output_dir, total, correct,
        total_input_tokens, total_output_tokens, partial_result_path, start_time,
    )
    _write_progress(progress_dict, job_id, current=total, total=total, state="completed", result_path=out_path)
    return {"status": "completed", "result_path": out_path}


def _finalize_and_save(
    results_list: list,
    testset: dict,
    model_name: str,
    provider: str,
    run_group_id: Optional[str],
    job_id: str,
    output_dir: str,
    processed_count: int,
    correct: int,
    total_input_tokens: int,
    total_output_tokens: int,
    partial_result_path: Optional[str],
    start_time: float,
) -> str:
    """Build and write a complete result file; clean up any partial file. Returns out_path."""
    import json, gzip, time as _time, os

    duration = _time.time() - start_time
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
            "accuracy": round(correct / max(processed_count, 1), 4),
            "correct_responses": correct,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        "results": results_list,
    }
    os.makedirs(output_dir, exist_ok=True)
    safe_model = model_name.replace("/", "_").replace(":", "_")
    ts = _time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_dir, f"results_{safe_model}_{ts}.json.gz")
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, default=str)
    if partial_result_path and os.path.exists(partial_result_path):
        try:
            os.unlink(partial_result_path)
        except Exception:
            pass
    return out_path


def _save_partial_results(
    results_list: list,
    testset: dict,
    model_name: str,
    provider: str,
    run_group_id: Optional[str],
    job_id: str,
    output_dir: str,
    paused_at: int,
    correct: int,
    total_input_tokens: int,
    total_output_tokens: int,
) -> str:
    """Save in-progress results to a partial file and return its path."""
    import json, gzip, time as _time, os

    os.makedirs(output_dir, exist_ok=True)
    partial_data = {
        "format_version": "1.0.0",
        "partial": True,
        "paused_at_index": paused_at,
        "metadata": {
            "result_id": job_id,
            "timestamp": _time.strftime("%Y%m%d_%H%M%S"),
            "run_group_id": run_group_id,
        },
        "model_info": {"model_name": model_name, "provider": provider},
        "testset_metadata": testset.get("metadata", {}),
        "summary_statistics": {
            "correct_responses": correct,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        "results": results_list,
    }
    # Pause checkpoints live under web_config.partial_dir (data/jobs/partial/)
    # so the results directory stays clean. `output_dir` is still needed for
    # finalized result files but not for transient checkpoints.
    from src.web.config import web_config
    partial_path = str(web_config.partial_path_for(job_id))
    os.makedirs(os.path.dirname(partial_path), exist_ok=True)
    with gzip.open(partial_path, "wt", encoding="utf-8") as f:
        json.dump(partial_data, f, indent=2, default=str)
    return partial_path


# ── Job manager ───────────────────────────────────────────────────────────────

class JobManager:
    """Job manager backed by ProcessPoolExecutor with optional JSON persistence."""

    def __init__(self, max_workers: int = 2, job_store: Optional[JobStore] = None) -> None:
        self._manager = multiprocessing.Manager()
        self._progress: dict = self._manager.dict()
        self._jobs: Dict[str, Job] = {}
        self._futures: Dict[str, Future] = {}
        self._pool = ProcessPoolExecutor(max_workers=max_workers)
        self._store: Optional[JobStore] = job_store

    # ── Persistence ────────────────────────────────────────────────────────

    def load_from_store(self) -> None:
        """Load historical jobs from the store (call once on server startup)."""
        if self._store is None:
            return
        for record in self._store.load_all():
            try:
                job = Job.from_stored_dict(record)
            except Exception as exc:
                logger.warning("Skipping malformed job record: %s", exc)
                continue
            # Jobs that were active when the server last shut down cannot be resumed
            # automatically (their worker processes are gone).
            if job.state in (JobState.PENDING, JobState.RUNNING):
                job.state = JobState.FAILED
                job.error = "Interrupted by server restart"
                job.finished_at = job.finished_at or time.time()
            self._jobs[job.id] = job
        logger.info("Loaded %d historical jobs from store", len(self._jobs))

    def save_to_store(self) -> None:
        """Bulk-save all jobs to the store (call on server shutdown)."""
        if self._store is None:
            return
        records = [job.to_storable_dict() for job in self._jobs.values()]
        try:
            self._store.save_all(records)
            logger.info("Saved %d jobs to store", len(records))
        except Exception as exc:
            logger.warning("Could not save jobs to store: %s", exc)

    def _persist_job(self, job: Job) -> None:
        """Immediately persist a single job (called after terminal state transitions)."""
        if self._store is None:
            return
        try:
            self._store.save_job(job.to_storable_dict())
        except Exception as exc:
            logger.warning("Could not persist job %s: %s", job.id, exc)

    # ── Submission ──────────────────────────────────────────────────────────

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
        start_index: int = 0,
        partial_result_path: Optional[str] = None,
        job_id: Optional[str] = None,
        accumulated_elapsed_seconds: float = 0.0,
    ) -> str:
        job_id = job_id or uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            model_name=model_name,
            testset_path=testset_path,
            run_group_id=run_group_id,
            provider=provider,
            ollama_host=ollama_host,
            output_dir=output_dir,
            temperature=temperature,
            max_tokens=max_tokens,
            no_think=no_think,
            api_key=api_key,
            api_base=api_base,
            accumulated_elapsed_seconds=accumulated_elapsed_seconds,
            start_index=start_index,
        )
        self._jobs[job_id] = job
        _write_progress(self._progress, job_id, current=start_index, total=0, state="pending", cancel_requested=False)

        future = self._pool.submit(
            _run_testset_worker,
            testset_path, model_name, run_group_id, provider, ollama_host,
            output_dir, temperature, max_tokens, no_think,
            self._progress, job_id,
            api_key, api_base, start_index, partial_result_path,
        )
        self._futures[job_id] = future
        future.add_done_callback(lambda f, jid=job_id: self._on_done(jid, f))
        return job_id

    def _on_done(self, job_id: str, future: Future) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        try:
            worker_result = future.result()
        except Exception as exc:
            if job.state == JobState.CANCELLED:
                job.finished_at = job.finished_at or time.time()
                self._persist_job(job)
                return
            job.state = JobState.FAILED
            job.error = str(exc)
            job.finished_at = time.time()
            self._persist_job(job)
            return

        status = worker_result.get("status") if isinstance(worker_result, dict) else "completed"
        result_path = worker_result.get("result_path") if isinstance(worker_result, dict) else worker_result

        if status == "cancelled" or job.state == JobState.CANCELLED:
            job.state = JobState.CANCELLED
            job.finished_at = job.finished_at or time.time()
        elif status == "paused":
            job.state = JobState.PAUSED
            job.paused_at_index = worker_result.get("paused_at_index")
            job.partial_result_path = worker_result.get("partial_result_path")
            job.finished_at = time.time()
        else:
            job.state = JobState.COMPLETED
            job.result_path = result_path
            job.finished_at = time.time()

        self._persist_job(job)

    # ── Query ───────────────────────────────────────────────────────────────

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        # Sync live progress from the shared dict (only meaningful for active workers)
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
        return [
            self.get_status(jid)
            for jid in sorted(self._jobs, key=lambda k: self._jobs[k].created_at, reverse=True)
            if not self._jobs[jid].hidden
        ]

    # ── Actions ──────────────────────────────────────────────────────────────

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        future = self._futures.get(job_id)
        if not job or not future:
            return False
        if job.state in TERMINAL_JOB_STATES or future.done():
            return False

        # Signal cancellation; worker polls _cancel_requested() between test cases.
        future.cancel()
        job.state = JobState.CANCELLED
        job.finished_at = time.time()
        _write_progress(self._progress, job_id, state="cancelled", cancel_requested=True)
        return True

    def pause(self, job_id: str) -> bool:
        """Signal a running job to pause cooperatively after the current test case."""
        job = self._jobs.get(job_id)
        future = self._futures.get(job_id)
        if not job or not future:
            return False
        if job.state != JobState.RUNNING or future.done():
            return False

        # Set pause_requested flag; worker checks _pause_requested() between test cases.
        # Do NOT call future.cancel() — the worker must finish its current test case
        # cleanly so it can save a consistent partial result file.
        current = _read_progress(self._progress, job_id)
        self._progress[job_id] = {**current, "pause_requested": True}
        return True

    def stop_and_dump(self, job_id: str) -> bool:
        """Stop a job and write a final result file.

        For running jobs: sets a cooperative signal; the worker finalizes after
        the current test case and exits cleanly.
        For paused jobs: the worker has already exited; we finalize directly from
        the partial checkpoint file in the manager process.
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.state == JobState.PAUSED:
            # Worker is gone — load partial file and finalize synchronously.
            import json, gzip, os as _os
            results_list: list = []
            correct = 0
            total_input_tokens = 0
            total_output_tokens = 0
            if job.partial_result_path and _os.path.exists(job.partial_result_path):
                try:
                    with gzip.open(job.partial_result_path, "rt", encoding="utf-8") as f:
                        prev = json.load(f)
                    results_list = prev.get("results", [])
                    stats = prev.get("summary_statistics", {})
                    correct = stats.get("correct_responses", 0)
                    total_input_tokens = stats.get("total_input_tokens", 0)
                    total_output_tokens = stats.get("total_output_tokens", 0)
                except Exception:
                    pass
            try:
                with gzip.open(job.testset_path, "rt", encoding="utf-8") as f:
                    testset = json.load(f)
            except Exception:
                testset = {}
            # Reconstruct a fake start_time so _finalize_and_save records correct duration.
            segment_elapsed = 0.0
            if job.started_at is not None and job.finished_at is not None:
                segment_elapsed = job.finished_at - job.started_at
            total_elapsed = job.accumulated_elapsed_seconds + segment_elapsed
            fake_start = time.time() - total_elapsed
            out_path = _finalize_and_save(
                results_list, testset, job.model_name, job.provider, job.run_group_id,
                job.id, job.output_dir, len(results_list), correct,
                total_input_tokens, total_output_tokens, job.partial_result_path, fake_start,
            )
            job.state = JobState.COMPLETED
            job.result_path = out_path
            job.partial_result_path = None
            job.finished_at = time.time()
            self._persist_job(job)
            return True

        # For running jobs: signal via shared dict; worker picks it up cooperatively.
        future = self._futures.get(job_id)
        if not future or job.state != JobState.RUNNING or future.done():
            return False
        current = _read_progress(self._progress, job_id)
        self._progress[job_id] = {**current, "stop_dump_requested": True}
        return True

    def resume(self, job_id: str) -> Optional[str]:
        """Resume a paused job. Returns the new job_id, or None if not resumable."""
        job = self._jobs.get(job_id)
        if not job or job.state != JobState.PAUSED:
            return None

        # Accumulate elapsed time from this paused segment so Duration stays cumulative.
        segment_elapsed = 0.0
        if job.started_at is not None and job.finished_at is not None:
            segment_elapsed = job.finished_at - job.started_at
        accumulated = job.accumulated_elapsed_seconds + segment_elapsed

        # Mark the paused job as superseded and hide it from the job list
        job.state = JobState.CANCELLED
        job.error = "Superseded by resumed job"
        job.hidden = True
        self._persist_job(job)

        # Submit a new job continuing from the checkpoint, inheriting the same params.
        new_job_id = self.submit(
            testset_path=job.testset_path,
            model_name=job.model_name,
            run_group_id=job.run_group_id,
            provider=job.provider,
            ollama_host=job.ollama_host,
            output_dir=job.output_dir,
            temperature=job.temperature,
            max_tokens=job.max_tokens,
            no_think=job.no_think,
            api_key=job.api_key,
            api_base=job.api_base,
            start_index=job.paused_at_index or 0,
            partial_result_path=job.partial_result_path,
            accumulated_elapsed_seconds=accumulated,
        )
        return new_job_id

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

        def _done(fut: Future) -> None:
            j = self._jobs.get(job_id)
            if not j:
                return
            try:
                worker_result = fut.result()
            except Exception as exc:
                if j.state == JobState.CANCELLED:
                    j.finished_at = j.finished_at or time.time()
                    self._persist_job(j)
                    return
                j.state = JobState.FAILED
                j.error = str(exc)
                j.finished_at = time.time()
                self._persist_job(j)
                return

            status = worker_result.get("status") if isinstance(worker_result, dict) else "completed"
            result_path = worker_result.get("result_path") if isinstance(worker_result, dict) else worker_result

            if status == "cancelled" or j.state == JobState.CANCELLED:
                j.state = JobState.CANCELLED
            else:
                j.result_path = result_path
                j.state = JobState.COMPLETED
            j.finished_at = time.time()
            self._persist_job(j)

        future.add_done_callback(_done)
        return job_id

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False)


# ── Module-level singleton (store wired in by app.py lifespan) ────────────────
job_manager = JobManager(max_workers=2)
