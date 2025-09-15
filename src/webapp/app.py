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
            continue
        except Exception as e:
            return e

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

    return None


def safe_import(module_path_or_basename):
    """
    Probeer direct import, anders basename import via import_page_module.
    """
    if "." in module_path_or_basename:
        try:
            return importlib.import_module(module_path_or_basename)
        except ModuleNotFoundError:
            pass
        except Exception as e:
            return e
    return import_page_module(module_path_or_basename.split('.')[-1])

# Sidebar -> keuzes
main_menu, assistant, tool = render_sidebar(default_assistant="general_support")

# Route based on main_menu
if main_menu == "Home":
    try:
        home_mod = safe_import("webapp.assistants.home")
        if isinstance(home_mod, Exception) or home_mod is None:
            raise home_mod or ModuleNotFoundError()
        render_home = getattr(home_mod, "render", None)
        if callable(render_home):
            render_home()
        else:
            st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
            st.write("Welkom bij de Document generator-app.")
    except Exception:
        st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
        st.write("Welkom bij de Document generator-app.")
        st.error(f"Kon home pagina niet laden:\n{traceback.format_exc()[:500]}")

elif main_menu == "Info":
    try:
        info_mod = safe_import("webapp.home.info")
        if isinstance(info_mod, Exception) or info_mod is None:
            raise info_mod or ModuleNotFoundError()
        render_info = getattr(info_mod, "render", None)
        if callable(render_info):
            render_info()
        else:
            st.header("Info")
            st.write("Informatiepagina")
    except Exception:
        st.header("Info")
        st.write("Informatiepagina")
        st.error(f"Kon info pagina niet laden:\n{traceback.format_exc()[:500]}")

elif main_menu == "Contact":
    try:
        contact_mod = safe_import("webapp.home.contact")
        if isinstance(contact_mod, Exception) or contact_mod is None:
            raise contact_mod or ModuleNotFoundError()
        render_contact = getattr(contact_mod, "render", None)
        if callable(render_contact):
            render_contact()
        else:
            st.header("Contact")
            st.write("Contactpagina")
    except Exception:
        st.header("Contact")
        st.write("Contactpagina")
        st.error(f"Kon contact pagina niet laden:\n{traceback.format_exc()[:500]}")

else:
    # Assistenten-mode
    if assistant in ASSISTANTS and (not tool or tool == ""):
        # Toon assistant-specifieke info
        try:
            info_mod = safe_import(f"webapp.assistants.{assistant}.info")
            if isinstance(info_mod, Exception) or info_mod is None:
                raise info_mod or ModuleNotFoundError()
            render_info = getattr(info_mod, "render", None)
            if callable(render_info):
                render_info()
            else:
                st.header(f"{ASSISTANTS[assistant]['label']} — Info")
                # Fallback describe
                info_func = getattr(info_mod, f"get_{assistant}_info", None)
                if callable(info_func):
                    data = info_func()
                    st.write(data.get("description", "Geen extra info beschikbaar."))
                else:
                    st.write("Geen extra info beschikbaar.")
        except Exception:
            st.header(f"{ASSISTANTS[assistant]['label']} — Info")
            st.error(f"Kon info-module voor {assistant} niet laden:\n{traceback.format_exc()[:500]}")

    elif assistant not in ASSISTANTS or not tool:
        # Fallback placeholder
        home_mod = safe_import("webapp.assistants.home")
        render_home = getattr(home_mod, "render", None)
        if callable(render_home):
            render_home()
            st.info("Kies bovenin een assistent en daarna een tool om te starten.")
        else:
            st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
            st.write("Kies een tool via de sidebar.")

    else:
        # Toon gekozen tool
        page_module_path = ASSISTANTS[assistant]["tools"][tool]["page_module"]
        try:
            try:
                mod = importlib.import_module(page_module_path)
            except Exception:
                mod = safe_import(page_module_path)
            if isinstance(mod, Exception) or mod is None:
                raise mod or ModuleNotFoundError()
        except Exception:
            st.error(f"Kon pagina-module niet laden: `{page_module_path}`\n{traceback.format_exc()[:500]}")
        else:
            render = getattr(mod, "render", None)
            if callable(render):
                render()
            else:
                st.error(f"Pagina `{page_module_path}` heeft geen render() functie.")
