"""One-shot migration from annotation sidecar files to SQLite.

Scans ``web_config.annotations_dir`` for ``*.json.gz`` sidecars, inserts each
case into the DB via :class:`AnnotationStore`, and moves the originals to
``data/annotations.bak/`` for rollback.

TD-096 rehash: the new ``_response_hash`` uses SHA256/16 hex chars instead of
MD5/8 hex. Legacy sidecar keys are MD5-hashed so a straight copy would
desync from the runtime hasher. For each legacy entry the migrator loads the
corresponding result file, matches the case by (test_id, legacy MD5 hash),
and inserts under the new SHA256 hash. Entries whose source result file is
missing fall back to the legacy hash — they act as opaque identifiers and
will be invisible to the new runtime (no new hash will match them), but
they're preserved rather than lost.

Idempotent: once moved, source files are gone and second-run is a no-op.
"""
from __future__ import annotations

import gzip
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from src.web.annotation_store import AnnotationStore

logger = logging.getLogger(__name__)


def migrate_sidecar_files_to_db(
    store: AnnotationStore,
    annotations_dir: Path | str,
    backup_dir: Path | str,
    results_lookup=None,
) -> int:
    """Migrate all sidecar files into the DB; return number of files migrated.

    ``results_lookup`` is an optional callable ``(result_filename) -> Path |
    None`` used to locate the source result file for rehashing. When None
    the migrator keeps the legacy hash for every entry (tests can pass a
    stub; production wires in ``src.web.api.analysis._find_result_file``).
    """
    # Deferred imports to keep the store tests (which hit this module) from
    # pulling in FastAPI / the full analysis stack.
    from src.web.api.human_review import (
        _migrate_annotation,
        _response_hash,
        _response_hash_legacy,
    )

    annotations_path = Path(annotations_dir)
    backup_path = Path(backup_dir)
    if not annotations_path.exists():
        return 0

    candidates = [p for p in annotations_path.glob("*.json.gz") if p.is_file()]
    if not candidates:
        return 0

    backup_path.mkdir(parents=True, exist_ok=True)
    migrated_files = 0
    for src in candidates:
        try:
            with gzip.open(str(src), "rt", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            logger.warning("Skipping unreadable annotation file %s: %s", src, exc)
            continue

        result_file_id = (payload.get("meta") or {}).get("result_file") or _strip_gz(src.name)
        cases = payload.get("cases") or {}
        if not cases:
            # Empty sidecar — move aside and skip.
            _move_to_backup(src, backup_path)
            migrated_files += 1
            continue

        # Load the source result file once per sidecar so we can rehash.
        raw_responses_by_test_id = _load_raw_responses(result_file_id, results_lookup)

        meta = payload.get("meta") or {}
        file_meta = {
            "plugin": meta.get("plugin"),
            "annotated_by": meta.get("annotated_by") or "human",
            "file_created_at": meta.get("created_at"),
            "file_updated_at": meta.get("updated_at") or meta.get("created_at"),
        }

        for _, case_record in cases.items():
            try:
                _migrate_one_case(
                    store,
                    result_file_id,
                    case_record,
                    file_meta,
                    raw_responses_by_test_id,
                    _response_hash,
                    _response_hash_legacy,
                    _migrate_annotation,
                )
            except Exception as exc:
                logger.warning(
                    "Could not migrate case in %s: %s", src.name, exc
                )
                continue

        _move_to_backup(src, backup_path)
        migrated_files += 1

    if migrated_files:
        logger.info(
            "Migrated %d annotation sidecar(s) from %s → SQLite "
            "(originals moved to %s)",
            migrated_files,
            annotations_path,
            backup_path,
        )
    return migrated_files


def _migrate_one_case(
    store: AnnotationStore,
    result_file_id: str,
    case_record: dict[str, Any],
    file_meta: dict[str, Any],
    raw_responses_by_test_id: dict[str, list[str]],
    new_hasher,
    legacy_hasher,
    annotation_normalizer,
) -> None:
    case_id = case_record.get("case_id")
    if not case_id:
        return

    legacy_hash = case_record.get("response_hash")

    # Rehash when we can match a source response. Otherwise keep the legacy
    # hash so the row isn't lost (it acts as an opaque identifier; runtime
    # hashes won't resolve to it, so the annotation simply becomes invisible
    # if the source response changed).
    new_hash = None
    if legacy_hash and case_id in raw_responses_by_test_id:
        for raw in raw_responses_by_test_id[case_id]:
            if legacy_hasher(raw) == legacy_hash:
                new_hash = new_hasher(raw)
                break

    effective_hash = new_hash or legacy_hash or new_hasher(
        "\n".join(raw_responses_by_test_id.get(case_id, []))
    )
    if not effective_hash:
        return

    # Normalize v1/v2 annotation dicts → v3 on the way in.
    annotation = case_record.get("annotation")
    if isinstance(annotation, dict):
        case_record["annotation"] = annotation_normalizer(annotation)

    # Pass meta through the ``_meta`` envelope so ``save_case`` can propagate
    # file-level values to every row.
    enriched = dict(case_record)
    enriched["_meta"] = file_meta
    store.save_case(result_file_id, case_id, effective_hash, enriched)


def _load_raw_responses(
    result_file_id: str, results_lookup
) -> dict[str, list[str]]:
    """Return ``{test_id: [raw_response, ...]}`` from the matching result file.

    A single test_id may appear multiple times (different languages /
    styles) — we keep all responses so the legacy-hash match can find the
    right variant.
    """
    if results_lookup is None:
        return {}
    try:
        fp = results_lookup(result_file_id)
    except Exception:
        fp = None
    if fp is None or not Path(fp).exists():
        return {}
    try:
        with gzip.open(str(fp), "rt", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        logger.warning(
            "Could not load source result for rehash (%s): %s", result_file_id, exc
        )
        return {}

    by_test_id: dict[str, list[str]] = {}
    for r in data.get("results") or []:
        tid = r.get("test_id")
        if not tid:
            continue
        raw = (r.get("output") or {}).get("raw_response") or ""
        by_test_id.setdefault(tid, []).append(raw)
    return by_test_id


def _move_to_backup(src: Path, backup_path: Path) -> None:
    try:
        shutil.move(str(src), str(backup_path / src.name))
    except Exception as exc:
        logger.warning(
            "Migrated %s but could not move to backup: %s", src, exc
        )


def _strip_gz(name: str) -> str:
    if name.endswith(".json.gz"):
        return name[: -len(".json.gz")]
    if name.endswith(".json"):
        return name[: -len(".json")]
    return Path(name).stem
