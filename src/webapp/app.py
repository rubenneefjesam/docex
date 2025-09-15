# webapp/app.py
import sys
from pathlib import Path

# Zet project-root op sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import traceback
import streamlit as st

from webapp.components.sidebar import render_sidebar
from webapp.registry import ASSISTANTS

# Directe imports voor Home, Info en Contact
from webapp.home.home import render as render_home
from webapp.home.info import render as render_info
from webapp.home.contact import render as render_contact

# Tool-loader
from webapp.core.tool_loader import load_tool_module_candidate, call_first_callable

st.set_page_config(page_title="Docgen Suite", layout="wide")

# Sidebar keuzes ophalen
main_menu, assistant, tool = render_sidebar(default_assistant="general_support")

# Routing
if main_menu == "Home":
    render_home()

elif main_menu == "Info":
    render_info()

elif main_menu == "Contact":
    render_contact()

else:
    # Assistenten-modus
    # 1) Alleen assistant geselecteerd → toon diens info
    if assistant in ASSISTANTS and not tool:
        info_module_path = f"webapp.assistants.{assistant}.info"
        try:
            info_mod = __import__(info_module_path, fromlist=["render"])
            render = getattr(info_mod, "render", None)
            if callable(render):
                render()
            else:
                st.header(f"{ASSISTANTS[assistant]['label']} — Info")
                st.write("Geen description beschikbaar.")
        except Exception as e:
            st.error(f"Fout bij laden assistant-info:\n{e}")

    # 2) Assistant én tool geselecteerd → laad de tool
    elif assistant in ASSISTANTS and tool in ASSISTANTS[assistant]["tools"]:
        tool_meta = ASSISTANTS[assistant]["tools"][tool]
        candidates = tool_meta.get(
            "page_module_candidates",
            [tool_meta.get("page_module")]
        )

        mod = load_tool_module_candidate(tool_meta["label"], *candidates)
        try:
            call_first_callable(mod, tool_meta["label"])
        except Exception as e:
            st.error(f"Fout bij starten {tool_meta['label']}:\n{traceback.format_exc()}")

    else:
        # Ongeldige combinatie → terug naar Home
        st.warning("Ongeldige selectie. Ga terug naar Home of Assistenten.")
        render_home()
