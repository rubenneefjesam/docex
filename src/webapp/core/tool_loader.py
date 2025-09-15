# src/webapp/core/tool_loader.py

import importlib
import streamlit as st

def call_tool(obj, name: str | None = None):
    """
    Call a callable or a module exposing run/app/main, with friendly UI errors.
    """
    if obj is None:
        st.error(f"{name or 'Tool'}: not available")
        return

    if callable(obj):
        return obj()

    for entry in ("run", "app", "main"):
        fn = getattr(obj, entry, None)
        if callable(fn):
            return fn()

    st.error(f"{name or 'Tool'}: geen entrypoint gevonden (run/app/main)")

def call_first_callable(candidate, name: str | None = None):
    """
    Accept a module object or a module path string, then call it.
    """
    if candidate is None:
        raise RuntimeError(f"{name or 'Tool'}: candidate is None")

    # If they passed a string, import it
    if isinstance(candidate, str):
        candidate = importlib.import_module(candidate)

    return call_tool(candidate, name)

def load_tool_module_candidate(human_name: str, *module_paths: str):
    """
    Try each import path in order; return the first successfully imported module.
    """
    for path in module_paths:
        if not path:
            continue
        try:
            return importlib.import_module(path)
        except ModuleNotFoundError:
            continue
        except Exception:
            # import error inside module—report in call_first_callable
            return importlib.import_module(path)

    # None succeeded
    st.error(f"{human_name}: kon geen module importeren uit {module_paths}")
    return None
