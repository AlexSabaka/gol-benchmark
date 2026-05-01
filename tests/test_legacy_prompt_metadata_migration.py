"""Tests for ``scripts/migrate_legacy_prompt_metadata.py``.

The script is invoked as a module (its public API is :func:`migrate_file`
and :func:`migrate_directory`) so we can drive it directly from pytest.
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Load the script as a module — it lives under scripts/ outside any package.
# Register in sys.modules BEFORE exec so the @dataclass decorator can resolve
# the module via cls.__module__ during class construction.
_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "migrate_legacy_prompt_metadata.py"
)
_MODULE_NAME = "migrate_legacy_prompt_metadata"
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, str(_SCRIPT))
assert _spec is not None and _spec.loader is not None
migrator = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = migrator
_spec.loader.exec_module(migrator)


def _write_gz(path: Path, payload: dict) -> None:
    with gzip.open(str(path), "wt", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def _read_gz(path: Path) -> dict:
    with gzip.open(str(path), "rt", encoding="utf-8") as f:
        return json.load(f)


def _legacy_payload() -> dict:
    return {
        "metadata": {"version": "1.0"},
        "results": [
            {
                "test_id": "case_1",
                "input": {
                    "prompt_metadata": {
                        "user_style": "minimal",
                        "system_style": "analytical",
                        "language": "en",
                    },
                    "system_prompt": "You are an expert...",
                    "user_prompt": "Solve...",
                },
                "output": {"raw_response": "drive"},
            },
            {
                "test_id": "case_2",
                "input": {
                    "prompt_metadata": {
                        "user_style": "casual",
                        "system_style": "casual",
                        "language": "es",
                    },
                    "system_prompt": "Eres...",
                    "user_prompt": "Solve...",
                },
                "output": {"raw_response": "walk"},
            },
        ],
    }


def test_migrate_adds_prompt_id_and_version(tmp_path: Path):
    f = tmp_path / "legacy.json.gz"
    _write_gz(f, _legacy_payload())

    stats = migrator.migrate_file(f, dry_run=False)
    assert stats.entries_seen == 2
    assert stats.entries_migrated == 2
    assert stats.skipped_no_system_style == 0
    assert stats.error is None

    out = _read_gz(f)
    pm0 = out["results"][0]["input"]["prompt_metadata"]
    pm1 = out["results"][1]["input"]["prompt_metadata"]
    assert pm0["prompt_id"] == "builtin_analytical"
    assert pm0["prompt_version"] == 1
    assert pm1["prompt_id"] == "builtin_casual"
    assert pm1["prompt_version"] == 1
    # Original system_style preserved
    assert pm0["system_style"] == "analytical"
    assert pm1["system_style"] == "casual"


def test_migration_is_idempotent(tmp_path: Path):
    f = tmp_path / "legacy.json.gz"
    _write_gz(f, _legacy_payload())
    migrator.migrate_file(f, dry_run=False)
    second = migrator.migrate_file(f, dry_run=False)
    # Both entries already carry prompt_id → migrated count is zero.
    assert second.entries_migrated == 0
    assert second.entries_seen == 2


def test_dry_run_does_not_write(tmp_path: Path):
    f = tmp_path / "legacy.json.gz"
    payload = _legacy_payload()
    _write_gz(f, payload)
    before = _read_gz(f)

    stats = migrator.migrate_file(f, dry_run=True)
    assert stats.entries_migrated == 2  # would migrate 2

    after = _read_gz(f)
    # No mutation occurred on disk
    for r in after["results"]:
        assert "prompt_id" not in r["input"]["prompt_metadata"]
    assert before == after


def test_mixed_legacy_and_migrated_entries(tmp_path: Path):
    payload = _legacy_payload()
    # Pre-mark first entry as already migrated.
    payload["results"][0]["input"]["prompt_metadata"]["prompt_id"] = (
        "builtin_analytical"
    )
    payload["results"][0]["input"]["prompt_metadata"]["prompt_version"] = 1
    f = tmp_path / "mixed.json.gz"
    _write_gz(f, payload)

    stats = migrator.migrate_file(f, dry_run=False)
    assert stats.entries_seen == 2
    assert stats.entries_migrated == 1  # only the second one

    out = _read_gz(f)
    assert out["results"][1]["input"]["prompt_metadata"]["prompt_id"] == (
        "builtin_casual"
    )


def test_skips_entries_without_system_style(tmp_path: Path):
    payload = {
        "results": [
            {
                "input": {"prompt_metadata": {"language": "en"}},
            },
            {
                "input": {
                    "prompt_metadata": {"system_style": "analytical"},
                },
            },
        ]
    }
    f = tmp_path / "weird.json.gz"
    _write_gz(f, payload)

    stats = migrator.migrate_file(f, dry_run=False)
    assert stats.entries_seen == 2
    assert stats.entries_migrated == 1
    assert stats.skipped_no_system_style == 1

    out = _read_gz(f)
    assert "prompt_id" not in out["results"][0]["input"]["prompt_metadata"]
    assert (
        out["results"][1]["input"]["prompt_metadata"]["prompt_id"]
        == "builtin_analytical"
    )


def test_directory_walk(tmp_path: Path):
    sub = tmp_path / "nested"
    sub.mkdir()
    _write_gz(tmp_path / "a.json.gz", _legacy_payload())
    _write_gz(sub / "b.json.gz", _legacy_payload())
    # Non-gz file should be ignored.
    (tmp_path / "ignore.txt").write_text("nope")

    all_stats = migrator.migrate_directory(tmp_path, dry_run=False)
    assert len(all_stats) == 2
    total_migrated = sum(s.entries_migrated for s in all_stats)
    assert total_migrated == 4
