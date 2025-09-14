# tests/test_imports.py
import importlib
import importlib.util
import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def is_importable(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False

def test_webapp_package_importable():
    assert is_importable("webapp"), "webapp package is not importable"

def test_registry_pages_importable_and_have_render():
    # import registry lazily so test file can run from project root
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
            mod = importlib.import_module(page_mod)
            if not hasattr(mod, "render") or not callable(getattr(mod, "render")):
                failed.append(f"{a_key}/{t_key}: {page_mod} missing callable render()")
    if failed:
        pytest.fail("Page import/render failures:\n" + "\n".join(failed))

def test_tools_top_level_importable():
    """
    Smoke-check: attempt to import each top-level package under ./tools as 'tools.<name>'.
    This is permissive — if a tools/ dir doesn't exist or is empty, the test passes.
    """
    tools_dir = ROOT / "tools"
    if not tools_dir.exists() or not tools_dir.is_dir():
        pytest.skip("No tools/ directory found — skipping tools import check")

    names = [p.name for p in tools_dir.iterdir() if p.is_dir() or (p.is_file() and p.suffix == ".py")]
    if not names:
        pytest.skip("tools/ exists but contains no packages/modules — skipping")

    failed = []
    for name in names:
        mod_name = f"tools.{name}"
        if not is_importable(mod_name):
            # sometimes tools are nested, still try import of nested candidates
            try:
                importlib.import_module(mod_name)
            except Exception as e:
                failed.append(f"{mod_name}: import error: {e}")
    if failed:
        pytest.fail("Tools import failures:\n" + "\n".join(failed))
