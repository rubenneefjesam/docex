# tests/test_imports.py
import sys
import importlib
import importlib.util
from pathlib import Path
import pytest

# Zorg dat de projectroot op sys.path staat (zodat "import webapp" werkt)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def is_importable(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False

def test_webapp_package_importable():
    assert is_importable("webapp"), "webapp package is not importable (check PYTHONPATH/sys.path)"

def test_registry_pages_importable_and_have_render():
    registry_spec = importlib.util.find_spec("webapp.registry")
    assert registry_spec is not None, "webapp.registry not found"
    registry = importlib.import_module("webapp.registry")
    assistants = getattr(registry, "ASSISTANTS", None)
    assert isinstance(assistants, dict), "ASSISTANTS not found or wrong type in registry"

    failed = []
    for a_key, a_meta in assistants.items():
        tools = a_meta.get("tools", {})
        for t_key, t_meta in tools.items():
            page_mod = t_meta.get("page_module")
            if not page_mod:
                failed.append(f"{a_key}/{t_key}: no page_module configured")
                continue
            if not is_importable(page_mod):
                failed.append(f"{a_key}/{t_key}: module {page_mod} not importable")
                continue
            try:
                mod = importlib.import_module(page_mod)
            except Exception as e:
                failed.append(f"{a_key}/{t_key}: import error for {page_mod}: {e}")
                continue
            if not hasattr(mod, "render") or not callable(getattr(mod, "render")):
                failed.append(f"{a_key}/{t_key}: {page_mod} missing callable render()")
    if failed:
        pytest.fail("Page import/render failures:\n" + "\n".join(failed))
