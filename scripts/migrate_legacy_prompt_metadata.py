#!/usr/bin/env python3
"""Backfill ``prompt_id`` / ``prompt_version`` onto legacy result files.

Pre-Prompt-Studio result entries record only ``system_style`` in
``input.prompt_metadata``. Prompt Studio analytics group by ``prompt_id`` +
``prompt_version`` instead, so old result files are invisible until backfilled.

This script walks every ``.json.gz`` under the given results directory and,
for each entry whose ``prompt_metadata`` lacks ``prompt_id``, sets:

    pm["prompt_id"]      = f"builtin_{pm['system_style']}"
    pm["prompt_version"] = 1

— matching the four built-in prompts seeded by ``PromptStore.seed_builtins``.
``system_style`` is preserved untouched so old chart code keeps working.

Idempotent: entries that already have ``prompt_id`` are skipped. Writes back
atomically (``temp + os.replace``). Logs per-file counts.

⚠️  This rewrites files in place. Run::

      cp -R results results.bak
      python scripts/migrate_legacy_prompt_metadata.py results

before letting it loose on a working dataset.
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("migrate_legacy_prompt_metadata")


@dataclass
class FileStats:
    file: Path
    entries_seen: int = 0
    entries_migrated: int = 0
    skipped_no_system_style: int = 0
    error: str | None = None


def migrate_file(path: Path, *, dry_run: bool) -> FileStats:
    stats = FileStats(file=path)
    try:
        with gzip.open(str(path), "rt", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        stats.error = f"open: {exc!r}"
        return stats

    results = data.get("results")
    if not isinstance(results, list):
        stats.error = "no 'results' list"
        return stats

    for entry in results:
        if not isinstance(entry, dict):
            continue
        inp = entry.get("input")
        if not isinstance(inp, dict):
            continue
        pm = inp.get("prompt_metadata")
        if not isinstance(pm, dict):
            pm = {}
            inp["prompt_metadata"] = pm
        stats.entries_seen += 1

        if pm.get("prompt_id"):
            continue  # already migrated

        system_style = pm.get("system_style")
        if not system_style:
            stats.skipped_no_system_style += 1
            continue

        pm["prompt_id"] = f"builtin_{system_style}"
        pm["prompt_version"] = 1
        stats.entries_migrated += 1

    if stats.entries_migrated == 0 or dry_run:
        return stats

    # Atomic write: temp file in same dir + os.replace.
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=path.stem + ".", suffix=".tmp.json.gz", dir=str(path.parent)
    )
    try:
        os.close(tmp_fd)
        with gzip.open(tmp_name, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_name, str(path))
    except Exception as exc:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        stats.error = f"write: {exc!r}"
    return stats


def migrate_directory(root: Path, *, dry_run: bool) -> list[FileStats]:
    files = sorted(root.rglob("*.json.gz"))
    return [migrate_file(p, dry_run=dry_run) for p in files]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill prompt_id / prompt_version on legacy result files. "
            "Idempotent; rewrites files in place."
        )
    )
    parser.add_argument(
        "results_dir", type=Path, help="Path to a directory of result files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Per-file logging"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.results_dir.is_dir():
        logger.error("Not a directory: %s", args.results_dir)
        return 2

    all_stats = migrate_directory(args.results_dir, dry_run=args.dry_run)
    files_changed = 0
    files_errored = 0
    total_seen = 0
    total_migrated = 0
    total_skipped = 0
    for s in all_stats:
        total_seen += s.entries_seen
        total_migrated += s.entries_migrated
        total_skipped += s.skipped_no_system_style
        if s.error:
            files_errored += 1
            logger.warning("error %s: %s", s.file, s.error)
            continue
        if s.entries_migrated > 0:
            files_changed += 1
            logger.info(
                "%s: migrated %d/%d entries (%d skipped — no system_style)",
                s.file,
                s.entries_migrated,
                s.entries_seen,
                s.skipped_no_system_style,
            )
        elif args.verbose:
            logger.debug(
                "%s: nothing to migrate (%d entries)", s.file, s.entries_seen
            )

    mode = "DRY-RUN — " if args.dry_run else ""
    logger.info(
        "%sscanned %d file(s); files-changed=%d; files-errored=%d; "
        "entries-seen=%d; entries-migrated=%d; entries-skipped=%d",
        mode,
        len(all_stats),
        files_changed,
        files_errored,
        total_seen,
        total_migrated,
        total_skipped,
    )
    return 0 if files_errored == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
