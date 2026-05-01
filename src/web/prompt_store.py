"""Prompt Studio persistence — SQLite-backed versioned system prompts.

Public surface (all signatures stable; internals may evolve):

    list_prompts(*, include_archived=False) -> list[dict]
    get_prompt(prompt_id)                   -> dict | None     # latest version
    list_versions(prompt_id)                -> list[dict]      # newest first
    get_version(prompt_id, version)         -> dict | None
    resolve_text(prompt_id, version, language) -> str          # EN fallback baked in

    create_prompt(*, name, slug, description, content, tags, created_by) -> str
    create_version(prompt_id, *, content, change_note,
                   parent_version, created_by) -> int
    update_metadata(prompt_id, *, name=None, description=None, tags=None) -> None
    archive(prompt_id)
    restore(prompt_id)

    seed_builtins() -> int                                     # idempotent

Editing a prompt creates a NEW row in ``prompt_versions`` — never UPDATEs an
existing one — so result files pinned to ``(prompt_id, version)`` keep
replaying forever. ``content_json`` is a single JSON column keyed by
language code (``{"en": "...", "es": "..."}``), with ``"en"`` required on
every version.

Schema lives in :file:`db_migrations/003_prompts.sql`.
"""
from __future__ import annotations

import json
import logging
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src.core.PromptEngine import SYSTEM_PROMPTS, Language, SystemPromptStyle
from src.web.db import run_migrations, transaction

logger = logging.getLogger(__name__)


_BUILTIN_NAMES: dict[SystemPromptStyle, str] = {
    SystemPromptStyle.ANALYTICAL: "Analytical",
    SystemPromptStyle.CASUAL: "Casual",
    SystemPromptStyle.ADVERSARIAL: "Adversarial",
    SystemPromptStyle.NONE: "None",
}

_BUILTIN_DESCRIPTIONS: dict[SystemPromptStyle, str] = {
    SystemPromptStyle.ANALYTICAL:
        "Rigorous, step-by-step chain-of-thought reasoning.",
    SystemPromptStyle.CASUAL:
        "Friendly, conversational, supportive companion tone.",
    SystemPromptStyle.ADVERSARIAL:
        "Resource-efficient, intuitive over exhaustive analysis.",
    SystemPromptStyle.NONE:
        "Empty system prompt — the model receives no system directive.",
}

_MAX_NAME_LEN = 200
_MAX_DESCRIPTION_LEN = 2000
_MAX_TAGS = 32
_MAX_TAG_LEN = 64
_MAX_CONTENT_LANGS = 32
_MAX_CONTENT_BYTES = 64 * 1024  # 64KiB per language string
_MAX_CHANGE_NOTE_LEN = 1000


class PromptStoreError(ValueError):
    """Raised on invalid input or constraint violation surfaced by the store."""


class PromptNotFoundError(PromptStoreError):
    pass


class PromptSlugConflictError(PromptStoreError):
    pass


class PromptStore:
    """SQLite-backed persistence for versioned system prompts."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        run_migrations(self._conn)

    # ── Read interface ────────────────────────────────────────────────────────

    def list_prompts(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        """Return every prompt with its latest version's number + creation time
        and language coverage. ``language_codes`` is the set of language keys
        on the latest version's ``content_json`` whose values are non-empty —
        feeds the catalog's language-coverage strip without an N+1 fetch.
        """
        sql = """
            SELECT
                p.id, p.name, p.slug, p.description, p.is_builtin, p.tags,
                p.archived_at, p.created_at, p.created_by, p.updated_at,
                latest.version       AS latest_version,
                latest.content_json  AS latest_content_json
            FROM prompts p
            LEFT JOIN (
                SELECT v.prompt_id, v.version, v.content_json
                FROM prompt_versions v
                JOIN (
                    SELECT prompt_id, MAX(version) AS max_version
                    FROM prompt_versions GROUP BY prompt_id
                ) m
                  ON v.prompt_id = m.prompt_id AND v.version = m.max_version
            ) latest ON latest.prompt_id = p.id
        """
        params: tuple = ()
        if not include_archived:
            sql += " WHERE p.archived_at IS NULL"
        sql += " ORDER BY p.is_builtin DESC, p.name COLLATE NOCASE"
        rows = self._conn.execute(sql, params).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            summary = _summary_from_row(row)
            content = _loads_content(row["latest_content_json"])
            summary["language_codes"] = sorted(
                lang for lang, text in content.items() if text
            )
            results.append(summary)
        return results

    def get_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        """Return prompt metadata + the latest version's content, or None."""
        meta = self._fetch_prompt_row(prompt_id)
        if meta is None:
            return None
        latest = self._conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_id = ? "
            "ORDER BY version DESC LIMIT 1",
            (prompt_id,),
        ).fetchone()
        result = _summary_from_row(meta)
        result["latest_version"] = latest["version"] if latest else None
        content = _loads_content(latest["content_json"]) if latest else {}
        result["content"] = content
        result["change_note"] = latest["change_note"] if latest else ""
        result["language_codes"] = sorted(
            lang for lang, text in content.items() if text
        )
        return result

    def list_versions(self, prompt_id: str) -> list[dict[str, Any]]:
        if self._fetch_prompt_row(prompt_id) is None:
            raise PromptNotFoundError(f"Unknown prompt_id: {prompt_id!r}")
        rows = self._conn.execute(
            "SELECT version, parent_version, change_note, created_at, created_by "
            "FROM prompt_versions WHERE prompt_id = ? ORDER BY version DESC",
            (prompt_id,),
        ).fetchall()
        return [
            {
                "version": r["version"],
                "parent_version": r["parent_version"],
                "change_note": r["change_note"] or "",
                "created_at": r["created_at"],
                "created_by": r["created_by"],
            }
            for r in rows
        ]

    def get_version(self, prompt_id: str, version: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_id = ? AND version = ?",
            (prompt_id, int(version)),
        ).fetchone()
        if row is None:
            return None
        return {
            "prompt_id": row["prompt_id"],
            "version": row["version"],
            "parent_version": row["parent_version"],
            "change_note": row["change_note"] or "",
            "content": _loads_content(row["content_json"]),
            "created_at": row["created_at"],
            "created_by": row["created_by"],
        }

    def resolve_text(
        self, prompt_id: str, version: int, language: str
    ) -> str:
        """Return the prompt text for ``language`` at ``(prompt_id, version)``.

        Falls back to English when the language is missing or empty. Returns
        ``""`` when the version is unknown — callers downstream of testset
        generation should never hit that path because the resolved TEXT is
        embedded in the testset at write time.
        """
        version_record = self.get_version(prompt_id, int(version))
        if version_record is None:
            logger.warning(
                "resolve_text: missing prompt version %s@v%s", prompt_id, version
            )
            return ""
        content = version_record["content"] or {}
        text = content.get(language) or content.get("en") or ""
        return text

    # ── Write interface ───────────────────────────────────────────────────────

    def create_prompt(
        self,
        *,
        name: str,
        slug: str | None = None,
        description: str = "",
        content: dict[str, str],
        tags: list[str] | None = None,
        created_by: str | None = None,
    ) -> str:
        """Create a new user-authored prompt at v1. Returns the new prompt_id."""
        name = _validate_name(name)
        description = _validate_description(description)
        tags = _validate_tags(tags or [])
        content = _validate_content(content)
        slug = _slugify(slug or name)

        prompt_id = _generate_user_prompt_id()
        now = _utcnow_iso()
        with transaction(self._conn):
            self._insert_prompt_row(
                prompt_id=prompt_id,
                name=name,
                slug=slug,
                description=description,
                is_builtin=0,
                tags=tags,
                created_at=now,
                created_by=created_by,
            )
            self._insert_version_row(
                prompt_id=prompt_id,
                version=1,
                content=content,
                parent_version=None,
                change_note="initial version",
                created_at=now,
                created_by=created_by,
            )
        return prompt_id

    def create_version(
        self,
        prompt_id: str,
        *,
        content: dict[str, str],
        change_note: str = "",
        parent_version: int | None = None,
        created_by: str | None = None,
    ) -> int:
        """Append a new version to an existing prompt. Returns the new number."""
        content = _validate_content(content)
        change_note = _validate_change_note(change_note)
        meta = self._fetch_prompt_row(prompt_id)
        if meta is None:
            raise PromptNotFoundError(f"Unknown prompt_id: {prompt_id!r}")

        with transaction(self._conn):
            current = self._conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS v "
                "FROM prompt_versions WHERE prompt_id = ?",
                (prompt_id,),
            ).fetchone()
            next_version = int(current["v"]) + 1
            if parent_version is None:
                parent_version = next_version - 1 if next_version > 1 else None
            self._insert_version_row(
                prompt_id=prompt_id,
                version=next_version,
                content=content,
                parent_version=parent_version,
                change_note=change_note,
                created_at=_utcnow_iso(),
                created_by=created_by,
            )
            self._touch_updated_at(prompt_id)
        return next_version

    def update_metadata(
        self,
        prompt_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        if self._fetch_prompt_row(prompt_id) is None:
            raise PromptNotFoundError(f"Unknown prompt_id: {prompt_id!r}")
        sets: list[str] = []
        values: list[Any] = []
        if name is not None:
            sets.append("name = ?")
            values.append(_validate_name(name))
        if description is not None:
            sets.append("description = ?")
            values.append(_validate_description(description))
        if tags is not None:
            sets.append("tags = ?")
            values.append(json.dumps(_validate_tags(tags), ensure_ascii=False))
        if not sets:
            return
        sets.append("updated_at = ?")
        values.append(_utcnow_iso())
        values.append(prompt_id)
        self._conn.execute(
            f"UPDATE prompts SET {', '.join(sets)} WHERE id = ?", tuple(values)
        )

    def archive(self, prompt_id: str) -> None:
        if self._fetch_prompt_row(prompt_id) is None:
            raise PromptNotFoundError(f"Unknown prompt_id: {prompt_id!r}")
        self._conn.execute(
            "UPDATE prompts SET archived_at = ?, updated_at = ? WHERE id = ?",
            (_utcnow_iso(), _utcnow_iso(), prompt_id),
        )

    def restore(self, prompt_id: str) -> None:
        if self._fetch_prompt_row(prompt_id) is None:
            raise PromptNotFoundError(f"Unknown prompt_id: {prompt_id!r}")
        self._conn.execute(
            "UPDATE prompts SET archived_at = NULL, updated_at = ? WHERE id = ?",
            (_utcnow_iso(), prompt_id),
        )

    # ── Seeding ───────────────────────────────────────────────────────────────

    def seed_builtins(self) -> int:
        """Insert the four canonical built-in prompts at v1 if missing.

        Idempotent — only inserts prompt_ids that don't already exist. Returns
        the count of newly inserted prompts (0 on subsequent boots).
        """
        created = 0
        for style in (
            SystemPromptStyle.ANALYTICAL,
            SystemPromptStyle.CASUAL,
            SystemPromptStyle.ADVERSARIAL,
            SystemPromptStyle.NONE,
        ):
            prompt_id = f"builtin_{style.value}"
            if self._fetch_prompt_row(prompt_id) is not None:
                continue
            content = _builtin_content_for_style(style)
            now = _utcnow_iso()
            with transaction(self._conn):
                self._insert_prompt_row(
                    prompt_id=prompt_id,
                    name=_BUILTIN_NAMES[style],
                    slug=prompt_id,  # builtins keep stable, predictable slugs
                    description=_BUILTIN_DESCRIPTIONS[style],
                    is_builtin=1,
                    tags=["builtin", style.value],
                    created_at=now,
                    created_by="system",
                )
                self._insert_version_row(
                    prompt_id=prompt_id,
                    version=1,
                    content=content,
                    parent_version=None,
                    change_note="seeded from PromptEngine.SYSTEM_PROMPTS",
                    created_at=now,
                    created_by="system",
                )
            created += 1
            logger.info("Seeded built-in prompt: %s", prompt_id)
        return created

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_prompt_row(self, prompt_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM prompts WHERE id = ?", (prompt_id,)
        ).fetchone()

    def _insert_prompt_row(
        self,
        *,
        prompt_id: str,
        name: str,
        slug: str,
        description: str,
        is_builtin: int,
        tags: list[str],
        created_at: str,
        created_by: str | None,
    ) -> None:
        try:
            self._conn.execute(
                "INSERT INTO prompts "
                "(id, name, slug, description, is_builtin, tags, "
                "created_at, created_by, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    prompt_id,
                    name,
                    slug,
                    description,
                    int(is_builtin),
                    json.dumps(tags, ensure_ascii=False),
                    created_at,
                    created_by,
                    created_at,
                ),
            )
        except sqlite3.IntegrityError as exc:
            msg = str(exc).lower()
            if "prompts.slug" in msg or "unique" in msg and "slug" in msg:
                raise PromptSlugConflictError(
                    f"Slug already in use: {slug!r}"
                ) from exc
            raise

    def _insert_version_row(
        self,
        *,
        prompt_id: str,
        version: int,
        content: dict[str, str],
        parent_version: int | None,
        change_note: str,
        created_at: str,
        created_by: str | None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO prompt_versions "
            "(prompt_id, version, content_json, parent_version, "
            "change_note, created_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                prompt_id,
                int(version),
                json.dumps(content, ensure_ascii=False),
                parent_version,
                change_note,
                created_at,
                created_by,
            ),
        )

    def _touch_updated_at(self, prompt_id: str) -> None:
        self._conn.execute(
            "UPDATE prompts SET updated_at = ? WHERE id = ?",
            (_utcnow_iso(), prompt_id),
        )


# ── Validation & helpers ──────────────────────────────────────────────────────


def _validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise PromptStoreError("name must be a string")
    name = name.strip()
    if not name:
        raise PromptStoreError("name must be non-empty")
    if len(name) > _MAX_NAME_LEN:
        raise PromptStoreError(f"name exceeds {_MAX_NAME_LEN} chars")
    return name


def _validate_description(description: str) -> str:
    if not isinstance(description, str):
        raise PromptStoreError("description must be a string")
    if len(description) > _MAX_DESCRIPTION_LEN:
        raise PromptStoreError(
            f"description exceeds {_MAX_DESCRIPTION_LEN} chars"
        )
    return description


def _validate_tags(tags: list[str]) -> list[str]:
    if not isinstance(tags, list):
        raise PromptStoreError("tags must be a list")
    if len(tags) > _MAX_TAGS:
        raise PromptStoreError(f"tags exceeds {_MAX_TAGS} entries")
    cleaned: list[str] = []
    for t in tags:
        if not isinstance(t, str):
            raise PromptStoreError("tag must be a string")
        t = t.strip()
        if not t:
            continue
        if len(t) > _MAX_TAG_LEN:
            raise PromptStoreError(f"tag exceeds {_MAX_TAG_LEN} chars")
        cleaned.append(t)
    return cleaned


def _validate_content(content: dict[str, str]) -> dict[str, str]:
    if not isinstance(content, dict):
        raise PromptStoreError("content must be a dict")
    if "en" not in content:
        raise PromptStoreError("content must include 'en'")
    if len(content) > _MAX_CONTENT_LANGS:
        raise PromptStoreError(
            f"content exceeds {_MAX_CONTENT_LANGS} languages"
        )
    cleaned: dict[str, str] = {}
    for lang, text in content.items():
        if not isinstance(lang, str) or not lang:
            raise PromptStoreError("content keys must be non-empty strings")
        if not isinstance(text, str):
            raise PromptStoreError(
                f"content[{lang!r}] must be a string"
            )
        if len(text.encode("utf-8")) > _MAX_CONTENT_BYTES:
            raise PromptStoreError(
                f"content[{lang!r}] exceeds {_MAX_CONTENT_BYTES} bytes"
            )
        cleaned[lang] = text
    en_text = cleaned.get("en", "").strip()
    if not en_text:
        raise PromptStoreError("content['en'] must be non-empty")
    return cleaned


def _validate_change_note(note: str) -> str:
    if not isinstance(note, str):
        raise PromptStoreError("change_note must be a string")
    if len(note) > _MAX_CHANGE_NOTE_LEN:
        raise PromptStoreError(
            f"change_note exceeds {_MAX_CHANGE_NOTE_LEN} chars"
        )
    return note


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """Lowercase ASCII kebab-case slug. Empty input → 'prompt'."""
    s = _SLUG_NON_ALNUM.sub("-", value.lower()).strip("-")
    return s or "prompt"


def _generate_user_prompt_id() -> str:
    """``usr_`` + 12 hex chars (48 bits of entropy)."""
    return f"usr_{secrets.token_hex(6)}"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _loads_content(text: Any) -> dict[str, str]:
    if not text:
        return {}
    try:
        v = json.loads(text)
    except Exception:
        return {}
    if not isinstance(v, dict):
        return {}
    return {str(k): str(val) for k, val in v.items() if isinstance(val, str)}


def _summary_from_row(row: sqlite3.Row) -> dict[str, Any]:
    keys = row.keys()
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "description": row["description"] or "",
        "is_builtin": bool(row["is_builtin"]),
        "tags": _loads_tags(row["tags"]),
        "archived_at": row["archived_at"],
        "created_at": row["created_at"],
        "created_by": row["created_by"],
        "updated_at": row["updated_at"],
        "latest_version": row["latest_version"] if "latest_version" in keys else None,
    }


def _loads_tags(text: Any) -> list[str]:
    if not text:
        return []
    try:
        v = json.loads(text)
    except Exception:
        return []
    return [str(x) for x in v if isinstance(x, str)] if isinstance(v, list) else []


def _builtin_content_for_style(style: SystemPromptStyle) -> dict[str, str]:
    """Project the nested SYSTEM_PROMPTS dict into a {lang: text} map."""
    out: dict[str, str] = {}
    for lang in Language:
        text = SYSTEM_PROMPTS.get(lang, {}).get(style, "")
        # NONE has empty strings; we still record them so resolve_text returns
        # "" deterministically without falling through to EN.
        out[lang.value] = text
    # _validate_content requires non-empty 'en'. NONE intentionally violates
    # that — seed_builtins inserts directly bypassing _validate_content, so
    # this is fine; keep all six language keys even if empty.
    return out


# ── Module-level singleton (wired by app.py lifespan) ─────────────────────────


_store: PromptStore | None = None


def set_store(store: PromptStore | None) -> None:
    """Install the process-wide store. Called by ``src.web.app``."""
    global _store
    _store = store


def get_store() -> PromptStore:
    """Return the installed store; raise if ``set_store`` wasn't called."""
    if _store is None:
        raise RuntimeError(
            "PromptStore has not been initialized. "
            "src.web.app wires it at startup; tests must call set_store()."
        )
    return _store
