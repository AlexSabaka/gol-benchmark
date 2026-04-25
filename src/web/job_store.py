"""Job persistence layer — SQLite-backed (Phase 1 migration).

All job I/O is confined to this module. To switch backends (Postgres, Redis),
replace the implementation of :class:`JobStore` without touching any other
file. The public interface is deliberately minimal::

    load_all()         → list[dict]
    save_job(d)        → None
    save_all(ds)       → None
    delete_job(id)     → None

Storage: the ``jobs`` table in ``{data_root}/gol.db``. Schema defined in
``src/web/db_migrations/001_jobs.sql``. See :mod:`src.web.db` for the
connection factory and migration runner.

File-backed predecessor: pre-v2.27 stored one JSON per job under
``data/jobs/``. The ``scripts/migrate_jobs_to_sqlite.py`` one-shot copies
those records into the DB and moves the originals to ``data/jobs.bak/``
for rollback.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

from src.web.db import run_migrations, transaction

logger = logging.getLogger(__name__)

# Column list — mirrors Job.to_storable_dict(). Order is load-bearing for the
# INSERT placeholder tuple, so don't reorder without regenerating the upsert.
_COLUMNS: tuple[str, ...] = (
    "id",
    "schema_version",
    "model_name",
    "testset_path",
    "run_group_id",
    "state",
    "progress_current",
    "progress_total",
    "result_path",
    "error",
    "created_at",
    "started_at",
    "finished_at",
    "paused_at_index",
    "partial_result_path",
    "provider",
    "ollama_host",
    "output_dir",
    "temperature",
    "max_tokens",
    "no_think",
    "api_key_enc",
    "api_base_enc",
    "accumulated_elapsed_seconds",
    "start_index",
    "hidden",
)

# Defaults for NOT NULL columns when a legacy record omits them. Matches the
# dataclass defaults on ``Job``.
_DEFAULTS: dict[str, Any] = {
    "schema_version": 2,
    "state": "pending",
    "progress_current": 0,
    "progress_total": 0,
    "created_at": 0.0,
    "provider": "ollama",
    "ollama_host": "http://localhost:11434",
    "output_dir": "results",
    "temperature": 0.1,
    "max_tokens": 2048,
    "no_think": 1,
    "accumulated_elapsed_seconds": 0.0,
    "start_index": 0,
    "hidden": 0,
}

_BOOL_COLUMNS = {"no_think", "hidden"}


def _validate_id(job_id: Any) -> str:
    if not job_id or not isinstance(job_id, str):
        raise ValueError(f"Invalid job id: {job_id!r}")
    return job_id


def _coerce(col: str, value: Any) -> Any:
    """Convert Python dict value to a SQLite-friendly primitive."""
    if value is None:
        return _DEFAULTS.get(col)
    if col in _BOOL_COLUMNS:
        return 1 if value else 0
    return value


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = {k: row[k] for k in row.keys()}
    # Re-hydrate boolean columns so callers receive Python bools (matches the
    # original JSON-file shape).
    for col in _BOOL_COLUMNS:
        if col in d and d[col] is not None:
            d[col] = bool(d[col])
    return d


class JobStore:
    """SQLite-backed persistence for Job records.

    Constructor accepts a live :class:`sqlite3.Connection` — callers (app.py
    lifespan) own the connection lifecycle. Migrations are run on construct
    so hand-rolled test harnesses don't have to remember to call them.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        run_migrations(self._conn)

    # ── Public interface ──────────────────────────────────────────────────────

    def load_all(self) -> list[dict[str, Any]]:
        """Return all job records ordered oldest-first by created_at."""
        cur = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM jobs ORDER BY created_at"
        )
        return [_row_to_dict(r) for r in cur.fetchall()]

    def save_job(self, job_dict: dict[str, Any]) -> None:
        """Upsert a single job record by id."""
        _validate_id(job_dict.get("id"))
        self._upsert(job_dict)

    def save_all(self, job_dicts: list[dict[str, Any]]) -> None:
        """Bulk-save job records; delete any DB rows not in the incoming list."""
        incoming_ids: list[str] = []
        for d in job_dicts:
            incoming_ids.append(_validate_id(d.get("id")))

        with transaction(self._conn):
            for d in job_dicts:
                self._upsert(d)
            if incoming_ids:
                placeholders = ",".join("?" for _ in incoming_ids)
                self._conn.execute(
                    f"DELETE FROM jobs WHERE id NOT IN ({placeholders})",
                    tuple(incoming_ids),
                )
            else:
                self._conn.execute("DELETE FROM jobs")

    def delete_job(self, job_id: str) -> None:
        """Remove a job record by id (no-op if not present)."""
        _validate_id(job_id)
        self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _upsert(self, d: dict[str, Any]) -> None:
        values = tuple(_coerce(col, d.get(col)) for col in _COLUMNS)
        placeholders = ",".join("?" for _ in _COLUMNS)
        assignments = ",".join(
            f"{c}=excluded.{c}" for c in _COLUMNS if c != "id"
        )
        self._conn.execute(
            f"INSERT INTO jobs ({', '.join(_COLUMNS)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {assignments}",
            values,
        )
