"""Tests for the Prompt Studio matrix axis — `system_style` derivation."""
from __future__ import annotations

import pytest

from src.stages.generate_testset import (
    _resolve_latest_prompt_version,
    _system_style_for as _gt_system_style_for,
)
from src.web.api.matrix import (
    MatrixPromptAxes,
    _build_prompt_combinations,
    _system_style_for,
)


# ── _system_style_for (matrix.py) ─────────────────────────────────────────────


def test_system_style_for_builtin_analytical():
    assert _system_style_for("builtin_analytical") == "analytical"


def test_system_style_for_builtin_casual():
    assert _system_style_for("builtin_casual") == "casual"


def test_system_style_for_builtin_adversarial():
    assert _system_style_for("builtin_adversarial") == "adversarial"


def test_system_style_for_builtin_none():
    assert _system_style_for("builtin_none") == "none"


def test_system_style_for_user_prompt_is_custom():
    assert _system_style_for("usr_abc123") == "custom"


def test_system_style_for_unknown_prefix_is_custom():
    assert _system_style_for("special-prefix") == "custom"


# ── generate_testset.py mirror helper ─────────────────────────────────────────


def test_generate_testset_helper_matches_matrix_helper():
    """The two derivation helpers must agree across all known prefixes."""
    for pid in (
        "builtin_analytical",
        "builtin_casual",
        "builtin_adversarial",
        "builtin_none",
        "usr_abc123",
        "anything_else",
    ):
        assert _gt_system_style_for(pid) == _system_style_for(pid)


# ── _build_prompt_combinations end-to-end ─────────────────────────────────────


@pytest.fixture
def populated_store():
    """Ensure built-in prompts are seeded so prompt-id resolution succeeds.

    The PromptStore is a process-wide singleton wired by the FastAPI
    lifespan. ``test_api_prompts.py`` already opens the lifespan via
    TestClient at import time, so when this module runs alongside it the
    store is already there. Importing it here ensures lifespan is up.
    """
    import tests.test_api_prompts  # noqa: F401  (side-effect: opens lifespan)
    yield


def test_build_combinations_with_builtin_prompt_ids(populated_store):
    axes = MatrixPromptAxes(
        user_styles=["minimal"],
        system_styles=[],
        languages=["en"],
        prompt_ids=["builtin_casual"],
    )
    combos = _build_prompt_combinations(axes)
    assert len(combos) == 1
    config = combos[0]
    assert config.prompt_id == "builtin_casual"
    assert config.prompt_version == 1
    # ── back-compat tag derived from the prompt_id, not from system_styles ──
    assert config.system_style == "casual"


def test_build_combinations_multiplies_axes(populated_store):
    axes = MatrixPromptAxes(
        user_styles=["minimal", "casual"],
        system_styles=[],
        languages=["en", "es"],
        prompt_ids=["builtin_analytical", "builtin_adversarial"],
    )
    combos = _build_prompt_combinations(axes)
    # 2 user × 2 lang × 2 prompts = 8 cells
    assert len(combos) == 8
    # Every combo carries a derived system_style from its prompt_id.
    for c in combos:
        assert c.system_style == _system_style_for(c.prompt_id or "")


def test_build_combinations_legacy_path_still_works(populated_store):
    """When prompt_ids is empty, the legacy enum cartesian still applies."""
    axes = MatrixPromptAxes(
        user_styles=["minimal"],
        system_styles=["analytical", "casual"],
        languages=["en"],
        prompt_ids=[],
    )
    combos = _build_prompt_combinations(axes)
    assert len(combos) == 2
    styles = sorted(c.system_style for c in combos)
    assert styles == ["analytical", "casual"]
    # Legacy combos don't carry prompt_id.
    for c in combos:
        assert c.prompt_id is None


# ── _resolve_latest_prompt_version ────────────────────────────────────────────
#
# Regression coverage for the bug where unpinned user prompts (prompt_version
# = None) silently fell back to the analytical built-in. The fix resolves
# `None → latest_version` at testset-generation time so the runtime guard at
# `src/plugins/base.py:_get_system_prompt` accepts the (id, version) pair.


def test_resolve_latest_prompt_version_for_builtin(populated_store):
    """Built-ins are seeded at v1 by the lifespan."""
    assert _resolve_latest_prompt_version("builtin_analytical") == 1


def test_resolve_latest_prompt_version_for_user_prompt(populated_store):
    """User-authored prompts resolve to whatever version the store reports."""
    from src.web import prompt_store as prompt_store_module

    store = prompt_store_module.get_store()
    pid = store.create_prompt(
        name="LatestResolverFixture",
        description="",
        content={"en": "I AM CUSTOM XYZ"},
        tags=[],
    )
    try:
        # v1 only.
        assert _resolve_latest_prompt_version(pid) == 1
        # Cut v2 — resolver must follow.
        store.create_version(prompt_id=pid, content={"en": "v2 body"})
        assert _resolve_latest_prompt_version(pid) == 2
    finally:
        store._conn.execute("DELETE FROM prompt_versions WHERE prompt_id = ?", (pid,))
        store._conn.execute("DELETE FROM prompts WHERE id = ?", (pid,))
        store._conn.commit()


def test_resolve_latest_prompt_version_unknown_returns_none(populated_store):
    """Unknown ids must not raise — caller falls back to legacy enum path."""
    assert _resolve_latest_prompt_version("usr_does_not_exist") is None
