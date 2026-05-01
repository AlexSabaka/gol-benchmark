"""Tests for :class:`src.web.prompt_store.PromptStore` and built-in seeding."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.PromptEngine import SYSTEM_PROMPTS, Language, SystemPromptStyle
from src.web import db
from src.web.prompt_store import (
    PromptNotFoundError,
    PromptSlugConflictError,
    PromptStore,
    PromptStoreError,
)


@pytest.fixture
def store(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    try:
        yield PromptStore(conn)
    finally:
        conn.close()


# ── Read interface ────────────────────────────────────────────────────────────


def test_list_empty(store: PromptStore):
    assert store.list_prompts() == []


def test_get_unknown_returns_none(store: PromptStore):
    assert store.get_prompt("usr_does_not_exist") is None
    assert store.get_version("usr_does_not_exist", 1) is None


def test_resolve_text_unknown_returns_empty(store: PromptStore):
    assert store.resolve_text("usr_missing", 1, "en") == ""


# ── Create + round-trip ───────────────────────────────────────────────────────


def test_create_prompt_roundtrip(store: PromptStore):
    pid = store.create_prompt(
        name="My Debug Prompt",
        description="Helps trace issues.",
        content={"en": "Be helpful and verbose."},
        tags=["debug", "experimental"],
        created_by="alex",
    )
    assert pid.startswith("usr_")

    detail = store.get_prompt(pid)
    assert detail is not None
    assert detail["name"] == "My Debug Prompt"
    assert detail["slug"] == "my-debug-prompt"
    assert detail["is_builtin"] is False
    assert detail["tags"] == ["debug", "experimental"]
    assert detail["latest_version"] == 1
    assert detail["content"] == {"en": "Be helpful and verbose."}
    assert detail["change_note"] == "initial version"


def test_create_prompt_rejects_missing_en(store: PromptStore):
    with pytest.raises(PromptStoreError):
        store.create_prompt(
            name="Spanish Only",
            content={"es": "Sé útil."},
        )


def test_create_prompt_rejects_empty_en(store: PromptStore):
    with pytest.raises(PromptStoreError):
        store.create_prompt(
            name="Empty",
            content={"en": "   "},
        )


def test_create_prompt_rejects_duplicate_slug(store: PromptStore):
    store.create_prompt(name="Same Name", content={"en": "first"})
    with pytest.raises(PromptSlugConflictError):
        store.create_prompt(
            name="Different",
            slug="same-name",
            content={"en": "second"},
        )


def test_create_prompt_rejects_blank_name(store: PromptStore):
    with pytest.raises(PromptStoreError):
        store.create_prompt(name="   ", content={"en": "ok"})


# ── Versioning ────────────────────────────────────────────────────────────────


def test_create_version_monotonic(store: PromptStore):
    pid = store.create_prompt(name="P", content={"en": "v1"})
    v2 = store.create_version(pid, content={"en": "v2"}, change_note="tweak")
    v3 = store.create_version(pid, content={"en": "v3"})
    assert v2 == 2 and v3 == 3
    versions = store.list_versions(pid)
    # Newest first
    assert [v["version"] for v in versions] == [3, 2, 1]
    # parent_version auto-derived
    assert versions[0]["parent_version"] == 2
    assert versions[1]["parent_version"] == 1
    assert versions[2]["parent_version"] is None


def test_create_version_unknown_prompt(store: PromptStore):
    with pytest.raises(PromptNotFoundError):
        store.create_version("usr_nope", content={"en": "x"})


def test_get_version_returns_immutable_content(store: PromptStore):
    pid = store.create_prompt(name="P", content={"en": "ORIGINAL"})
    store.create_version(pid, content={"en": "EDITED"})
    v1 = store.get_version(pid, 1)
    v2 = store.get_version(pid, 2)
    assert v1 is not None and v2 is not None
    assert v1["content"]["en"] == "ORIGINAL"
    assert v2["content"]["en"] == "EDITED"
    assert v2["parent_version"] == 1


# ── update_metadata ───────────────────────────────────────────────────────────


def test_update_metadata_does_not_bump_version(store: PromptStore):
    pid = store.create_prompt(name="Old Name", content={"en": "x"})
    store.update_metadata(pid, name="New Name", description="A reason.",
                          tags=["renamed"])
    detail = store.get_prompt(pid)
    assert detail["name"] == "New Name"
    assert detail["description"] == "A reason."
    assert detail["tags"] == ["renamed"]
    assert detail["latest_version"] == 1
    # Content unchanged
    assert detail["content"] == {"en": "x"}


def test_update_metadata_unknown_prompt(store: PromptStore):
    with pytest.raises(PromptNotFoundError):
        store.update_metadata("usr_nope", name="x")


# ── archive / restore ────────────────────────────────────────────────────────


def test_archive_excluded_from_default_list(store: PromptStore):
    pid = store.create_prompt(name="P", content={"en": "x"})
    assert any(p["id"] == pid for p in store.list_prompts())
    store.archive(pid)
    assert not any(p["id"] == pid for p in store.list_prompts())
    assert any(
        p["id"] == pid for p in store.list_prompts(include_archived=True)
    )
    detail = store.get_prompt(pid)
    assert detail["archived_at"] is not None


def test_restore_brings_back(store: PromptStore):
    pid = store.create_prompt(name="P", content={"en": "x"})
    store.archive(pid)
    store.restore(pid)
    assert any(p["id"] == pid for p in store.list_prompts())
    detail = store.get_prompt(pid)
    assert detail["archived_at"] is None


# ── resolve_text fallback ────────────────────────────────────────────────────


def test_resolve_text_language_present(store: PromptStore):
    pid = store.create_prompt(
        name="Multi", content={"en": "EN text", "es": "ES text"}
    )
    assert store.resolve_text(pid, 1, "en") == "EN text"
    assert store.resolve_text(pid, 1, "es") == "ES text"


def test_resolve_text_falls_back_to_en(store: PromptStore):
    pid = store.create_prompt(name="EN Only", content={"en": "just english"})
    assert store.resolve_text(pid, 1, "fr") == "just english"
    assert store.resolve_text(pid, 1, "ua") == "just english"


def test_resolve_text_empty_language_falls_back(store: PromptStore):
    # Stored entry has empty FR, non-empty EN — FR call should still surface EN.
    pid = store.create_prompt(
        name="Sparse", content={"en": "english", "fr": ""}
    )
    assert store.resolve_text(pid, 1, "fr") == "english"


# ── seed_builtins ────────────────────────────────────────────────────────────


def test_seed_builtins_inserts_four(store: PromptStore):
    n = store.seed_builtins()
    assert n == 4
    listing = store.list_prompts()
    ids = {p["id"] for p in listing}
    assert ids == {
        "builtin_analytical", "builtin_casual",
        "builtin_adversarial", "builtin_none",
    }
    for p in listing:
        assert p["is_builtin"] is True
        assert p["latest_version"] == 1


def test_seed_builtins_idempotent(store: PromptStore):
    store.seed_builtins()
    second = store.seed_builtins()
    assert second == 0
    assert len(store.list_prompts()) == 4


def test_seed_builtins_content_matches_promptengine(store: PromptStore):
    store.seed_builtins()
    for style in (
        SystemPromptStyle.ANALYTICAL,
        SystemPromptStyle.CASUAL,
        SystemPromptStyle.ADVERSARIAL,
    ):
        pid = f"builtin_{style.value}"
        for lang in Language:
            expected = SYSTEM_PROMPTS[lang][style]
            assert store.resolve_text(pid, 1, lang.value) == expected


def test_seed_builtins_none_resolves_to_empty(store: PromptStore):
    store.seed_builtins()
    # NONE is intentionally empty across all languages — resolve to "".
    for lang in Language:
        assert store.resolve_text("builtin_none", 1, lang.value) == ""


# ── Tags JSON storage round-trips ────────────────────────────────────────────


def test_tags_round_trip(store: PromptStore):
    pid = store.create_prompt(
        name="Tagged",
        content={"en": "x"},
        tags=["t1", "t2", "non-ascii: ☕"],
    )
    detail = store.get_prompt(pid)
    assert detail["tags"] == ["t1", "t2", "non-ascii: ☕"]


def test_tags_strip_blanks_and_validate_types(store: PromptStore):
    pid = store.create_prompt(
        name="Cleaned", content={"en": "x"}, tags=["a", "  ", "b"]
    )
    detail = store.get_prompt(pid)
    assert detail["tags"] == ["a", "b"]

    with pytest.raises(PromptStoreError):
        store.create_prompt(name="Bad", content={"en": "x"},
                            tags=["a", 123])  # type: ignore[list-item]
