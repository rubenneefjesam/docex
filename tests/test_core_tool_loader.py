# tests/test_core_tool_loader.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webapp.core import tool_loader

def test_call_first_callable_with_callable():
    assert tool_loader.call_first_callable(lambda: "ok") == "ok"

def test_load_tool_module_candidate_nonexistent():
    # should return None for non-existent candidates
    mod = tool_loader.load_tool_module_candidate("nonexistent", "this.module.does.not.exist", "")
    assert mod is None

def test_call_tool_module_like_object():
    class DummyMod:
        def run(self):
            return "ran"
    m = DummyMod()
    assert tool_loader.call_tool(m) == "ran"
