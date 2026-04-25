"""Annotation persistence layer — SQLite-backed (Phase 2 migration).

Replaces the ``data/annotations/{stem}.json.gz`` sidecar files. The public
surface is:

    load_for_file(result_file_id)                  → sidecar-shaped dict | None
    save_case(result_file_id, case_id, response_hash, case_record)
    delete_file(result_file_id)                    → int rows deleted
    delete_case(result_file_id, case_id, response_hash) → bool
    list_annotated_result_files()                  → set[str]

``load_for_file`` returns a dict with the same ``{"meta": {...}, "cases": {...}}``
shape the sidecar files produced, so the improvement-report aggregator in
:mod:`src.web.human_review_aggregator` can consume it unchanged.

Schema defined in :file:`db_migrations/002_annotations.sql`.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from src.web.db import run_migrations, transaction

logger = logging.getLogger(__name__)

# JSON-array columns — persisted as TEXT, loaded back as Python lists.
_JSON_ARRAY_COLUMNS: tuple[str, ...] = (
    "spans",
    "response_classes",
    "context_anchors",
    "answer_keywords",
    "negative_spans",
    "negative_keywords",
    "context_windows",
)

# All scalar annotation fields that travel inside the nested ``annotation``
# dict of the case record (alongside the array fields above).
_ANNOTATION_SCALAR_FIELDS: tuple[str, ...] = ("annotator_note", "timestamp")

# Per-case context columns (live at the top level of the case record).
_CASE_CONTEXT_COLUMNS: tuple[str, ...] = (
    "response_length",
    "parser_match_type",
    "parser_extracted",
    "expected",
    "language",
    "user_style",
    "system_style",
    "parse_strategy",
    "parse_confidence",
    "model_name",
)

# File-level meta columns (same value across every row of a file).
_FILE_META_COLUMNS: tuple[str, ...] = (
    "plugin",
    "annotated_by",
    "file_created_at",
    "file_updated_at",
)


def _dumps(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _loads(text: Any) -> list:
    if text is None:
        return []
    try:
        v = json.loads(text)
    except Exception:
        return []
    return v if isinstance(v, list) else []


class AnnotationStore:
    """SQLite-backed annotation persistence.

    ``__init__`` runs pending migrations so test harnesses don't have to.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        run_migrations(self._conn)

    # ── Public interface ──────────────────────────────────────────────────────

    def load_for_file(self, result_file_id: str) -> dict[str, Any] | None:
        """Return the full sidecar-shaped dict for a result file, or None."""
        rows = self._conn.execute(
            "SELECT * FROM annotations WHERE result_file_id = ? "
            "ORDER BY case_id, response_hash",
            (result_file_id,),
        ).fetchall()
        if not rows:
            return None

        cases: dict[str, Any] = {}
        annotated = 0
        for row in rows:
            case_record = _row_to_case_record(row)
            key = f"{row['case_id']}::{row['response_hash']}"
            cases[key] = case_record
            if _is_annotated(case_record):
                annotated += 1

        first = rows[0]
        meta = {
            "result_file": result_file_id,
            "plugin": first["plugin"],
            "annotated_by": first["annotated_by"],
            "created_at": first["file_created_at"],
            "updated_at": first["file_updated_at"],
            "annotated_count": annotated,
            "skipped_count": len(rows) - annotated,
        }
        return {"meta": meta, "cases": cases}

    def save_case(
        self,
        result_file_id: str,
        case_id: str,
        response_hash: str,
        case_record: dict[str, Any],
    ) -> None:
        """Upsert a single annotation row.

        ``case_record`` carries the sidecar case-record shape (top-level
        scalars + nested ``annotation`` dict). File-level meta values
        (``plugin`` / ``annotated_by`` / ``file_created_at`` /
        ``file_updated_at``) should be supplied via ``case_record["_meta"]``
        — they're applied to this row and to any existing rows for the same
        file so every row stays in sync with the latest file-level values.
        """
        _validate_key(result_file_id, case_id, response_hash)
        meta_updates = case_record.pop("_meta", None) or {}

        values = _case_record_to_values(
            result_file_id, case_id, response_hash, case_record, meta_updates
        )
        with transaction(self._conn):
            self._upsert_row(values)
            # Propagate file-level meta to every row for this file so the
            # ``_meta`` projection returned by ``load_for_file`` is coherent.
            if meta_updates:
                self._propagate_meta(result_file_id, meta_updates)

    def delete_file(self, result_file_id: str) -> int:
        """Remove every annotation row for a result file. Returns row count."""
        cur = self._conn.execute(
            "DELETE FROM annotations WHERE result_file_id = ?",
            (result_file_id,),
        )
        return cur.rowcount

    def delete_case(
        self, result_file_id: str, case_id: str, response_hash: str
    ) -> bool:
        """Remove a single annotation row. Returns True if a row was deleted.

        Resolves TD-095 — pre-v2.27 only the whole sidecar could be deleted.
        """
        _validate_key(result_file_id, case_id, response_hash)
        cur = self._conn.execute(
            "DELETE FROM annotations "
            "WHERE result_file_id = ? AND case_id = ? AND response_hash = ?",
            (result_file_id, case_id, response_hash),
        )
        return cur.rowcount > 0

    def list_annotated_result_files(self) -> set[str]:
        """Return the set of result_file_ids that have at least one annotation."""
        rows = self._conn.execute(
            "SELECT DISTINCT result_file_id FROM annotations"
        ).fetchall()
        return {r["result_file_id"] for r in rows}

    def has_annotations(self, result_file_id: str) -> bool:
        """True iff the given result file has at least one annotation row."""
        row = self._conn.execute(
            "SELECT 1 FROM annotations WHERE result_file_id = ? LIMIT 1",
            (result_file_id,),
        ).fetchone()
        return row is not None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _upsert_row(self, values: dict[str, Any]) -> None:
        cols = list(values.keys())
        placeholders = ",".join("?" for _ in cols)
        assignments = ",".join(
            f"{c}=excluded.{c}"
            for c in cols
            if c not in ("result_file_id", "case_id", "response_hash")
        )
        self._conn.execute(
            f"INSERT INTO annotations ({', '.join(cols)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(result_file_id, case_id, response_hash) "
            f"DO UPDATE SET {assignments}",
            tuple(values[c] for c in cols),
        )

    def _propagate_meta(
        self, result_file_id: str, meta_updates: dict[str, Any]
    ) -> None:
        """Apply file-level meta values to every row of this file."""
        applicable = {
            k: v for k, v in meta_updates.items() if k in _FILE_META_COLUMNS
        }
        if not applicable:
            return
        sets = ", ".join(f"{k} = ?" for k in applicable)
        self._conn.execute(
            f"UPDATE annotations SET {sets} WHERE result_file_id = ?",
            tuple(applicable.values()) + (result_file_id,),
        )


# ── Row ↔ case-record conversion ───────────────────────────────────────────────


def _scalarise(value: Any) -> Any:
    """Coerce a column value to something SQLite can bind.

    SQLite only accepts ``None`` / ``int`` / ``float`` / ``str`` / ``bytes``
    as parameter values. Plugins like ``picture_algebra`` / ``linda_fallacy``
    / ``misquote`` return ``dict`` / ``list`` for ``parsed_answer`` /
    ``expected``, which trip ``sqlite3.ProgrammingError: type 'dict' is not
    supported``. JSON-stringify those so the round-trip persists meaningful
    text. Booleans pass through (SQLite stores them as 0/1 ints natively).
    """
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


def _case_record_to_values(
    result_file_id: str,
    case_id: str,
    response_hash: str,
    case_record: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Flatten a sidecar case-record into a dict of column values."""
    ann = case_record.get("annotation") or {}

    values: dict[str, Any] = {
        "result_file_id": result_file_id,
        "case_id": case_id,
        "response_hash": response_hash,
    }

    for col in _CASE_CONTEXT_COLUMNS:
        values[col] = _scalarise(case_record.get(col))

    for col in _JSON_ARRAY_COLUMNS:
        if col == "context_windows":
            values[col] = _dumps(case_record.get("context_windows") or [])
        else:
            values[col] = _dumps(ann.get(col) or [])

    values["annotator_note"] = ann.get("annotator_note") or ""
    values["annotation_ts"] = ann.get("timestamp")

    for col in _FILE_META_COLUMNS:
        values[col] = meta.get(col)

    return values


def _row_to_case_record(row: sqlite3.Row) -> dict[str, Any]:
    """Reconstruct a sidecar case-record from a DB row."""
    annotation: dict[str, Any] = {}
    for col in _JSON_ARRAY_COLUMNS:
        if col == "context_windows":
            continue  # lives at the case level, not inside ``annotation``
        annotation[col] = _loads(row[col])
    annotation["annotator_note"] = row["annotator_note"] or ""
    if row["annotation_ts"]:
        annotation["timestamp"] = row["annotation_ts"]

    record: dict[str, Any] = {"case_id": row["case_id"]}
    for col in _CASE_CONTEXT_COLUMNS:
        record[col] = row[col]
    record["response_hash"] = row["response_hash"]
    record["context_windows"] = _loads(row["context_windows"])
    record["annotation"] = annotation
    return record


def _is_annotated(case_record: dict[str, Any]) -> bool:
    ann = case_record.get("annotation") or {}
    return bool(ann.get("spans")) or bool(ann.get("response_classes"))


def _validate_key(result_file_id: str, case_id: str, response_hash: str) -> None:
    for name, value in (
        ("result_file_id", result_file_id),
        ("case_id", case_id),
        ("response_hash", response_hash),
    ):
        if not value or not isinstance(value, str):
            raise ValueError(f"Invalid {name}: {value!r}")


# ── Module-level singleton (wired by app.py lifespan) ──────────────────────────

_store: AnnotationStore | None = None


def set_store(store: AnnotationStore | None) -> None:
    """Install the process-wide store. Called by ``src.web.app``."""
    global _store
    _store = store


def get_store() -> AnnotationStore:
    """Return the installed store; raise if ``set_store`` wasn't called.

    Consumers hold no reference of their own — they call this each time
    so tests can monkey-patch the singleton for isolated DB state.
    """
    if _store is None:
        raise RuntimeError(
            "AnnotationStore has not been initialized. "
            "src.web.app wires it at startup; tests must call set_store()."
        )
    return _store
