# proxy naar de échte comparison tool in general_assistant
from importlib import import_module

_CANDIDATES = [
    "webapp.assistants.general_assistant.tools.doc_comparison.doc_comparison",
    "webapp.assistants.general_assistant.tools.doc_comparison",
]

_app = None
for path in _CANDIDATES:
    try:
        mod = import_module(path)
        if hasattr(mod, "app"):
            _app = mod.app
            break
        if hasattr(mod, "run"):
            _app = mod.run
            break
    except Exception:
        continue

if _app is None:
    raise ImportError(f"Doc Comparison: kon geen module importeren uit {_CANDIDATES!r}")

def app():
    return _app()

__all__ = ["app"]
