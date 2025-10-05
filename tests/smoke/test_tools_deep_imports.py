# tests/smoke/test_tools_deep_imports.py
import importlib
import importlib.util
import sys
from pathlib import Path
import os
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOOLS_DIR = ROOT / "tools"

def is_importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def test_tools_top_level_and_common_candidates():
    if not TOOLS_DIR.exists() or not TOOLS_DIR.is_dir():
        pytest.skip("No tools/ directory")
    failed = []

    for entry in sorted(TOOLS_DIR.iterdir(), key=lambda p: p.name):
        # skip non .py files and dirs? We'll handle dirs and .py files separately
        if entry.name.startswith("."):
            continue

        # If it's a file like smoke_import.py, skip known scripts (heuristic)
        if entry.is_file() and entry.suffix == ".py":
            stem = entry.stem
            # skip test/helper scripts or explicit smoke scripts
            if stem.startswith("smoke") or stem in ("smoke_import", "smoke-import", "run_smoke"):
                continue
            # skip executable scripts
            if os.access(entry, os.X_OK):
                continue
            candidate = f"tools.{stem}"
            try:
                if not is_importable(candidate):
                    # try loading by file location (non-package) - but don't execute arbitrary scripts
                    failed.append(f"{candidate}: not importable")
                    continue
                # attempt import to catch runtime import errors
                try:
                    importlib.import_module(candidate)
                except SystemExit as e:
                    failed.append(f"{candidate}: SystemExit({e.code}) on import (skipped?)")
                except Exception as e:
                    failed.append(f"{candidate}: import error: {type(e).__name__}: {e}")
            except Exception as e:
                failed.append(f"{candidate}: unexpected error: {e}")

        # If it's a directory, try importing the package and some common nested modules
        elif entry.is_dir():
            pkg_name = f"tools.{entry.name}"
            try:
                if not is_importable(pkg_name):
                    failed.append(f"{pkg_name}: package not importable")
                    continue
                try:
                    importlib.import_module(pkg_name)
                except SystemExit as e:
                    failed.append(f"{pkg_name}: SystemExit({e.code}) on import")
                except Exception as e:
                    # record the import exception but keep going
                    failed.append(f"{pkg_name}: import error: {type(e).__name__}: {e}")
                    # continue to try nested candidates nonetheless
                # try some common nested candidates if package imported ok
                nested_candidates = [
                    f"{pkg_name}.coge",
                    f"{pkg_name}.dogen",
                    f"{pkg_name}.docgen",
                    f"{pkg_name}.steps",
                    f"{pkg_name}.docex",
                ]
                for nc in nested_candidates:
                    try:
                        if importlib.util.find_spec(nc) is not None:
                            try:
                                importlib.import_module(nc)
                            except SystemExit as e:
                                failed.append(f"{nc}: SystemExit({e.code}) on import")
                            except Exception as e:
                                failed.append(f"{nc}: import error: {type(e).__name__}: {e}")
                    except Exception:
                        # ignore lookup errors for nested candidates
                        pass

            except Exception as e:
                failed.append(f"{pkg_name}: unexpected error: {e}")

    if failed:
        pytest.fail("Tools import issues:\n" + "\n".join(failed))
