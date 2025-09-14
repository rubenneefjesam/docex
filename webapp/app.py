import streamlit as st
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any

# -----------------------
# Config + defaults
# -----------------------
st.set_page_config(page_title="Document generator-app", layout="wide")
st.session_state.setdefault("main_nav", "Home")
st.session_state.setdefault("assistant_nav", None)
st.session_state.setdefault("tool_nav", None)

RESET_ASSISTANT_ON_LEAVE = True

# -----------------------
# Safe helpers (zorg dat deze vóór het gebruik staan)
# -----------------------
def safe_index(options, value, default=0):
    """Veilige index lookup: return default als value niet in options staat."""
    try:
        return options.index(value)
    except Exception:
        return default

# -----------------------
# Dynamic discovery for assistants (files and packages)
# -----------------------
ASSISTANTS_DIR = Path(__file__).parent / "assistants"

def discover_assistants() -> Dict[str, Dict[str, Any]]:
    """
    Discover assistant modules in webapp/assistants.
    Only include modules where IS_ASSISTANT is True.
    Supports:
      - single-file assistants (assistants/foo.py)
      - package assistants (assistants/foo/__init__.py)
    """
    assistants: Dict[str, Dict[str, Any]] = {}
    if not ASSISTANTS_DIR.exists():
        return assistants

    def try_load(path: Path, key: str):
        try:
            spec = importlib.util.spec_from_file_location(f"assistants.{key}", str(path))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[f"assistants.{key}"] = mod
            spec.loader.exec_module(mod)
            # must explicitly mark as assistant
            is_assistant = getattr(mod, "IS_ASSISTANT", False)
            if not is_assistant:
                return None
            display = getattr(mod, "DISPLAY_NAME", key)
            tools = getattr(mod, "TOOLS", [])
            return {"module": mod, "display": display, "tools": tools}
        except Exception as e:
            st.warning(f"Kon assistant '{path.name}' niet laden: {e}")
            return None

    # 1) python files directly in the folder
    for py in sorted(ASSISTANTS_DIR.glob("*.py")):
        if py.name.startswith("_") or py.name == "validate_assistants.py":
            continue
        key = py.stem
        meta = try_load(py, key)
        if meta:
            assistants[key] = meta

    # 2) directories (packages) with __init__.py
    for d in sorted([p for p in ASSISTANTS_DIR.iterdir() if p.is_dir()]):
        init_py = d / "__init__.py"
        if not init_py.exists():
            continue
        key = d.name
        meta = try_load(init_py, key)
        if meta:
            assistants[key] = meta

    return assistants

# Discover assistants at startup
ASSISTANTS = discover_assistants()  # dict

# Map display -> key for lookup
DISPLAY_TO_KEY = {v["display"]: k for k, v in ASSISTANTS.items()}

# -----------------------
# Sidebar (navigation)
# -----------------------
PAGES = ["Home", "Assistants", "Info", "Contact"]
with st.sidebar:
    st.markdown("## Hoofdmenu")
    page_idx = safe_index(PAGES, st.session_state.get("main_nav", "Home"))
    page = st.radio("", options=PAGES, index=page_idx, key="main_nav")
    st.markdown("---")

    if page == "Assistants":
        displays = [v["display"] for v in ASSISTANTS.values()]
        if not displays:
            st.info("Geen assistenten gevonden in `assistants/`. Maak eerst modules aan.")
            st.stop()

        # ensure a sensible default in session_state
        if st.session_state.get("assistant_nav") not in displays:
            st.session_state["assistant_nav"] = displays[0]

        ass_idx = safe_index(displays, st.session_state["assistant_nav"])
        selected_display = st.radio("### Assistent voor:", options=displays, index=ass_idx, key="assistant_nav")

        # load tools for this assistant
        assistant_key = DISPLAY_TO_KEY[selected_display]
        assistant_meta = ASSISTANTS[assistant_key]
        tools_for_assistant = assistant_meta.get("tools", [])

        # default tool
        if st.session_state.get("tool_nav") not in tools_for_assistant:
            st.session_state["tool_nav"] = tools_for_assistant[0] if tools_for_assistant else None

        if tools_for_assistant:
            st.markdown("### Kies tool:")
            tool_idx = safe_index(tools_for_assistant, st.session_state["tool_nav"])
            selected_tool = st.radio("", options=tools_for_assistant, index=tool_idx, key="tool_nav")
        else:
            st.info("Deze assistent heeft (nog) geen tools.")
            st.session_state["tool_nav"] = None
    else:
        # Not on Assistants page: optionally reset
        if RESET_ASSISTANT_ON_LEAVE:
            st.session_state["assistant_nav"] = None
            st.session_state["tool_nav"] = None

# -----------------------
# Render helpers
# -----------------------
def render_header():
    col1, col2 = st.columns([1, 6])
    with col1:
        st.write("")  # ruimte voor logo/image
    with col2:
        st.markdown("<h1 style='text-align:center'>Document generator-app</h1>", unsafe_allow_html=True)
        st.write("Kies links in het menu een pagina en, bij Assistants, een assistent en tool.")

def render_home():
    render_header()
    st.title("🏠 Home")
    st.write("Welkom bij de app. Gebruik het menu links.")

def render_info():
    render_header()
    st.title("ℹ️ Info")
    st.write("- Versie: 1.0.0")

def render_contact():
    render_header()
    st.title("📬 Contact")
    st.write("support@example.com")

# -----------------------
# Dispatcher
# -----------------------
current_page = st.session_state.get("main_nav", "Home")
if current_page == "Home":
    render_home()
elif current_page == "Info":
    render_info()
elif current_page == "Contact":
    render_contact()
elif current_page == "Assistants":
    sel_display = st.session_state.get("assistant_nav")
    if not sel_display:
        st.info("Kies een assistent in de sidebar.")
        st.stop()

    sel_key = DISPLAY_TO_KEY.get(sel_display)
    if not sel_key:
        st.error("Geselecteerde assistent niet gevonden (key error).")
        st.stop()

    meta = ASSISTANTS[sel_key]
    module = meta["module"]
    selected_tool = st.session_state.get("tool_nav")

    render_func = getattr(module, "render", None)
    if not callable(render_func):
        st.error(f"Assistant '{meta['display']}' heeft geen render(module) functie.")
    else:
        try:
            render_func(selected_tool)
        except Exception as e:
            st.error(f"Fout in render van assistant {meta['display']}: {e}")
else:
    st.error("Onbekende pagina geselecteerd.")
