# tests/test_pages_modules.py
import sys
from pathlib import Path
import importlib
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def test_main_pages_have_render():
    modules = [
        "webapp.assistants.home",
        "webapp.assistants.info",
        "webapp.assistants.contact",
    ]
    for modname in modules:
        mod = importlib.import_module(modname)
        assert hasattr(mod, "render") and callable(getattr(mod, "render")), f"{modname} missing callable render()"
