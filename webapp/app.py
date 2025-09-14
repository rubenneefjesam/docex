# webapp/app.py
import importlib
import traceback
from pathlib import Path
import streamlit as st

# Helpers
def safe_index(seq, value, default=0):
    try:
        return list(seq).index(value)
    except ValueError:
        return default

def discover_assistants():
    """Discover modules/packages under webapp/assistants without importing package __init__ side-effects."""
    assistants_dir = Path(__file__).parent / "assistants"
    results = {}
    for entry in sorted(assistants_dir.iterdir()):
        if entry.name.startswith("_"):
            continue
        # skip tools / helpers directories accidentally left here
        if entry.is_dir():
            # package: try import webapp.assistants.<name>
            module_name = f"webapp.assistants.{entry.name}"
        elif entry.is_file() and entry.suffix == ".py":
            if entry.name == "__init__.py":
                continue
            module_name = f"webapp.assistants.{entry.stem}"
        else:
            continue

        try:
            mod = importlib.import_module(module_name)
            results[entry.name if entry.is_dir() else entry.stem] = mod
        except Exception as e:
            # record the error module as None; we will show an error later if needed
            results[entry.name if entry.is_dir() else entry.stem] = e
    return results

def import_page_module(base_name):
    """Try importing a page module: either webapp.assistants.<base_name> or webapp.assistants.<base_name>.<base_name>."""
    candidates = [
        f"webapp.assistants.{base_name}",
        f"webapp.assistants.{base_name}.{base_name}",
    ]
    for cand in candidates:
        try:
            return importlib.import_module(cand)
        except ModuleNotFoundError:
            continue
        except Exception as e:
            # Return exception for inspection
            return e
    return None

# Main UI
st.set_page_config(layout="wide", page_title="Docex")

st.sidebar.title("Navigatie")
MAIN_PAGES = ["Home", "Assistants", "Info", "Contact"]
st.session_state.setdefault("main_nav", "Home")

main_nav = st.sidebar.radio("Ga naar", MAIN_PAGES, index=safe_index(MAIN_PAGES, st.session_state.get("main_nav", "Home")))
st.session_state["main_nav"] = main_nav

# Discover assistant modules/packages
modules_map = discover_assistants()

# Build assistants list (only include those with IS_ASSISTANT == True)
assistants = []
assistants_by_key = {}
for key, mod in modules_map.items():
    if isinstance(mod, Exception):
        # Import failed — skip but keep trace for later
        continue
    is_assistant = getattr(mod, "IS_ASSISTANT", False)
    if is_assistant:
        display = getattr(mod, "DISPLAY_NAME", key)
        assistants.append(display)
        assistants_by_key[display] = (key, mod)

# Page rendering
def render_non_assistant_page(page_name):
    """Render Home / Info / Contact by trying to import their module(s)."""
    base = page_name.lower()
    mod = import_page_module(base)
    if isinstance(mod, Exception):
        st.error(f"Fout bij importeren van pagina '{page_name}':\n```\n{traceback.format_exc(limit=1)}\n```")
        return
    if mod is None:
        st.error(f"Pagina-module voor '{page_name}' niet gevonden (verwachte webapp.assistants.{base} of package).")
        return
    # call render(tool=None) if available, else try render()
    try:
        if hasattr(mod, "render") and callable(mod.render):
            mod.render(None)
        else:
            st.error(f"Module voor '{page_name}' heeft geen render(tool) functie.")
    except Exception:
        st.error(f"Fout bij uitvoeren van pagina '{page_name}':\n```\n{traceback.format_exc()}\n```")

if main_nav in ["Home", "Info", "Contact"]:
    render_non_assistant_page(main_nav)
    st.experimental_rerun() if False else None  # no-op but leaves room if needed
    st.stop()

# Assistants page
st.title("Assistants")
if not assistants:
    st.info("Geen assistants gevonden. Zet `IS_ASSISTANT = True` in de assistant-modules.")
else:
    # choose assistant
    st.sidebar.subheader("Kies assistant")
    st.session_state.setdefault("selected_assistant", assistants[0])
    selected = st.sidebar.selectbox("Assistant", assistants, index=safe_index(assistants, st.session_state.get("selected_assistant")))
    st.session_state["selected_assistant"] = selected

    # load module and its tools
    key, mod = assistants_by_key[selected]
    # if module failed to import earlier, show error
    if isinstance(mod, Exception):
        st.error(f"Kon module '{key}' niet importeren:\n```\n{mod}\n```")
    else:
        # show available tools for this assistant only
        tools = getattr(mod, "TOOLS", ["— Kies tool —"])
        st.sidebar.subheader("Tool")
        st.session_state.setdefault("selected_tool", tools[0] if tools else "— Kies tool —")
        selected_tool = st.sidebar.selectbox("Kies tool", tools, index=safe_index(tools, st.session_state.get("selected_tool")))
        st.session_state["selected_tool"] = selected_tool

        # call module.render(tool)
        try:
            if hasattr(mod, "render") and callable(mod.render):
                mod.render(selected_tool)
            else:
                st.error(f"Assistant '{selected}' heeft geen render(tool) functie.")
        except Exception:
            st.error(f"Fout bij uitvoeren van assistant '{selected}':\n```\n{traceback.format_exc()}\n```")
