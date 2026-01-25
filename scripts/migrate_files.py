#!/usr/bin/env python3
"""
Migration script to organize existing benchmark files.

This script helps migrate from the old scattered directory structure
to the new organized PathManager-based structure.
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.path_manager import get_path_manager


def migrate_files(dry_run=True):
    """
    Migrate existing files to new directory structure.
    
    Args:
        dry_run: If True, only show what would be done without making changes
    """
    path_mgr = get_path_manager()
    root = Path.cwd()
    
    print("=" * 70)
    print("File Migration Script")
    print("=" * 70)
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be moved")
    else:
        print("⚠️  LIVE MODE - Files will be moved!")
    print()
    
    # Collect files to migrate
    migrations = []
    
    # 1. Find scattered results directories
    for results_dir in root.glob("results_*"):
        if results_dir.is_dir():
            print(f"Found old results directory: {results_dir.name}")
            for result_file in results_dir.glob("*.json.gz"):
                new_path = path_mgr.RESULTS_RUNS_DIR / result_file.name
                migrations.append((result_file, root / new_path, "result"))
    
    # 2. Find results files in root results/ without subdirectory
    results_root = root / "results"
    if results_root.exists():
        for result_file in results_root.glob("*.json.gz"):
            if result_file.is_file():
                new_path = path_mgr.RESULTS_RUNS_DIR / result_file.name
                migrations.append((result_file, root / new_path, "result"))
        
        for result_file in results_root.glob("*.csv"):
            if result_file.is_file():
                new_path = path_mgr.RESULTS_RUNS_DIR / result_file.name
                migrations.append((result_file, root / new_path, "result"))
    
    # 3. Find scattered benchmark_configs
    old_configs_dir = root / "benchmark_configs"
    if old_configs_dir.exists():
        print(f"Found old config directory: benchmark_configs")
        for config_file in old_configs_dir.glob("*.yaml"):
            new_path = path_mgr.CONFIG_TESTSETS_DIR / config_file.name
            migrations.append((config_file, root / new_path, "config"))
    
    # 4. Find scattered testsets in configs/
    old_testsets = root / "configs"
    if old_testsets.exists():
        for testset_file in old_testsets.glob("testset_*.json.gz"):
            new_path = path_mgr.TESTSETS_DIR / testset_file.name
            migrations.append((testset_file, root / new_path, "testset"))
    
    # Display migration plan
    print()
    print("=" * 70)
    print("Migration Plan")
    print("=" * 70)
    print()
    
    if not migrations:
        print("✓ No files need migration!")
        print()
        return
    
    by_type = {}
    for src, dst, file_type in migrations:
        by_type.setdefault(file_type, []).append((src, dst))
    
    for file_type, files in by_type.items():
        print(f"\n{file_type.upper()} FILES ({len(files)}):")
        for src, dst in files[:5]:  # Show first 5
            print(f"  {src.relative_to(root)} → {dst.relative_to(root)}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
    
    print()
    print(f"Total: {len(migrations)} files to migrate")
    print()
    
    # Execute migration
    if not dry_run:
        response = input("Proceed with migration? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
        
        print()
        print("Migrating files...")
        moved = 0
        failed = 0
        
        for src, dst, file_type in migrations:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                moved += 1
                print(f"✓ Moved: {src.name}")
            except Exception as e:
                failed += 1
                print(f"✗ Failed: {src.name} - {e}")
        
        print()
        print(f"Migration complete: {moved} moved, {failed} failed")
        
        # Cleanup empty directories
        print()
        print("Cleaning up empty directories...")
        for results_dir in root.glob("results_*"):
            if results_dir.is_dir() and not any(results_dir.iterdir()):
                results_dir.rmdir()
                print(f"✓ Removed empty: {results_dir.name}")
        
        if old_configs_dir.exists() and not any(old_configs_dir.iterdir()):
            old_configs_dir.rmdir()
            print(f"✓ Removed empty: benchmark_configs")
    
    else:
        print()
        print("To execute migration, run with --live flag:")
        print(f"  python {Path(__file__).name} --live")


def show_directory_structure():
    """Display the new directory structure."""
    print()
    print("=" * 70)
    print("New Directory Structure")
    print("=" * 70)
    print()
    print("workspace/")
    print("├── configs/")
    print("│   └── testsets/           # YAML configs")
    print("├── testsets/               # Generated test sets")
    print("├── results/")
    print("│   ├── runs/               # Test execution results")
    print("│   └── reports/            # Analysis reports")
    print("└── .benchmark_metadata/    # Run tracking")
    print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate benchmark files to new organized structure"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute migration (default is dry-run)"
    )
    parser.add_argument(
        "--show-structure",
        action="store_true",
        help="Show new directory structure"
    )
    
    args = parser.parse_args()
    
    if args.show_structure:
        show_directory_structure()
        return
    
    migrate_files(dry_run=not args.live)


if __name__ == "__main__":
    main()
