"""Tests for :mod:`src.web.db` — connection factory and migration runner."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.web import db


def test_connect_enables_wal_and_foreign_keys(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    try:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert journal_mode == "wal"
        assert fk == 1
    finally:
        conn.close()


def test_connect_creates_parent_directories(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c" / "test.db"
    conn = db.connect(nested)
    try:
        assert nested.exists()
        assert nested.parent.is_dir()
    finally:
        conn.close()


def test_migrations_apply_in_order_and_record_versions(tmp_path: Path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_first.sql").write_text("CREATE TABLE one (x INTEGER);")
    (migrations / "002_second.sql").write_text("CREATE TABLE two (y INTEGER);")

    conn = db.connect(tmp_path / "test.db")
    try:
        applied = db.run_migrations(conn, migrations)
        assert applied == [1, 2]

        rows = conn.execute(
            "SELECT version FROM schema_version ORDER BY version"
        ).fetchall()
        assert [r["version"] for r in rows] == [1, 2]

        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "one" in tables
        assert "two" in tables
    finally:
        conn.close()


def test_migrations_are_idempotent(tmp_path: Path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_only.sql").write_text("CREATE TABLE only_t (x INTEGER);")

    conn = db.connect(tmp_path / "test.db")
    try:
        first = db.run_migrations(conn, migrations)
        second = db.run_migrations(conn, migrations)
        assert first == [1]
        assert second == []
    finally:
        conn.close()


def test_migration_failure_does_not_record_version(tmp_path: Path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    # Invalid SQL — executescript is not atomic for DDL, but the version row
    # must NOT be recorded so the next boot retries the migration. Migration
    # files are expected to use ``IF NOT EXISTS`` for retry safety.
    (migrations / "001_broken.sql").write_text("THIS IS NOT VALID SQL;")

    conn = db.connect(tmp_path / "test.db")
    try:
        with pytest.raises(Exception):
            db.run_migrations(conn, migrations)
        rows = conn.execute("SELECT version FROM schema_version").fetchall()
        assert rows == []
    finally:
        conn.close()


def test_transaction_commits_on_success(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    try:
        conn.execute("CREATE TABLE t (x INTEGER)")
        with db.transaction(conn):
            conn.execute("INSERT INTO t VALUES (1)")
            conn.execute("INSERT INTO t VALUES (2)")
        count = conn.execute("SELECT COUNT(*) AS c FROM t").fetchone()["c"]
        assert count == 2
    finally:
        conn.close()


def test_transaction_rolls_back_on_exception(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    try:
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (42)")
        with pytest.raises(RuntimeError):
            with db.transaction(conn):
                conn.execute("INSERT INTO t VALUES (99)")
                raise RuntimeError("boom")
        rows = conn.execute("SELECT x FROM t").fetchall()
        assert [r["x"] for r in rows] == [42]
    finally:
        conn.close()
