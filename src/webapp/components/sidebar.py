# webapp/components/sidebar.py

from pathlib import Path
import streamlit as st
from webapp.registry import ASSISTANTS
from typing import List

def _first_tool_key(assistant_key: str) -> str:
    return next(iter(ASSISTANTS.get(assistant_key, {}).get("tools", {}).keys()), "")

def render_sidebar(default_assistant: str = "general_support",
                   default_tool: str | None = None):
    # Logo
    base_assets = Path(__file__).resolve().parents[1] / "assets"
    for name in ("beeldmerk.png", "Beeldmerk.png", "logo.png", "logo.svg"):
        p = base_assets / name
        if p.exists():
            st.sidebar.image(str(p), width=140)
            break

    # Hoofdmenu
    st.sidebar.header("Hoofdmenu")
    main_options = ["Home", "Assistenten", "Info", "Contact"]

    # init session_state voor main_menu
    if "main_menu" not in st.session_state:
        qp = st.query_params
        page_q = qp.get("page", ["Home"])
        page = page_q[0] if isinstance(page_q, list) and page_q else "Home"
        st.session_state.main_menu = page if page in main_options else "Home"

    # Hoofdmenu-radio (houd deze call exact zoals-ie was)
    main_menu = st.sidebar.radio(
        label="Hoofdmenu",
        options=main_options,
        index=main_options.index(st.session_state.main_menu),
        key="main_menu_radio",
        on_change=lambda: st.session_state.update({"main_menu": st.session_state.main_menu_radio}),
        label_visibility="visible",
    )
    # Houd session_state.main_menu altijd in sync met de radio-keuze
    st.session_state.main_menu = main_menu

    st.sidebar.markdown("---")

    # Buiten Assistenten‐mode: behoud assistant/tool state
    if main_menu != "Assistenten":
        if "assistant_key" not in st.session_state:
            st.session_state.assistant_key = default_assistant
        if "tool_key" not in st.session_state:
            st.session_state.tool_key = default_tool or ""
        # URL sync
        st.query_params["page"] = main_menu
        return main_menu, st.session_state.assistant_key, st.session_state.tool_key

    # ---------- Assistenten mode ----------
    st.sidebar.header("Assistent voor:")
    assistant_keys: List[str] = list(ASSISTANTS.keys())
    assistant_labels: List[str] = [ASSISTANTS[k]["label"] for k in assistant_keys]

    # init session_state voor assistant/tool
    if "assistant_key" not in st.session_state or "tool_key" not in st.session_state:
        qp = st.query_params
        # ASSISTANT
        a_q = qp.get("assistant", [])
        a = a_q[0] if isinstance(a_q, list) and a_q else default_assistant
        st.session_state.assistant_key = a if a in assistant_keys else default_assistant
        # TOOL (veilige extractie)
        t_q = qp.get("tool", [])
        t = t_q[0] if isinstance(t_q, list) and t_q else ""
        st.session_state.tool_key = t if t in ASSISTANTS[st.session_state.assistant_key]["tools"] else ""
        # Sync radios
        st.session_state.assistant_radio = ASSISTANTS[st.session_state.assistant_key]["label"]
        st.session_state.tool_radio = ""

    def _on_assistant_changed():
        sel = st.session_state.assistant_radio
        idx = assistant_labels.index(sel) if sel in assistant_labels else 0
        new_a = assistant_keys[idx]
        st.session_state.assistant_key = new_a
        st.session_state.tool_key = ""
        st.session_state.tool_radio = ""
        st.query_params["page"] = "Assistenten"

    # Assistant‐selector
    a_index = assistant_keys.index(st.session_state.assistant_key)
    st.sidebar.radio(
        label="Assistent voor",
        options=assistant_labels,
        index=a_index,
        key="assistant_radio",
        on_change=_on_assistant_changed,
        label_visibility="visible",
    )

    # Tools‐selector
    chosen = st.session_state.assistant_key
    tools_meta = ASSISTANTS[chosen]["tools"]
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]

    if tool_keys:
        placeholder = ["— Kies tool —"] + tool_labels
        if st.session_state.tool_key in tool_keys:
            curr_label = tools_meta[st.session_state.tool_key]["label"]
            default_idx = placeholder.index(curr_label)
        else:
            default_idx = 0
            st.session_state.tool_radio = placeholder[0]

        def _on_tool_changed():
            sel = st.session_state.tool_radio
            if sel == placeholder[0]:
                st.session_state.tool_key = ""
            else:
                # placeholder[0] is de dummy, dus -1
                st.session_state.tool_key = tool_keys[placeholder.index(sel) - 1]
            st.query_params["page"] = "Assistenten"

        st.sidebar.radio(
            label="Kies tool",
            options=placeholder,
            index=default_idx,
            key="tool_radio",
            on_change=_on_tool_changed,
            label_visibility="visible",
        )
    else:
        st.sidebar.info("Nog geen tools geconfigureerd voor deze assistant.")
        st.session_state.tool_key = ""
        st.session_state.tool_radio = ""

    st.sidebar.markdown("---")
    # URL sync
    st.query_params["assistant"] = st.session_state.assistant_key
    st.query_params["tool"]      = st.session_state.tool_key or ""
    st.query_params["page"]      = "Assistenten"

    return "Assistenten", st.session_state.assistant_key, st.session_state.tool_key
