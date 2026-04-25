"""Tests for :class:`src.web.annotation_store.AnnotationStore` and migrator."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from src.web import db
from src.web.annotation_store import AnnotationStore
from src.web.annotation_store_migrator import migrate_sidecar_files_to_db


@pytest.fixture
def store(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    try:
        yield AnnotationStore(conn)
    finally:
        conn.close()


def _case_record(
    case_id: str = "case_a",
    *,
    spans: list | None = None,
    response_classes: list | None = None,
    **overrides,
) -> dict:
    record = {
        "case_id": case_id,
        "response_length": 42,
        "response_hash": "deadbeefcafe1234",
        "parser_match_type": "parse_error",
        "parser_extracted": None,
        "expected": "drive",
        "language": "en",
        "user_style": "casual",
        "system_style": "analytical",
        "parse_strategy": "unknown",
        "parse_confidence": None,
        "model_name": "test-model",
        "context_windows": [],
        "annotation": {
            "spans": spans if spans is not None else [],
            "response_classes": response_classes if response_classes is not None else [],
            "context_anchors": [],
            "answer_keywords": [],
            "negative_spans": [],
            "negative_keywords": [],
            "annotator_note": "",
            "timestamp": "2026-04-22T10:00:00Z",
        },
        "_meta": {
            "plugin": "carwash",
            "annotated_by": "human",
            "file_created_at": "2026-04-22T09:00:00Z",
            "file_updated_at": "2026-04-22T10:00:00Z",
        },
    }
    record.update(overrides)
    return record


def test_load_missing_file_returns_none(store: AnnotationStore):
    assert store.load_for_file("no-such-file") is None


def test_save_and_load_roundtrip(store: AnnotationStore):
    record = _case_record(
        spans=[
            {
                "text": "drive",
                "char_start": 10,
                "char_end": 15,
                "position": "end",
                "format": "plain",
            }
        ],
        response_classes=["hedge"],
    )
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", record)

    payload = store.load_for_file("rf.json.gz")
    assert payload is not None
    assert payload["meta"]["plugin"] == "carwash"
    assert payload["meta"]["annotated_count"] == 1
    assert payload["meta"]["skipped_count"] == 0
    assert payload["meta"]["result_file"] == "rf.json.gz"

    key = "case_a::deadbeefcafe1234"
    assert key in payload["cases"]
    case = payload["cases"][key]
    assert case["language"] == "en"
    assert case["annotation"]["spans"][0]["text"] == "drive"
    assert case["annotation"]["response_classes"] == ["hedge"]


def test_meta_counters_split_annotated_vs_skipped(store: AnnotationStore):
    annotated = _case_record(
        "case_a",
        spans=[{"text": "x", "char_start": 0, "char_end": 1, "position": "end", "format": "plain"}],
    )
    skipped = _case_record("case_b")  # no spans, no classes — "skipped"
    skipped["response_hash"] = "aaaaaaaaaaaaaaaa"
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", annotated)
    store.save_case("rf.json.gz", "case_b", "aaaaaaaaaaaaaaaa", skipped)

    payload = store.load_for_file("rf.json.gz")
    assert payload["meta"]["annotated_count"] == 1
    assert payload["meta"]["skipped_count"] == 1


def test_save_case_upserts(store: AnnotationStore):
    record = _case_record(response_classes=["hedge"])
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", record)

    record2 = _case_record(response_classes=["refusal"])
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", record2)

    payload = store.load_for_file("rf.json.gz")
    case = payload["cases"]["case_a::deadbeefcafe1234"]
    assert case["annotation"]["response_classes"] == ["refusal"]
    # Only one row — upserted in place.
    assert len(payload["cases"]) == 1


def test_delete_case_removes_one_row_leaves_others(store: AnnotationStore):
    a = _case_record("case_a", response_classes=["hedge"])
    b = _case_record("case_b", response_classes=["refusal"])
    b["response_hash"] = "bbbbbbbbbbbbbbbb"
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", a)
    store.save_case("rf.json.gz", "case_b", "bbbbbbbbbbbbbbbb", b)

    assert store.delete_case("rf.json.gz", "case_a", "deadbeefcafe1234") is True

    payload = store.load_for_file("rf.json.gz")
    assert set(payload["cases"]) == {"case_b::bbbbbbbbbbbbbbbb"}


def test_delete_case_missing_returns_false(store: AnnotationStore):
    assert store.delete_case("rf.json.gz", "case_z", "zzzzzzzzzzzzzzzz") is False


def test_delete_file_wipes_all_rows(store: AnnotationStore):
    a = _case_record("case_a", response_classes=["hedge"])
    b = _case_record("case_b", response_classes=["refusal"])
    b["response_hash"] = "bbbbbbbbbbbbbbbb"
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", a)
    store.save_case("rf.json.gz", "case_b", "bbbbbbbbbbbbbbbb", b)

    removed = store.delete_file("rf.json.gz")
    assert removed == 2
    assert store.load_for_file("rf.json.gz") is None


def test_list_annotated_result_files(store: AnnotationStore):
    store.save_case(
        "rf1.json.gz", "case_a", "deadbeefcafe1234",
        _case_record(response_classes=["hedge"]),
    )
    store.save_case(
        "rf2.json.gz", "case_a", "deadbeefcafe1234",
        _case_record(response_classes=["hedge"]),
    )
    assert store.list_annotated_result_files() == {"rf1.json.gz", "rf2.json.gz"}


def test_has_annotations(store: AnnotationStore):
    assert store.has_annotations("rf.json.gz") is False
    store.save_case(
        "rf.json.gz", "case_a", "deadbeefcafe1234",
        _case_record(response_classes=["hedge"]),
    )
    assert store.has_annotations("rf.json.gz") is True


def test_save_handles_dict_expected_value(store: AnnotationStore):
    """Picture-algebra / linda_fallacy / misquote return dict / list for
    `expected` and `parser_extracted`. SQLite can't bind those directly;
    `_scalarise` JSON-stringifies them so the save succeeds."""
    record = _case_record(
        spans=[],
        response_classes=["hedge"],
        expected={"x": 5, "y": 10, "z": 15},
        parser_extracted=["walk", "drive", "fly"],
    )
    # Must not raise sqlite3.ProgrammingError.
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", record)

    payload = store.load_for_file("rf.json.gz")
    case = payload["cases"]["case_a::deadbeefcafe1234"]
    # Round-trip: dict comes back as a JSON string. Consumers (aggregator,
    # frontend) treat `expected` as `unknown` so this is correct.
    assert isinstance(case["expected"], str)
    assert "x" in case["expected"] and "5" in case["expected"]
    assert isinstance(case["parser_extracted"], str)
    assert "walk" in case["parser_extracted"]


def test_save_rejects_invalid_keys(store: AnnotationStore):
    record = _case_record()
    with pytest.raises(ValueError):
        store.save_case("", "case_a", "deadbeefcafe1234", record)
    with pytest.raises(ValueError):
        store.save_case("rf.json.gz", "", "deadbeefcafe1234", record)
    with pytest.raises(ValueError):
        store.save_case("rf.json.gz", "case_a", "", record)


def test_meta_propagates_to_existing_rows(store: AnnotationStore):
    """File-level meta on the second save overwrites rows from the first save."""
    first = _case_record("case_a", response_classes=["hedge"])
    store.save_case("rf.json.gz", "case_a", "deadbeefcafe1234", first)

    second = _case_record("case_b", response_classes=["refusal"])
    second["response_hash"] = "bbbbbbbbbbbbbbbb"
    second["_meta"]["file_updated_at"] = "2026-04-23T10:00:00Z"
    store.save_case("rf.json.gz", "case_b", "bbbbbbbbbbbbbbbb", second)

    payload = store.load_for_file("rf.json.gz")
    assert payload["meta"]["updated_at"] == "2026-04-23T10:00:00Z"


# ── Migrator tests ─────────────────────────────────────────────────────────────


def _write_sidecar(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(str(path), "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)


def _write_result_file(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "model_info": {"model_name": "test-model", "provider": "ollama"},
        "results": entries,
    }
    with gzip.open(str(path), "wt", encoding="utf-8") as fh:
        json.dump(data, fh)


def test_migrator_handles_empty_dir(store: AnnotationStore, tmp_path: Path):
    migrated = migrate_sidecar_files_to_db(
        store, tmp_path / "annotations", tmp_path / "annotations.bak"
    )
    assert migrated == 0


def test_migrator_rehashes_to_sha256_when_source_available(
    store: AnnotationStore, tmp_path: Path
):
    """Legacy MD5 hash is replaced with SHA256/16-hex prefix after rehash."""
    from src.web.api.human_review import _response_hash, _response_hash_legacy

    # One real response; compute its legacy (MD5) and new (SHA256) hashes.
    raw_response = "After some thought, you should drive."
    legacy_hash = _response_hash_legacy(raw_response)
    new_hash = _response_hash(raw_response)
    assert legacy_hash != new_hash
    assert len(legacy_hash) == 8 and len(new_hash) == 16

    # Write a sidecar that carries the legacy hash.
    sidecar = {
        "meta": {
            "result_file": "rf.json.gz",
            "plugin": "carwash",
            "annotated_by": "human",
            "created_at": "2026-04-22T09:00:00Z",
            "updated_at": "2026-04-22T10:00:00Z",
        },
        "cases": {
            f"case_a::{legacy_hash}": {
                "case_id": "case_a",
                "response_hash": legacy_hash,
                "response_length": len(raw_response),
                "annotation": {
                    "spans": [],
                    "response_classes": ["hedge"],
                    "annotator_note": "",
                    "timestamp": "2026-04-22T10:00:00Z",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    backup_dir = tmp_path / "annotations.bak"
    result_dir = tmp_path / "results"

    _write_sidecar(annot_dir / "rf.json.gz", sidecar)
    _write_result_file(
        result_dir / "rf.json.gz",
        [{"test_id": "case_a", "output": {"raw_response": raw_response}}],
    )

    def locate(name: str) -> Path | None:
        fp = result_dir / name
        return fp if fp.exists() else None

    migrated = migrate_sidecar_files_to_db(store, annot_dir, backup_dir, locate)
    assert migrated == 1

    payload = store.load_for_file("rf.json.gz")
    # Row stored under the NEW hash; legacy hash is gone.
    assert any(k.endswith(f"::{new_hash}") for k in payload["cases"])
    assert not any(k.endswith(f"::{legacy_hash}") for k in payload["cases"])

    # Sidecar moved to backup.
    assert (backup_dir / "rf.json.gz").exists()
    assert not (annot_dir / "rf.json.gz").exists()


def test_migrator_preserves_legacy_hash_when_source_missing(
    store: AnnotationStore, tmp_path: Path
):
    """No source result file → fall back to legacy hash as opaque id."""
    from src.web.api.human_review import _response_hash_legacy

    legacy_hash = _response_hash_legacy("some response")
    sidecar = {
        "meta": {"result_file": "gone.json.gz", "plugin": "carwash"},
        "cases": {
            f"case_a::{legacy_hash}": {
                "case_id": "case_a",
                "response_hash": legacy_hash,
                "annotation": {
                    "spans": [],
                    "response_classes": ["hedge"],
                    "annotator_note": "",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    _write_sidecar(annot_dir / "gone.json.gz", sidecar)

    migrated = migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    assert migrated == 1

    payload = store.load_for_file("gone.json.gz")
    # Row kept under the old hash (it's opaque; runtime SHA256 won't match).
    assert any(k.endswith(f"::{legacy_hash}") for k in payload["cases"])


def test_migrator_normalizes_v1_response_class_scalar(
    store: AnnotationStore, tmp_path: Path
):
    """Old sidecars with scalar ``response_class`` migrate to array shape."""
    sidecar = {
        "meta": {"result_file": "rf.json.gz", "plugin": "carwash"},
        "cases": {
            "case_a::aaaaaaaa": {
                "case_id": "case_a",
                "response_hash": "aaaaaaaa",
                "annotation": {
                    "spans": [],
                    "response_class": "hedge",  # v1 scalar shape
                    "annotator_note": "",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    _write_sidecar(annot_dir / "rf.json.gz", sidecar)

    migrated = migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    assert migrated == 1

    payload = store.load_for_file("rf.json.gz")
    case = next(iter(payload["cases"].values()))
    # Scalar → array migration; hedge is a canonical v4 class so it survives.
    assert case["annotation"]["response_classes"] == ["hedge"]


def test_migrator_drops_verbose_correct_class(
    store: AnnotationStore, tmp_path: Path
):
    """v4: `verbose_correct` / `verbose` are dropped entirely — Extractable
    is implicit when a span exists."""
    sidecar = {
        "meta": {"result_file": "rf.json.gz", "plugin": "carwash"},
        "cases": {
            "case_a::aaaaaaaa": {
                "case_id": "case_a",
                "response_hash": "aaaaaaaa",
                "annotation": {
                    "spans": [],
                    "response_class": "verbose_correct",  # v1 code, dropped in v4
                    "annotator_note": "",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    _write_sidecar(annot_dir / "rf.json.gz", sidecar)

    migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    payload = store.load_for_file("rf.json.gz")
    case = next(iter(payload["cases"].values()))
    # verbose_correct lands in _CLASS_DROP, producing an empty list.
    assert case["annotation"]["response_classes"] == []


@pytest.mark.parametrize("legacy_code", ["gibberish", "refusal", "language_error"])
def test_migrator_folds_model_failure_codes_to_unrecoverable(
    store: AnnotationStore, tmp_path: Path, legacy_code: str
):
    """v4: gibberish / refusal / language_error all collapse to unrecoverable."""
    sidecar = {
        "meta": {"result_file": f"rf_{legacy_code}.json.gz", "plugin": "carwash"},
        "cases": {
            "case_a::aaaaaaaa": {
                "case_id": "case_a",
                "response_hash": "aaaaaaaa",
                "annotation": {
                    "spans": [],
                    "response_classes": [legacy_code],
                    "annotator_note": "",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    _write_sidecar(annot_dir / f"rf_{legacy_code}.json.gz", sidecar)

    migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    payload = store.load_for_file(f"rf_{legacy_code}.json.gz")
    case = next(iter(payload["cases"].values()))
    assert case["annotation"]["response_classes"] == ["unrecoverable"]


def test_migrator_dedupes_collapsed_unrecoverable(
    store: AnnotationStore, tmp_path: Path
):
    """Two legacy codes that both fold to `unrecoverable` produce a single entry."""
    sidecar = {
        "meta": {"result_file": "rf.json.gz", "plugin": "carwash"},
        "cases": {
            "case_a::aaaaaaaa": {
                "case_id": "case_a",
                "response_hash": "aaaaaaaa",
                "annotation": {
                    "spans": [],
                    "response_classes": ["gibberish", "refusal"],
                    "annotator_note": "",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    _write_sidecar(annot_dir / "rf.json.gz", sidecar)

    migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    payload = store.load_for_file("rf.json.gz")
    case = next(iter(payload["cases"].values()))
    assert case["annotation"]["response_classes"] == ["unrecoverable"]


def test_migrator_folds_negative_keywords_into_negative_spans(
    store: AnnotationStore, tmp_path: Path
):
    """v4: the distinction between negative_spans and negative_keywords is gone.
    Legacy `negative_keywords` entries are appended to `negative_spans` on read."""
    sidecar = {
        "meta": {"result_file": "rf.json.gz", "plugin": "carwash"},
        "cases": {
            "case_a::aaaaaaaa": {
                "case_id": "case_a",
                "response_hash": "aaaaaaaa",
                "annotation": {
                    "spans": [],
                    "response_classes": ["hedge"],
                    "negative_spans": [
                        {"text": "drive", "char_start": 0, "char_end": 5},
                    ],
                    "negative_keywords": [
                        {"text": "or walk", "char_start": 6, "char_end": 13},
                    ],
                    "annotator_note": "",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    _write_sidecar(annot_dir / "rf.json.gz", sidecar)

    migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    payload = store.load_for_file("rf.json.gz")
    case = next(iter(payload["cases"].values()))
    ann = case["annotation"]
    # Both entries now live in negative_spans; negative_keywords is empty.
    assert {s["text"] for s in ann["negative_spans"]} == {"drive", "or walk"}
    assert ann["negative_keywords"] == []


def test_migrator_is_idempotent(store: AnnotationStore, tmp_path: Path):
    sidecar = {
        "meta": {"result_file": "rf.json.gz", "plugin": "carwash"},
        "cases": {
            "case_a::aaaaaaaa": {
                "case_id": "case_a",
                "response_hash": "aaaaaaaa",
                "annotation": {
                    "spans": [],
                    "response_classes": ["hedge"],
                    "annotator_note": "",
                },
            }
        },
    }
    annot_dir = tmp_path / "annotations"
    _write_sidecar(annot_dir / "rf.json.gz", sidecar)

    first = migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    second = migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    assert first == 1
    assert second == 0  # files already moved


def test_migrator_skips_malformed_gzip(store: AnnotationStore, tmp_path: Path):
    annot_dir = tmp_path / "annotations"
    annot_dir.mkdir()
    (annot_dir / "bad.json.gz").write_text("not gzip at all")

    migrated = migrate_sidecar_files_to_db(
        store, annot_dir, tmp_path / "annotations.bak", lambda _: None
    )
    assert migrated == 0
    # Malformed file untouched.
    assert (annot_dir / "bad.json.gz").exists()
