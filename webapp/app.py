# webapp/app.py
# --- ensure project root on sys.path (MUST come first) ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
import importlib.util
import traceback
import streamlit as st

from webapp.components.sidebar import render_sidebar
from webapp.registry import ASSISTANTS

st.set_page_config(page_title="Docgen Suite", layout="wide")

# --- Robust import helper ---------------------------------------------------
def import_page_module(base_name):
    """
    Probeer meerdere import-namen, en als fallback laad module direct vanaf bestandspad:
    - webapp.assistants.<base_name>
    - assistants.<base_name>
    - webapp.assistants.<base_name>.<base_name>  (package met submodule)
    - fallback: laad webapp/assistants/<base_name>/__init__.py of webapp/assistants/<base_name>.py direct
    Retourneert module, Exception (bij import/runtime error), of None (niet gevonden).
    """
    candidates = [
        f"webapp.assistants.{base_name}",
        f"assistants.{base_name}",
        f"webapp.assistants.{base_name}.{base_name}",
        f"assistants.{base_name}.{base_name}",
        f"{base_name}",
    ]

    for cand in candidates:
        try:
            return importlib.import_module(cand)
        except ModuleNotFoundError:
            # niet gevonden onder deze naam — probeer volgende
            continue
        except Exception as e:
            # andere importfout (syntax, runtime) — geef terug zodat we de fout kunnen tonen
            return e

    # Fallback: probeer direct vanaf het bestandssysteem in webapp/assistants
    assistants_dir = Path(__file__).parent / "assistants"
    pkg_init = assistants_dir / base_name / "__init__.py"
    mod_file = assistants_dir / f"{base_name}.py"

    try:
        if pkg_init.exists():
            spec = importlib.util.spec_from_file_location(f"assistants.{base_name}", str(pkg_init))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        if mod_file.exists():
            spec = importlib.util.spec_from_file_location(f"assistants.{base_name}", str(mod_file))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception as e:
        return e

    # niets gevonden
    return None


def safe_import(module_path_or_basename):
    """
    Probeer eerst directe import (als dotted path). Anders behandel als basename
    en gebruik import_page_module. Retourneert module of Exception of None.
    """
    # If user passed a dotted module path, attempt direct import first.
    if "." in module_path_or_basename:
        try:
            return importlib.import_module(module_path_or_basename)
        except ModuleNotFoundError:
            # fallback to basename logic below
            pass
        except Exception as e:
            return e

    # fallback: extract basename and try flexible import
    base = module_path_or_basename.split(".")[-1]
    return import_page_module(base)


# Sidebar -> keuze ophalen (nu: main_menu, assistant, tool)
main_menu, assistant, tool = render_sidebar(default_assistant="general_support")

# small debug in sidebar to inspect runtime import ability of some pages
st.sidebar.markdown("### DEBUG: import checks")
debug_imports = {}
for name in ("home", "info", "contact", assistant or ""):
    if not name:
        continue
    res = safe_import(f"webapp.assistants.{name}")
    if res is None:
        debug_imports[name] = "NOT FOUND"
    elif isinstance(res, Exception):
        debug_imports[name] = f"IMPORT ERROR: {type(res).__name__}: {str(res)[:300]}"
    else:
        debug_imports[name] = {
            "DISPLAY_NAME": getattr(res, "DISPLAY_NAME", None),
            "IS_ASSISTANT": getattr(res, "IS_ASSISTANT", None),
            "has_render": callable(getattr(res, "r_
