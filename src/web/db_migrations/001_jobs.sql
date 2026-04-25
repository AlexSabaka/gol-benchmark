-- Phase 1: job records (replaces data/jobs/*.json).
--
-- Columns mirror src/web/jobs.py::Job.to_storable_dict(). Credentials land in
-- api_key_enc / api_base_enc as Fernet ciphertext — matches TD-085 encryption.
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL DEFAULT 2,
    model_name TEXT NOT NULL,
    testset_path TEXT NOT NULL,
    run_group_id TEXT,
    state TEXT NOT NULL,
    progress_current INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    result_path TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL,
    paused_at_index INTEGER,
    partial_result_path TEXT,
    provider TEXT NOT NULL DEFAULT 'ollama',
    ollama_host TEXT NOT NULL DEFAULT 'http://localhost:11434',
    output_dir TEXT NOT NULL DEFAULT 'results',
    temperature REAL NOT NULL DEFAULT 0.1,
    max_tokens INTEGER NOT NULL DEFAULT 2048,
    no_think INTEGER NOT NULL DEFAULT 1,
    api_key_enc TEXT,
    api_base_enc TEXT,
    accumulated_elapsed_seconds REAL NOT NULL DEFAULT 0.0,
    start_index INTEGER NOT NULL DEFAULT 0,
    hidden INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
CREATE INDEX IF NOT EXISTS idx_jobs_run_group ON jobs(run_group_id);
