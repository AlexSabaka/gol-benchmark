"""Job persistence layer — per-job JSON files under a jobs directory.

All JSON I/O is confined to this module. To switch backends (e.g. MongoDB, Redis),
replace the implementation of JobStore without touching any other file.

Storage layout::

    data/jobs/
    ├── <job_id_1>.json
    ├── <job_id_2>.json
    └── ...

Each file contains a single job record dict. Atomic writes via
``tempfile.mkstemp`` + ``os.replace``.

Path resolution: ``src/web/app.py`` constructs ``JobStore(web_config.jobs_dir)``.
A legacy ``GOL_JOBS_FILE`` env var is accepted and maps to the parent directory
of the referenced file (per-job JSONs live alongside the old monolithic file).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _safe_id(job_id: str) -> str:
    """Reject path-traversal attempts in job IDs. Call before touching the FS."""
    if not job_id or "/" in job_id or "\\" in job_id or job_id in (".", ".."):
        raise ValueError(f"Unsafe job id: {job_id!r}")
    return job_id


class JobStore:
    """Persistence layer for Job records — per-job files under ``jobs_dir``.

    Interface is intentionally minimal so it can be backed by any store:
        load_all()         → list[dict]
        save_job(d)        → None
        save_all(ds)       → None
        delete_job(id)     → None

    Backwards-compat: if ``jobs_dir`` is a path to a legacy ``jobs.json`` file,
    its parent directory is used instead. The legacy monolithic file is not
    read — run ``scripts/migrate_data_layout.py`` to split it.
    """

    def __init__(self, jobs_dir: Path | str) -> None:
        p = Path(jobs_dir)
        if p.suffix == ".json" and not p.is_dir():
            # Legacy path — caller handed us a jobs.json file. Use parent dir.
            p = p.parent
        self._dir = p
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Public interface ──────────────────────────────────────────────────────

    def load_all(self) -> list[dict[str, Any]]:
        """Return all saved job records. Returns [] if dir is empty or unreadable."""
        if not self._dir.exists():
            return []
        records: list[dict[str, Any]] = []
        for f in self._dir.glob("*.json"):
            try:
                with f.open("r", encoding="utf-8") as fh:
                    records.append(json.load(fh))
            except Exception as exc:
                logger.warning("Could not load job file %s: %s", f, exc)
        # Stable ordering on the /jobs page — oldest first, newest last by
        # created_at (strings compare lexicographically for ISO-8601, and
        # numeric epoch floats compare numerically via mixed sort key below).
        records.sort(key=lambda d: d.get("created_at") or 0)
        return records

    def save_job(self, job_dict: dict[str, Any]) -> None:
        """Upsert a single job record. Atomic write (temp file → rename)."""
        job_id = _safe_id(str(job_dict.get("id", "")))
        self._write_one(job_id, job_dict)

    def save_all(self, job_dicts: list[dict[str, Any]]) -> None:
        """Bulk-save all job records; delete any on-disk files not in the list."""
        incoming_ids = set()
        for d in job_dicts:
            jid = _safe_id(str(d.get("id", "")))
            incoming_ids.add(jid)
            self._write_one(jid, d)
        # Prune files that no longer correspond to known jobs.
        for f in self._dir.glob("*.json"):
            if f.stem not in incoming_ids:
                try:
                    f.unlink()
                except OSError as exc:
                    logger.warning("Could not prune stale job file %s: %s", f, exc)

    def delete_job(self, job_id: str) -> None:
        """Remove a job record by ID (no-op if not present)."""
        jid = _safe_id(job_id)
        target = self._dir / f"{jid}.json"
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("Could not delete job file %s: %s", target, exc)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _write_one(self, job_id: str, data: dict[str, Any]) -> None:
        """Atomic write: write to temp file in same directory, then rename."""
        target = self._dir / f"{job_id}.json"
        fd, tmp = tempfile.mkstemp(prefix=".job-", suffix=".json", dir=str(self._dir))
        try:
            os.close(fd)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp, target)
        except Exception:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            raise
