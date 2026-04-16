"""Job persistence layer — serializes/deserializes Job records to a JSON file.

All JSON I/O is confined to this module. To switch backends (e.g. MongoDB, Redis),
replace the implementation of JobStore without touching any other file.

Storage format (jobs.json):
    {
        "version": 1,
        "jobs": {
            "<job_id>": { <job record dict> },
            ...
        }
    }

Configure path via GOL_JOBS_FILE env var (default: jobs.json at project root).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1


class JobStore:
    """Persistence layer for Job records.

    Interface is intentionally minimal so it can be backed by any store:
        load_all()         → list[dict]
        save_job(d)        → None
        save_all(ds)       → None
        delete_job(id)     → None
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    # ── Public interface ──────────────────────────────────────────────────────

    def load_all(self) -> list[dict[str, Any]]:
        """Return all saved job records. Returns [] if file is missing or corrupt."""
        if not self._path.exists():
            return []
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            jobs_map: dict = data.get("jobs", {})
            return list(jobs_map.values())
        except Exception as exc:
            logger.warning("Could not load jobs from %s: %s", self._path, exc)
            return []

    def save_job(self, job_dict: dict[str, Any]) -> None:
        """Upsert a single job record. Atomic write (temp file → rename)."""
        data = self._read_raw()
        data.setdefault("jobs", {})[job_dict["id"]] = job_dict
        self._write_raw(data)

    def save_all(self, job_dicts: list[dict[str, Any]]) -> None:
        """Bulk-save all job records, replacing existing file contents."""
        data = {"version": _SCHEMA_VERSION, "jobs": {d["id"]: d for d in job_dicts}}
        self._write_raw(data)

    def delete_job(self, job_id: str) -> None:
        """Remove a job record by ID (no-op if not present)."""
        data = self._read_raw()
        data.setdefault("jobs", {}).pop(job_id, None)
        self._write_raw(data)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _read_raw(self) -> dict:
        if not self._path.exists():
            return {"version": _SCHEMA_VERSION, "jobs": {}}
        try:
            with self._path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Corrupt jobs file %s, starting fresh: %s", self._path, exc)
            return {"version": _SCHEMA_VERSION, "jobs": {}}

    def _write_raw(self, data: dict) -> None:
        """Atomic write: write to temp file in same directory, then rename."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix=".json", dir=self._path.parent)
        try:
            os.close(fd)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp, self._path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
