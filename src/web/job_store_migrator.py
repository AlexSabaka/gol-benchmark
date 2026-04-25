"""One-shot migration from file-backed job records to SQLite.

Scans ``jobs_dir`` for legacy ``{job_id}.json`` records, upserts each into the
DB via :class:`JobStore`, and moves the originals to ``backup_dir`` for
rollback. Idempotent — on second run the source files are already gone.

Not called automatically; ``src/web/app.py`` invokes it inside the lifespan
handler so a fresh server boot picks up pre-existing jobs exactly once.
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from src.web.job_store import JobStore

logger = logging.getLogger(__name__)


def migrate_json_jobs_to_db(
    store: JobStore,
    jobs_dir: Path | str,
    backup_dir: Path | str,
) -> int:
    """Copy any ``{jobs_dir}/*.json`` job records into the DB.

    Returns the number of records migrated. Subdirectories (e.g.
    ``jobs_dir/partial``) are ignored. Source files are moved to
    ``backup_dir`` after a successful DB insert so re-runs are no-ops.

    Import is deferred to avoid pulling in the Job class during tests that
    only exercise the raw JobStore surface.
    """
    # Local import — ``Job`` pulls in crypto / web_config which we don't
    # need for JobStore-only tests.
    from src.web.jobs import Job

    jobs_path = Path(jobs_dir)
    backup_path = Path(backup_dir)
    if not jobs_path.exists():
        return 0

    candidates = [p for p in jobs_path.glob("*.json") if p.is_file()]
    if not candidates:
        return 0

    backup_path.mkdir(parents=True, exist_ok=True)
    migrated = 0
    for src in candidates:
        try:
            with src.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception as exc:
            logger.warning("Skipping unreadable job file %s: %s", src, exc)
            continue
        try:
            # Round-trip through Job to normalize legacy plaintext credentials
            # into the v2 encrypted envelope before they hit the DB.
            normalized = Job.from_stored_dict(raw).to_storable_dict()
        except Exception as exc:
            logger.warning("Skipping malformed job file %s: %s", src, exc)
            continue
        try:
            store.save_job(normalized)
        except Exception as exc:
            logger.warning("Could not migrate job file %s: %s", src, exc)
            continue

        dst = backup_path / src.name
        try:
            shutil.move(str(src), str(dst))
        except Exception as exc:
            # DB already has the record; if move fails we'll re-migrate next
            # boot (upsert is idempotent) so this is recoverable.
            logger.warning("Migrated %s but could not move to backup: %s", src, exc)
            continue
        migrated += 1

    if migrated:
        logger.info(
            "Migrated %d job record(s) from %s → SQLite (originals moved to %s)",
            migrated,
            jobs_path,
            backup_path,
        )
    return migrated
