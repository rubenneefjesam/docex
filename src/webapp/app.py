# src/webapp/app.py
from pathlib import Path
import sys
import os
import traceback
import streamlit as st

# --- Zorg dat src/ op sys.path staat (veilig voor verschillende runners) ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../docex
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
# --------------------------------------------------------------------------

from webapp.registry import ASSISTANTS
from webapp.components.sidebar import render_sidebar
from webapp.home.home import render as render_home
from webapp.home.info import render as render_info
from webapp.home.contact import render as render_contact

st.set_page_config(page_title="Docgen Suite", layout="wide")


def render_assistant_info(key: str) -> None:
    """Render de info-pagina van een assistant als die bestaat, anders een fallback."""
    module_path = f"webapp.assistants.{key}.info"
    try:
        mod = __import__(module_path, fromlist=["render"])
        render_fn = getattr(mod, "render", None)
        if callable(render_fn):
            render_fn()
        else:
            st.header(f"{ASSISTANTS[key]['label']} — Info")
            st.write("Geen extra informatie beschikbaar.")
    except Exception as e:
        st.error(f"Kon info-module niet laden voor '{key}': {e}")


# --- UI flow ---
page, assistant_key, tool_key = render_sidebar(default_assistant="general_support")

if page == "Home":
    render_home()

elif page == "Info":
    render_info()

elif page == "Contact":
    render_contact()

elif page == "Assistenten":
    # render_sidebar() garandeert dat assistant_key geldig is
    if tool_key:
        tool_info = ASSISTANTS[assistant_key]["tools"][tool_key]
        try:
            entry = tool_info["resolver"]()  # haalt 'app' (of 'run') uit het package
        except Exception as e:
            st.error(
                f"Kon entrypoint niet resolven voor {assistant_key}.{tool_key}:\n{e}"
            )
            st.code("".join(traceback.format_exc()))
        else:
            try:
                entry()  # voer de Streamlit-tool uit
            except Exception:
                st.error(f"Fout bij uitvoeren van {assistant_key}.{tool_key}:")
                st.code("".join(traceback.format_exc()))
    else:
        # Alleen assistant gekozen → toon de info van die assistant
        render_assistant_info(assistant_key)

# --- Optioneel: debug-paneel alleen bij DEBUG_ENV=1 ---
if os.environ.get("DEBUG_ENV") == "1":
    st.sidebar.title("Environment debug")
    st.json(
        {
            "sys.executable": sys.executable,
            "cwd": os.getcwd(),
            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV"),
            "assistants": list(ASSISTANTS.keys()),
        }
    )
