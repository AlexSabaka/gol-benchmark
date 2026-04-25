-- Phase 2: annotation records (replaces data/annotations/*.json.gz sidecars).
--
-- Schema mirrors the sidecar case-record shape 1:1 so the aggregator (which
-- consumes sidecar-shaped dicts) can feed off the store with no structural
-- changes. List-valued fields (spans, context_anchors, etc.) are JSON columns
-- — SQLite's JSON1 is available if we ever need to query into them. No child
-- tables because we never query span-by-column.
--
-- The PK is (result_file_id, case_id, response_hash). response_hash is now a
-- 16-hex-char SHA256 prefix (TD-096) but the column stores whatever the writer
-- supplies — legacy MD5 hashes migrated in as-is if the source result file is
-- unavailable for rehashing.
CREATE TABLE IF NOT EXISTS annotations (
    result_file_id    TEXT NOT NULL,
    case_id           TEXT NOT NULL,
    response_hash     TEXT NOT NULL,
    -- Per-case context surfaced to the aggregator
    response_length   INTEGER,
    parser_match_type TEXT,
    parser_extracted  TEXT,
    expected          TEXT,
    language          TEXT,
    user_style        TEXT,
    system_style      TEXT,
    parse_strategy    TEXT,
    parse_confidence  TEXT,
    model_name        TEXT,
    -- v3 annotation payload (JSON arrays of dicts)
    spans             TEXT NOT NULL DEFAULT '[]',
    response_classes  TEXT NOT NULL DEFAULT '[]',
    context_anchors   TEXT NOT NULL DEFAULT '[]',
    answer_keywords   TEXT NOT NULL DEFAULT '[]',
    negative_spans    TEXT NOT NULL DEFAULT '[]',
    negative_keywords TEXT NOT NULL DEFAULT '[]',
    context_windows   TEXT NOT NULL DEFAULT '[]',
    annotator_note    TEXT NOT NULL DEFAULT '',
    annotation_ts     TEXT,
    -- File-level denormalized meta (copied onto every row of a file)
    plugin            TEXT,
    annotated_by      TEXT,
    file_created_at   TEXT,
    file_updated_at   TEXT,
    PRIMARY KEY (result_file_id, case_id, response_hash)
);
CREATE INDEX IF NOT EXISTS idx_annotations_result_file ON annotations(result_file_id);
CREATE INDEX IF NOT EXISTS idx_annotations_updated_at ON annotations(file_updated_at);
