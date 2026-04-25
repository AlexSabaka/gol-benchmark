"""Tests for :class:`src.web.job_store.JobStore` (SQLite backend)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.web import crypto, db
from src.web.config import web_config
from src.web.job_store import JobStore
from src.web.job_store_migrator import migrate_json_jobs_to_db
from src.web.jobs import JOB_SCHEMA_VERSION, Job, JobState


@pytest.fixture
def isolated_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point web_config at a throwaway data root; clear crypto key cache."""
    monkeypatch.setattr(web_config, "data_root", str(tmp_path))
    monkeypatch.delenv("GOL_SECRET_KEY", raising=False)
    crypto.reset_cache()
    yield tmp_path
    crypto.reset_cache()


@pytest.fixture
def store(isolated_data: Path):
    conn = db.connect(isolated_data / "gol.db")
    try:
        yield JobStore(conn)
    finally:
        conn.close()


def _sample_job(**overrides) -> Job:
    defaults = dict(
        id="job-abc",
        model_name="gpt-4o-mini",
        testset_path="data/testsets/foo.json.gz",
        provider="openai_compatible",
        api_key="sk-abc123",
        api_base="https://api.example.com/v1",
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_empty_store_returns_empty_list(store: JobStore):
    assert store.load_all() == []


def test_save_and_load_roundtrip(store: JobStore):
    job = _sample_job()
    store.save_job(job.to_storable_dict())

    rows = store.load_all()
    assert len(rows) == 1
    restored = Job.from_stored_dict(rows[0])
    assert restored.id == job.id
    assert restored.model_name == job.model_name
    assert restored.api_key == job.api_key
    assert restored.api_base == job.api_base
    assert restored.state == JobState.PENDING


def test_save_job_upserts_on_duplicate_id(store: JobStore):
    job = _sample_job()
    store.save_job(job.to_storable_dict())

    job.state = JobState.COMPLETED
    job.progress_current = 99
    store.save_job(job.to_storable_dict())

    rows = store.load_all()
    assert len(rows) == 1
    assert rows[0]["state"] == "completed"
    assert rows[0]["progress_current"] == 99


def test_credentials_are_encrypted_at_rest(store: JobStore, isolated_data: Path):
    job = _sample_job()
    store.save_job(job.to_storable_dict())

    # Raw SQLite read — bypass the store so we see the stored ciphertext.
    raw_conn = db.connect(isolated_data / "gol.db")
    try:
        row = raw_conn.execute(
            "SELECT api_key_enc, api_base_enc FROM jobs WHERE id = ?", (job.id,)
        ).fetchone()
    finally:
        raw_conn.close()

    assert row["api_key_enc"] and "sk-abc123" not in row["api_key_enc"]
    assert row["api_base_enc"] and "api.example.com" not in row["api_base_enc"]


def test_save_all_prunes_missing_rows(store: JobStore):
    j1 = _sample_job(id="keep-1")
    j2 = _sample_job(id="keep-2", api_key="")
    j3 = _sample_job(id="drop-3", api_key="")
    for j in (j1, j2, j3):
        store.save_job(j.to_storable_dict())
    assert {r["id"] for r in store.load_all()} == {"keep-1", "keep-2", "drop-3"}

    store.save_all([j1.to_storable_dict(), j2.to_storable_dict()])
    assert {r["id"] for r in store.load_all()} == {"keep-1", "keep-2"}


def test_save_all_with_empty_list_clears_table(store: JobStore):
    store.save_job(_sample_job().to_storable_dict())
    store.save_all([])
    assert store.load_all() == []


def test_delete_job_removes_single_row(store: JobStore):
    j1 = _sample_job(id="a")
    j2 = _sample_job(id="b", api_key="")
    store.save_job(j1.to_storable_dict())
    store.save_job(j2.to_storable_dict())

    store.delete_job("a")
    ids = {r["id"] for r in store.load_all()}
    assert ids == {"b"}


def test_delete_job_missing_id_is_noop(store: JobStore):
    store.save_job(_sample_job().to_storable_dict())
    store.delete_job("does-not-exist")
    assert len(store.load_all()) == 1


def test_load_all_ordered_by_created_at(store: JobStore):
    for i, jid in enumerate(["c", "a", "b"]):
        j = _sample_job(id=jid, api_key="", created_at=float(i))
        store.save_job(j.to_storable_dict())
    ids = [r["id"] for r in store.load_all()]
    assert ids == ["c", "a", "b"]  # created_at 0,1,2 order


def test_booleans_roundtrip_as_python_bools(store: JobStore):
    job = _sample_job(no_think=False, hidden=True, api_key="")
    store.save_job(job.to_storable_dict())
    row = store.load_all()[0]
    assert row["no_think"] is False
    assert row["hidden"] is True


def test_save_job_rejects_missing_id(store: JobStore):
    with pytest.raises(ValueError):
        store.save_job({"model_name": "x"})


def test_schema_version_recorded_after_construction(isolated_data: Path):
    conn = db.connect(isolated_data / "gol.db")
    try:
        JobStore(conn)
        v = db.current_version(conn)
        assert v >= 1
    finally:
        conn.close()


# ── Migrator: file → SQLite ────────────────────────────────────────────────────

def test_migrator_moves_legacy_json_to_db_and_backup(
    isolated_data: Path, store: JobStore
):
    jobs_dir = isolated_data / "jobs"
    backup_dir = isolated_data / "jobs.bak"
    jobs_dir.mkdir()

    # Legacy v1 record — plaintext credentials, no schema_version.
    legacy = {
        "id": "legacy-1",
        "model_name": "gpt-4o",
        "testset_path": "data/testsets/foo.json.gz",
        "state": "paused",
        "created_at": 1700000000.0,
        "paused_at_index": 5,
        "api_key": "sk-legacy-plain",
        "api_base": "https://legacy.example.com/v1",
    }
    (jobs_dir / "legacy-1.json").write_text(json.dumps(legacy))

    # v2 record — already encrypted envelope.
    v2_job = _sample_job(id="v2-2")
    (jobs_dir / "v2-2.json").write_text(json.dumps(v2_job.to_storable_dict()))

    migrated = migrate_json_jobs_to_db(store, jobs_dir, backup_dir)
    assert migrated == 2

    rows = {r["id"]: r for r in store.load_all()}
    assert set(rows) == {"legacy-1", "v2-2"}

    # Legacy record upgraded to v2 on the way in
    restored_legacy = Job.from_stored_dict(rows["legacy-1"])
    assert restored_legacy.api_key == "sk-legacy-plain"
    assert rows["legacy-1"]["schema_version"] == JOB_SCHEMA_VERSION

    # Originals moved aside
    assert not (jobs_dir / "legacy-1.json").exists()
    assert (backup_dir / "legacy-1.json").exists()
    assert (backup_dir / "v2-2.json").exists()


def test_migrator_skips_subdirectories(isolated_data: Path, store: JobStore):
    jobs_dir = isolated_data / "jobs"
    (jobs_dir / "partial").mkdir(parents=True)
    # Partial checkpoint — not a job record, must not be ingested.
    (jobs_dir / "partial" / "some.json").write_text("{}")

    migrated = migrate_json_jobs_to_db(
        store, jobs_dir, isolated_data / "jobs.bak"
    )
    assert migrated == 0
    assert store.load_all() == []
    # Partial file must stay put
    assert (jobs_dir / "partial" / "some.json").exists()


def test_migrator_is_idempotent_on_second_run(
    isolated_data: Path, store: JobStore
):
    jobs_dir = isolated_data / "jobs"
    jobs_dir.mkdir()
    job = _sample_job()
    (jobs_dir / f"{job.id}.json").write_text(json.dumps(job.to_storable_dict()))

    first = migrate_json_jobs_to_db(store, jobs_dir, isolated_data / "jobs.bak")
    second = migrate_json_jobs_to_db(store, jobs_dir, isolated_data / "jobs.bak")
    assert first == 1
    assert second == 0  # files already moved
    assert len(store.load_all()) == 1


def test_migrator_handles_missing_jobs_dir(
    isolated_data: Path, store: JobStore
):
    migrated = migrate_json_jobs_to_db(
        store, isolated_data / "nope", isolated_data / "jobs.bak"
    )
    assert migrated == 0


def test_migrator_skips_malformed_json(isolated_data: Path, store: JobStore):
    jobs_dir = isolated_data / "jobs"
    jobs_dir.mkdir()
    (jobs_dir / "good.json").write_text(
        json.dumps(_sample_job(id="good").to_storable_dict())
    )
    (jobs_dir / "bad.json").write_text("not json at all {")

    migrated = migrate_json_jobs_to_db(
        store, jobs_dir, isolated_data / "jobs.bak"
    )
    assert migrated == 1
    assert {r["id"] for r in store.load_all()} == {"good"}
    # Malformed file left alone, good file moved
    assert (jobs_dir / "bad.json").exists()
    assert not (jobs_dir / "good.json").exists()
