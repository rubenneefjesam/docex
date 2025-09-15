# webapp/core/tool_loader.py
import importlib
import importlib.util
import streamlit as st

def call_tool(obj, name: str | None = None):
    """Call a callable or a module exposing run/app/main, with friendly UI errors."""
    try:
        if obj is None:
            st.error(f"{name or 'Tool'}: not available")
            return
        if callable(obj):
            return obj()
        for attr in ("run", "app", "main"):
            if hasattr(obj, attr) and callable(getattr(obj, attr)):
                return getattr(obj, attr)()
        st.error(f"{name or 'Tool'}: no callable entrypoint found (checked run/app/main)")
    except Exception as e:
        try:
            st.exception(e)
        except Exception:
            pass
        raise

def call_first_callable(candidate, name: str | None = None):
    """Accept a module object, a callable, or a module path string and try to run it."""
    if candidate is None:
        raise RuntimeError(f"{name or 'Tool'}: candidate is None")
    if isinstance(candidate, str):
        candidate = importlib.import_module(candidate)
    return call_tool(candidate, name)

def load_tool_module_candidate(human_name: str, *module_candidates: str):
    """
    Try multiple import paths; return the first successfully imported module or None.
    """
    for candidate in module_candidates:
        if not candidate:
            continue
        try:
            spec = importlib.util.find_spec(candidate)
        except Exception:
            spec = None
        if spec is None:
            try:
                mod = importlib.import_module(candidate)
                return mod
            except Exception:
                continue
        else:
            try:
                mod = importlib.import_module(candidate)
                return mod
            except Exception:
                continue
    return None
