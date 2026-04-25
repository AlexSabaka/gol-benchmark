"""SQLite connection + migration runner for the GoL Benchmark data layer.

Single-file SQLite database at ``{data_root}/gol.db`` holds mutable application
state (jobs, annotations, result/testset metadata index). Large immutable blobs
(result payloads, testsets, pause checkpoints) remain on disk and are referenced
by path from the DB.

Connections are WAL-mode, foreign-key-enforcing, and autocommit at the driver
level — transactions are managed explicitly via :func:`transaction`. The module
is deliberately small so it stays easy to audit.

Usage::

    conn = connect(web_config.db_path)
    run_migrations(conn)
    # ...construct JobStore / AnnotationStore with the live connection...
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "db_migrations"


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open a SQLite connection with WAL + FK pragmas applied.

    ``isolation_level=None`` puts the driver in autocommit mode; transactions
    must be opened explicitly via :func:`transaction`. That's deliberate —
    the alternative (Python's implicit BEGIN) interacts poorly with DDL and
    with ``executescript``.
    """
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Explicit transaction boundary — BEGIN on enter, COMMIT/ROLLBACK on exit."""
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_schema_version_table(conn)
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) AS v FROM schema_version"
    ).fetchone()
    return int(row["v"]) if row else 0


def run_migrations(
    conn: sqlite3.Connection, migrations_dir: Path | None = None
) -> list[int]:
    """Apply pending SQL migrations in numeric order, return versions applied.

    Migration files are ``NNN_name.sql`` under ``migrations_dir`` (default
    :data:`MIGRATIONS_DIR`). Each file is applied inside its own transaction
    and the version is recorded in ``schema_version``. Idempotent — already-
    applied versions are skipped.
    """
    migrations_dir = migrations_dir or MIGRATIONS_DIR
    _ensure_schema_version_table(conn)
    if not migrations_dir.exists():
        return []

    existing = current_version(conn)
    pending: list[tuple[int, Path]] = []
    for p in sorted(migrations_dir.glob("*.sql")):
        prefix = p.name.split("_", 1)[0]
        try:
            version = int(prefix)
        except ValueError:
            logger.warning("Skipping migration with non-numeric prefix: %s", p.name)
            continue
        if version > existing:
            pending.append((version, p))

    applied: list[int] = []
    for version, path in pending:
        sql = path.read_text(encoding="utf-8")
        logger.info("Applying migration %03d (%s)", version, path.name)
        # ``executescript`` issues an implicit COMMIT before running and cannot
        # be wrapped in our :func:`transaction` helper. If it fails mid-script
        # we intentionally do NOT record the version — the next startup will
        # retry the migration. Migration files should therefore use ``CREATE
        # TABLE IF NOT EXISTS`` / similar so a retry after partial application
        # is idempotent.
        try:
            conn.executescript(sql)
        except Exception:
            logger.exception("Migration %03d (%s) failed — not recorded", version, path.name)
            raise
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        applied.append(version)
    return applied
