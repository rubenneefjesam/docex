# tests/test_registry_files.py
import sys
from pathlib import Path
import importlib, importlib.util
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webapp import registry

def module_to_path(module_name: str) -> Path:
    parts = module_name.split(".")
    return ROOT.joinpath(*parts).with_suffix(".py")

def test_registry_page_files_exist():
    missing = []
    for a_key, a_meta in registry.ASSISTANTS.items():
        for t_key, t_meta in a_meta.get("tools", {}).items():
            page_mod = t_meta.get("page_module")
            if not page_mod:
                missing.append(f"{a_key}/{t_key}: no page_module configured")
                continue
            p = module_to_path(page_mod)
            if not p.exists():
                missing.append(f"{a_key}/{t_key}: page_module {page_mod} -> file missing ({p})")
    assert not missing, "Missing page files:\n" + "\n".join(missing)
