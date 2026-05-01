-- Phase 3: Prompt Studio — versioned, user-managed system prompts.
--
-- Two tables: parent metadata (`prompts`) + immutable versions
-- (`prompt_versions`). Editing a prompt creates a new row in
-- `prompt_versions` — never UPDATEs an existing one — so old result files
-- pinned to (prompt_id, version) keep replaying forever.
--
-- Built-in prompts (analytical / casual / adversarial / none) are seeded
-- at first boot from src/core/PromptEngine.py::SYSTEM_PROMPTS via
-- PromptStore.seed_builtins(). They use stable IDs (`builtin_<style>`)
-- and may be edited by users — that creates v2+ on top of the immutable
-- v1.
--
-- Multi-language content lives in a single `content_json` column keyed
-- by language code: {"en": "...", "es": "...", ...}. "en" is required
-- on every version; missing languages fall back to English at resolve
-- time (matches PromptEngine.get_system_prompt semantics).
CREATE TABLE IF NOT EXISTS prompts (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    slug          TEXT NOT NULL UNIQUE,
    description   TEXT NOT NULL DEFAULT '',
    is_builtin    INTEGER NOT NULL DEFAULT 0,
    tags          TEXT NOT NULL DEFAULT '[]',
    archived_at   TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    created_by    TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    prompt_id      TEXT NOT NULL,
    version        INTEGER NOT NULL,
    content_json   TEXT NOT NULL,
    parent_version INTEGER,
    change_note    TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    created_by     TEXT,
    PRIMARY KEY (prompt_id, version),
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_prompts_archived   ON prompts(archived_at);
CREATE INDEX IF NOT EXISTS idx_prompts_is_builtin ON prompts(is_builtin);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_id ON prompt_versions(prompt_id);
