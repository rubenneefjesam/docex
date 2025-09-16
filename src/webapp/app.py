# src/webapp/app.py
from pathlib import Path
import sys, os, traceback
import streamlit as st

# --- Path safety net: zorg dat src/ op sys.path staat ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # .../docex
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
# ---------------------------------------------------------

from webapp.registry import ASSISTANTS
from webapp.components.sidebar import render_sidebar
from webapp.home.home import render as render_home
from webapp.home.info import render as render_info
from webapp.home.contact import render as render_contact

st.set_page_config(page_title="Docgen Suite", layout="wide")


def render_assistant_info(key: str):
    """Dynamisch de info-page van een assistant renderen (optioneel)."""
    module_path = f"webapp.assistants.{key}.info"
    try:
        mod = __import__(module_path, fromlist=["render"])
        render = getattr(mod, "render", None)
        if callable(render):
            render()
        else:
            st.header(f"{ASSISTANTS[key]['label']} — Info")
            st.write("Geen extra informatie beschikbaar.")
    except Exception as e:
        st.error(f"Kon info-module niet laden voor '{key}': {e}")


# ---- UI: sidebar keuzes ----
page, assistant_key, tool_key = render_sidebar(default_assistant="general_support")

if page == "Home":
    render_home()
elif page == "Info":
    render_info()
elif page == "Contact":
    render_contact()
else:
    # Assistenten-mode
    asst = ASSISTANTS.get(assistant_key)
    if not asst:
        st.warning("Kies een geldige assistant.")
        st.stop()

    tools = asst.get("tools", {})
    tool_keys = list(tools.keys())

    if not tool_key:
        # Alleen assistant gekozen → toon info
        render_assistant_info(assistant_key)
        st.stop()

    if tool_key not in tools:
        st.warning("Kies een geldige tool.")
        st.stop()

    tool_info = tools[tool_key]

    # === NIEUW: pak entrypoint via registry.resolver() ===
    try:
        entry = tool_info["resolver"]()  # levert callable (app/run) of raise-t
    except Exception as e:
        st.error(
            f"Kon entrypoint niet resolven voor {assistant_key}.{tool_key}:\n{e}"
        )
        st.code("".join(traceback.format_exc()))
        st.stop()

    # Run de tool binnen Streamlit-context
    try:
        entry()  # callable die de UI rendert
    except Exception:
        st.error(f"Fout bij uitvoeren van {assistant_key}.{tool_key}:")
        st.code("".join(traceback.format_exc()))
        # geen st.stop(); laat de user de fout zien


# ---- Optioneel: debug alleen met DEBUG_ENV=1 ----
if os.environ.get("DEBUG_ENV") == "1":
    st.sidebar.title("Environment debug")
    st.json({
        "sys.executable": sys.executable,
        "cwd": os.getcwd(),
        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV"),
        "assistants": list(ASSISTANTS.keys()),
    })
