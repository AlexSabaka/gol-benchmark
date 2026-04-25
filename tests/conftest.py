"""Test-suite-wide fixtures & sandboxing.

Sets ``GOL_DATA_ROOT`` to a per-session tempdir before any ``src.web``
modules load, so the SQLite DB + legacy-file migrators created inside
``src.web.app`` run against a throwaway sandbox instead of the real
``data/`` directory.
"""
from __future__ import annotations

import os
import tempfile

# Must be set before any ``from src.web...`` import resolves the
# ``web_config`` singleton. pytest imports conftest.py before collecting
# test modules, so this is early enough.
if "GOL_DATA_ROOT" not in os.environ:
    os.environ["GOL_DATA_ROOT"] = tempfile.mkdtemp(prefix="gol_eval_test_")
