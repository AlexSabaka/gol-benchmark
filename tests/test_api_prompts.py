"""Tests for the /api/prompts CRUD router.

Uses ``TestClient`` as a context manager so FastAPI's lifespan runs — the
lifespan wires the singleton ``PromptStore`` from the live SQLite DB.
``GOL_DATA_ROOT`` is sandboxed to a tempdir by ``tests/conftest.py`` so we
don't pollute the real ``data/`` directory.

The TestClient is opened with ``__enter__`` but never closed — matches the
pattern in ``tests/test_human_review.py`` so that running the full test
module set doesn't tear down lifespan singletons mid-run.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.web import prompt_store as prompt_store_module
from src.web.app import app

_client_ctx = TestClient(app)
_client_ctx.__enter__()
client = _client_ctx


@pytest.fixture(autouse=True)
def _wipe_user_prompts():
    """Each test starts from "builtins only" — drop user-authored rows."""
    try:
        store = prompt_store_module.get_store()
    except RuntimeError:
        return
    store._conn.execute("DELETE FROM prompt_versions WHERE prompt_id LIKE 'usr_%'")
    store._conn.execute("DELETE FROM prompts WHERE is_builtin = 0")


# ── Listing ──────────────────────────────────────────────────────────────────


def test_list_returns_seeded_builtins():
    response = client.get("/api/prompts")
    assert response.status_code == 200
    body = response.json()
    ids = {p["id"] for p in body}
    assert {
        "builtin_analytical", "builtin_casual",
        "builtin_adversarial", "builtin_none",
    }.issubset(ids)
    for p in body:
        assert p["latest_version"] == 1


# ── Create + read ────────────────────────────────────────────────────────────


def test_create_and_get():
    create = client.post(
        "/api/prompts",
        json={
            "name": "Test Prompt",
            "description": "for tests",
            "content": {"en": "be helpful"},
            "tags": ["t"],
        },
    )
    assert create.status_code == 201
    pid = create.json()["prompt_id"]
    assert pid.startswith("usr_")

    detail = client.get(f"/api/prompts/{pid}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["name"] == "Test Prompt"
    assert body["content"]["en"] == "be helpful"
    assert body["latest_version"] == 1


def test_create_rejects_missing_en():
    r = client.post(
        "/api/prompts",
        json={"name": "Spanish Only", "content": {"es": "Sé útil."}},
    )
    assert r.status_code == 400


def test_create_rejects_blank_name():
    r = client.post(
        "/api/prompts", json={"name": "  ", "content": {"en": "x"}}
    )
    assert r.status_code == 400


def test_create_rejects_duplicate_slug():
    client.post(
        "/api/prompts",
        json={"name": "Same", "content": {"en": "first"}},
    )
    second = client.post(
        "/api/prompts",
        json={"name": "Different", "slug": "same",
              "content": {"en": "second"}},
    )
    assert second.status_code == 409


# ── Versioning ───────────────────────────────────────────────────────────────


def test_create_version_monotonic():
    pid = client.post(
        "/api/prompts", json={"name": "P", "content": {"en": "v1"}}
    ).json()["prompt_id"]

    v2 = client.post(
        f"/api/prompts/{pid}/versions",
        json={"content": {"en": "v2"}, "change_note": "tweak"},
    )
    assert v2.status_code == 201
    assert v2.json()["version"] == 2

    v3 = client.post(
        f"/api/prompts/{pid}/versions",
        json={"content": {"en": "v3"}},
    ).json()
    assert v3["version"] == 3

    versions = client.get(f"/api/prompts/{pid}/versions").json()
    assert [v["version"] for v in versions] == [3, 2, 1]


def test_get_specific_version():
    pid = client.post(
        "/api/prompts", json={"name": "Pin", "content": {"en": "ORIGINAL"}}
    ).json()["prompt_id"]
    client.post(
        f"/api/prompts/{pid}/versions",
        json={"content": {"en": "EDITED"}},
    )
    v1 = client.get(f"/api/prompts/{pid}/versions/1").json()
    v2 = client.get(f"/api/prompts/{pid}/versions/2").json()
    assert v1["content"]["en"] == "ORIGINAL"
    assert v2["content"]["en"] == "EDITED"


def test_create_version_unknown_404():
    r = client.post(
        "/api/prompts/usr_nope/versions", json={"content": {"en": "x"}}
    )
    assert r.status_code == 404


# ── PATCH metadata ───────────────────────────────────────────────────────────


def test_patch_does_not_bump_version():
    pid = client.post(
        "/api/prompts", json={"name": "Old", "content": {"en": "x"}}
    ).json()["prompt_id"]

    r = client.patch(
        f"/api/prompts/{pid}",
        json={"name": "New", "description": "reason", "tags": ["renamed"]},
    )
    assert r.status_code == 200

    detail = client.get(f"/api/prompts/{pid}").json()
    assert detail["name"] == "New"
    assert detail["description"] == "reason"
    assert detail["tags"] == ["renamed"]
    assert detail["latest_version"] == 1


def test_patch_unknown_404():
    r = client.patch("/api/prompts/usr_nope", json={"name": "x"})
    assert r.status_code == 404


# ── Archive / restore ────────────────────────────────────────────────────────


def test_archive_excluded_from_default_listing():
    pid = client.post(
        "/api/prompts", json={"name": "P", "content": {"en": "x"}}
    ).json()["prompt_id"]

    archive = client.post(f"/api/prompts/{pid}/archive")
    assert archive.status_code == 200

    listing = client.get("/api/prompts").json()
    assert pid not in {p["id"] for p in listing}

    listing_inc = client.get("/api/prompts?include_archived=true").json()
    assert pid in {p["id"] for p in listing_inc}

    restored = client.post(f"/api/prompts/{pid}/restore")
    assert restored.status_code == 200
    assert pid in {p["id"] for p in client.get("/api/prompts").json()}


def test_archive_unknown_404():
    r = client.post("/api/prompts/usr_nope/archive")
    assert r.status_code == 404


# ── Metadata endpoint extension ──────────────────────────────────────────────


def test_metadata_includes_prompts():
    body = client.get("/api/metadata").json()
    assert "prompts" in body
    ids = {p["id"] for p in body["prompts"]}
    assert "builtin_analytical" in ids
    sample = next(p for p in body["prompts"] if p["id"] == "builtin_analytical")
    assert sample["latest_version"] == 1
    assert sample["is_builtin"] is True
    # All 6 languages have non-empty analytical text → all 6 codes present.
    assert set(sample["language_codes"]) == {"en", "es", "fr", "de", "zh", "ua"}
