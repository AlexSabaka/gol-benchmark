#!/usr/bin/env python3
"""One-time migration: consolidate runtime files under ``data/``.

Moves:
  - testsets/              → data/testsets/
  - results/results_*.json.gz + results/judge_*.json.gz → data/results/
  - results/*_annotations.json.gz → data/annotations/{stem without suffix}.json.gz
  - results/partial_*.json.gz → data/jobs/partial/{job_id}.json.gz
  - reports/               → data/reports/
  - jobs.json              → one file per job at data/jobs/<id>.json
  - gol_eval.log           → data/logs/gol_eval.log

Idempotent: skips files whose destinations already exist. Safe to re-run.

Usage::

    python scripts/migrate_data_layout.py --dry-run   # preview planned moves
    python scripts/migrate_data_layout.py             # execute
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data"

OLD_TESTSETS = PROJECT_ROOT / "testsets"
OLD_RESULTS = PROJECT_ROOT / "results"
OLD_REPORTS = PROJECT_ROOT / "reports"
OLD_JOBS_FILE = PROJECT_ROOT / "jobs.json"
OLD_LOG = PROJECT_ROOT / "gol_eval.log"

NEW_TESTSETS = DATA_ROOT / "testsets"
NEW_RESULTS = DATA_ROOT / "results"
NEW_ANNOTATIONS = DATA_ROOT / "annotations"
NEW_REPORTS = DATA_ROOT / "reports"
NEW_JOBS = DATA_ROOT / "jobs"
NEW_PARTIAL = NEW_JOBS / "partial"
NEW_LOGS = DATA_ROOT / "logs"


class Stats:
    def __init__(self) -> None:
        self.moved = 0
        self.skipped = 0
        self.errors = 0

    def summary(self) -> str:
        return f"{{moved: {self.moved}, skipped: {self.skipped}, errors: {self.errors}}}"


def _move(src: Path, dst: Path, *, dry_run: bool, stats: Stats) -> None:
    if not src.exists():
        return
    if dst.exists():
        print(f"  SKIP  {src.relative_to(PROJECT_ROOT)} → {dst.relative_to(PROJECT_ROOT)} (target exists)")
        stats.skipped += 1
        return
    print(f"  MOVE  {src.relative_to(PROJECT_ROOT)} → {dst.relative_to(PROJECT_ROOT)}")
    if dry_run:
        stats.moved += 1
        return
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        stats.moved += 1
    except Exception as exc:
        print(f"  ERROR {src}: {exc}", file=sys.stderr)
        stats.errors += 1


def _move_tree(src: Path, dst: Path, *, dry_run: bool, stats: Stats) -> None:
    """Move each file inside `src` into `dst`, preserving filenames."""
    if not src.exists() or not src.is_dir():
        return
    for child in sorted(src.iterdir()):
        _move(child, dst / child.name, dry_run=dry_run, stats=stats)


def migrate_testsets(dry_run: bool, stats: Stats) -> None:
    print("[testsets]")
    _move_tree(OLD_TESTSETS, NEW_TESTSETS, dry_run=dry_run, stats=stats)


def migrate_results_and_annotations(dry_run: bool, stats: Stats) -> None:
    """Split old ``results/`` into results/, annotations/, and partials."""
    print("[results / annotations / partials]")
    if not OLD_RESULTS.exists():
        return
    for child in sorted(OLD_RESULTS.iterdir()):
        name = child.name
        if child.is_dir():
            # Recurse one level — some multi-model runs store results in subdirs.
            sub_dst = NEW_RESULTS / name
            print(f"  SUBDIR {child.relative_to(PROJECT_ROOT)} → {sub_dst.relative_to(PROJECT_ROOT)}")
            for grandchild in sorted(child.iterdir()):
                _route_result_file(grandchild, sub_dst, dry_run=dry_run, stats=stats)
            # Remove empty subdir after move.
            if not dry_run:
                try:
                    child.rmdir()
                except OSError:
                    pass
            continue
        _route_result_file(child, NEW_RESULTS, dry_run=dry_run, stats=stats)


def _route_result_file(child: Path, results_dst: Path, *, dry_run: bool, stats: Stats) -> None:
    name = child.name
    if name.endswith("_annotations.json.gz"):
        # Strip the suffix — new layout uses the results stem directly.
        stem = name[: -len("_annotations.json.gz")]
        dst = NEW_ANNOTATIONS / f"{stem}.json.gz"
        _move(child, dst, dry_run=dry_run, stats=stats)
    elif name.startswith("partial_") and name.endswith(".json.gz"):
        # partial_<job_id>.json.gz → data/jobs/partial/<job_id>.json.gz
        job_id = name[len("partial_"): -len(".json.gz")]
        dst = NEW_PARTIAL / f"{job_id}.json.gz"
        _move(child, dst, dry_run=dry_run, stats=stats)
    elif name.startswith("results_") and name.endswith(".json.gz"):
        _move(child, results_dst / name, dry_run=dry_run, stats=stats)
    elif name.startswith("judge_") and name.endswith(".json.gz"):
        _move(child, results_dst / name, dry_run=dry_run, stats=stats)
    else:
        # Unknown file — move verbatim into results/ so nothing is lost.
        _move(child, results_dst / name, dry_run=dry_run, stats=stats)


def migrate_reports(dry_run: bool, stats: Stats) -> None:
    print("[reports]")
    _move_tree(OLD_REPORTS, NEW_REPORTS, dry_run=dry_run, stats=stats)


def migrate_log(dry_run: bool, stats: Stats) -> None:
    print("[log]")
    _move(OLD_LOG, NEW_LOGS / OLD_LOG.name, dry_run=dry_run, stats=stats)


def migrate_jobs(dry_run: bool, stats: Stats) -> None:
    """Explode jobs.json into one file per job."""
    print("[jobs]")
    if not OLD_JOBS_FILE.exists():
        return
    try:
        with OLD_JOBS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"  ERROR reading {OLD_JOBS_FILE}: {exc}", file=sys.stderr)
        stats.errors += 1
        return
    jobs = data.get("jobs") or {}
    if not jobs:
        print(f"  SKIP  {OLD_JOBS_FILE.name} (no jobs to migrate)")
        return

    # Write per-job files, then archive the monolithic file.
    for job_id, record in jobs.items():
        if not job_id or "/" in job_id or "\\" in job_id:
            print(f"  ERROR unsafe job id: {job_id!r}", file=sys.stderr)
            stats.errors += 1
            continue
        dst = NEW_JOBS / f"{job_id}.json"
        if dst.exists():
            print(f"  SKIP  job {job_id} (target exists)")
            stats.skipped += 1
            continue
        print(f"  WRITE {dst.relative_to(PROJECT_ROOT)}")
        if not dry_run:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                with dst.open("w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2, default=str)
                stats.moved += 1
            except Exception as exc:
                print(f"  ERROR writing {dst}: {exc}", file=sys.stderr)
                stats.errors += 1
        else:
            stats.moved += 1

    # Archive the old monolithic file so we don't re-migrate on rerun.
    archive = OLD_JOBS_FILE.with_suffix(".json.migrated")
    print(f"  ARCHIVE {OLD_JOBS_FILE.name} → {archive.name}")
    if not dry_run:
        try:
            OLD_JOBS_FILE.rename(archive)
        except OSError as exc:
            print(f"  ERROR archiving jobs.json: {exc}", file=sys.stderr)
            stats.errors += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without executing.",
    )
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "EXECUTE"
    print(f"== Migrating runtime layout to data/ ({mode}) ==")
    print(f"  project root: {PROJECT_ROOT}")
    print(f"  data root:    {DATA_ROOT}")
    print()

    # Create target directories up-front (safe either way — JobStore and
    # WebConfig also create them on app startup).
    if not args.dry_run:
        for d in (NEW_TESTSETS, NEW_RESULTS, NEW_ANNOTATIONS, NEW_REPORTS,
                  NEW_JOBS, NEW_PARTIAL, NEW_LOGS):
            d.mkdir(parents=True, exist_ok=True)

    stats = Stats()
    migrate_testsets(args.dry_run, stats)
    migrate_results_and_annotations(args.dry_run, stats)
    migrate_reports(args.dry_run, stats)
    migrate_jobs(args.dry_run, stats)
    migrate_log(args.dry_run, stats)

    print()
    print(f"== Summary: {stats.summary()} ==")
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
