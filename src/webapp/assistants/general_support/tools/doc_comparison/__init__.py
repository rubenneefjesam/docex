# src/webapp/assistants/general_support/tools/doc_comparison/__init__.py
from importlib import import_module
import pkgutil

_APP = None

def _pick(mod):
    if hasattr(mod, "app"):
        return mod.app
    if hasattr(mod, "run"):
        return mod.run
    return None

# Doorzoek hele 'webapp.assistants' boom naar modules met 'doc_comparison' in de naam
roots = ["webapp.assistants"]
for root in roots:
    try:
        pkg = import_module(root)
    except Exception:
        continue
    prefix = pkg.__name__ + "."
    for finder, name, ispkg in pkgutil.walk_packages(pkg.__path__, prefix):
        if "doc_comparison" in name.rsplit(".", 1)[-1]:
            try:
                mod = import_module(name)
                pick = _pick(mod)
                if pick:
                    _APP = pick
                    break
            except Exception:
                continue
    if _APP:
        break

if _APP is None:
    # fallback: een paar veelvoorkomende varianten
    for cand in [
        "webapp.assistants.general_assistant.tools.doc_comparison.doc_comparison",
        "webapp.assistants.general_assistant.tools.doc_comparison",
        "webapp.assistants.general_support.tools.doc_comparison.doc_comparison",
        "webapp.assistants.general_support.tools.doc_comparison",
    ]:
        try:
            mod = import_module(cand)
            pick = _pick(mod)
            if pick:
                _APP = pick
                break
        except Exception:
            pass

if _APP is None:
    raise ImportError("Doc Comparison: geen geschikte module gevonden met app()/run() binnen 'webapp.assistants'.")

def app():
    return _APP()

__all__ = ["app"]
