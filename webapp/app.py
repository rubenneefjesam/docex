# webapp/app.py

import sys
from pathlib import Path

# --- projectroot aan sys.path toevoegen ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
import importlib.util
import traceback

import streamlit as st


# Small helper to call a tool entrypoint defensively. Accepts either:
# - a callable (function), or
# - a module-like object exposing run/app/main functions.
def call_tool(obj, name: str | None = None):
    try:
        if obj is None:
            st.error(f"{name or 'Tool'}: not available")
            return
        # If obj itself is callable (function), call it
        if callable(obj):
            return obj()
        # If obj is a module-like object, prefer run/app/main
        for attr in ("run", "app", "main"):
            if hasattr(obj, attr) and callable(getattr(obj, attr)):
                return getattr(obj, attr)()
        st.error(f"{name or 'Tool'}: no callable entrypoint found (checked run/app/main)")
    except Exception as e:
        # Show exception in Streamlit UI and re-raise for logs
        try:
            st.exception(e)
        except Exception:
            pass
        raise


# Convenience wrapper that accepts either a module or a callable and tries to run it.
def call_first_callable(candidate, name: str | None = None):
    # if candidate is None -> error
    if candidate is None:
        raise RuntimeError(f"{name or 'Tool'}: candidate is None")
    # if it's a module path string, try to import it
    if isinstance(candidate, str):
        try:
            candidate = importlib.import_module(candidate)
        except Exception as e:
            raise
    # delegate to call_tool (which handles modules and callables)
    return call_tool(candidate, name)


# Try multiple module import candidates in order and return the first successfully imported module.
def load_tool_module_candidate(human_name: str, *module_candidates: str):
    """
    Example:
      load_tool_module_candidate("Document generator",
                                 "tools.plan_creator.dogen",
                                 "tools.plan_creator",
                                 "tools.doc_generator.docgen")
    Returns the imported module or None if none import.
    """
    for candidate in module_candidates:
        if not candidate:
            continue
        # quick spec check first (so we don't execute heavy package code unless needed)
        try:
            spec = importlib.util.find_spec(candidate)
        except Exception:
            spec = None
        if spec is None:
            # try fallback: if candidate is a package, sometimes find_spec fails if package has errors;
            # we'll still attempt to import and catch exceptions.
            try:
                mod = importlib.import_module(candidate)
                return mod
            except Exception:
                # continue to next candidate
                continue
        else:
            try:
                mod = importlib.import_module(candidate)
                return mod
            except Exception:
                # import failed (maybe missing deps) -> continue to next
                continue
    # nothing worked
    return None


# ===== Streamlit UI =====

st.set_page_config(page_title="Docgen Suite", layout="wide")

with st.sidebar:
    # logo (local)
    logo_path = Path(__file__).resolve().parent / "assets" / "beeldmerk.png"
    if logo_path.exists():
        st.markdown(
            f"<div style='text-align:center; padding:8px 0;'><img src='{logo_path.as_posix()}' width='140' alt='bedrijf-logo' style='max-width:100%; height:auto;' /></div>",
            unsafe_allow_html=True,
        )

    st.header("Assistent voor:")
    top_choice = st.radio(
        "Assistent voor:",
        ["General support", "Tender assistant", "Risk assistant", "Calculator assistant", "Legal assistant"],
        index=0,
        label_visibility="collapsed",
    )
    st.markdown("---")
    sub_choice = None

    if top_choice == "General support":
        st.subheader("Actieve tools")
        # detect which tools are available (do not raise if import fails)
        docgen_available = importlib.util.find_spec("tools.doc_generator") is not None or importlib.util.find_spec("tools.plan_creator") is not None
        coge_available = importlib.util.find_spec("tools.doc_comparison") is not None

        options = []
        if docgen_available:
            options.append("Document generator")
        if coge_available:
            options.append("Document comparison")

        if options:
            sub_choice = st.radio("Kies tool:", options, index=0)
        else:
            st.info("Geen tools geactiveerd voor General support.")
    else:
        st.info("Nog geen tools geconfigureerd voor deze assistant.")

    # Map the assistant/sub-choice to the new 'choice' used by the main page logic
    if top_choice == "General support":
        if sub_choice == "Document generator":
            choice = "Document generator"
        elif sub_choice == "Document comparison":
            choice = "Document comparison"
        else:
            choice = "Home"
    else:
        # show Home / placeholder for non-configured assistants
        choice = "Home"

# --- Main page routing ---
if choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de **Document generator-app**. Kies een tool via de sidebar.")

elif choice == "Informatie":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write("Info: **Document generator** = Document generator, **Document comparison** = compare (placeholder).")

elif choice == "Document generator":
    # Try likely module import candidates (most specific -> generic)
    docmod = load_tool_module_candidate(
        "Document generator",
        "tools.plan_creator.dogen",
        "tools.plan_creator",
        "tools.doc_generator.docgen",
        "tools.doc_generator",
    )
    if docmod:
        try:
            # call module's run/app/main or callable
            call_first_callable(docmod, "Document generator")
        except Exception as e:
            st.error(f"Fout bij starten Document generator: {e}")
            # show a short traceback in logs (not too verbose for UI)
            traceback.print_exc()
    else:
        st.error("Document generator module niet gevonden (controleer tools/doc_generator of tools/plan_creator)")

elif choice == "Document comparison":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>🔍 Document comparison</h1>", unsafe_allow_html=True)
    cogemod = load_tool_module_candidate(
        "Document comparison",
        "tools.doc_comparison.coge",
        "tools.doc_comparison",
    )
    if cogemod:
        try:
            call_first_callable(cogemod, "Document comparison")
        except Exception as e:
            st.error(f"Fout bij starten Document comparison: {e}")
            traceback.print_exc()
    else:
        st.error("Document comparison module niet gevonden (controleer tools/doc_comparison)")
