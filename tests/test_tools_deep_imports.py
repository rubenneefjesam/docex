# tests/test_tools_deep_imports.py
import sys
from pathlib import Path
import importlib, importlib.util
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def is_importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def test_tools_top_level_and_common_candidates():
    tools_dir = ROOT / "tools"
    if not tools_dir.exists():
        # no tools folder -> skip
        import pytest; pytest.skip("No tools/ directory")
    failed = []
    # try all immediate children (dir names)
    for entry in tools_dir.iterdir():
        if not entry.exists():
            continue
        # try import as package or module: tools.<name>
        candidate = f"tools.{entry.name}"
        if not is_importable(candidate):
            # try a common nested candidate patterns
            nested_try = [
                f"{candidate}.{entry.name}",
                f"{candidate}.coge",
                f"{candidate}.dogen",
                f"{candidate}.docex",
            ]
            if not any(is_importable(n) for n in nested_try):
                failed.append(candidate)
    assert not failed, "Some tools not importable or missing common nested modules: " + ", ".join(failed)
