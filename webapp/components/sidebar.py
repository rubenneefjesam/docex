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
        page_q = qp.get("page", ["Assistenten"])[0]
        if page_q not in main_options:
            page_q = "Assistenten"
        st.session_state.main_menu = page_q

    main_menu = st.sidebar.radio(
        label="Hoofdmenu",
        options=main_options,
        index=main_options.index(st.session_state.main_menu),
        key="main_menu_radio",
        label_visibility="visible",
        on_change=lambda: st.session_state.update({"main_menu": st.session_state.main_menu_radio}),
    )
    st.sidebar.markdown("---")

    # Buiten Assistenten‐mode: behoud assistant/tool state
    if main_menu != "Assistenten":
        if "assistant_key" not in st.session_state:
            st.session_state.assistant_key = default_assistant
        if "tool_key" not in st.session_state:
            st.session_state.tool_key = ""
        st.query_params["page"] = main_menu
        return main_menu, st.session_state.assistant_key, st.session_state.tool_key

    # ---------- Assistenten mode ----------
    st.sidebar.header("Assistent voor:")
    assistant_keys: List[str] = list(ASSISTANTS.keys())
    assistant_labels: List[str] = [ASSISTANTS[k]["label"] for k in assistant_keys]

    # init session_state voor assistant/tool
    if "assistant_key" not in st.session_state or "tool_key" not in st.session_state:
        qp = st.query_params
        a = qp.get("assistant", [default_assistant])[0]
        if a not in assistant_keys:
            a = default_assistant
        # tool uit query param of leeg
        t = qp.get("tool", [""])[0]
        if t not in ASSISTANTS.get(a, {}).get("tools", {}):
            t = ""
        st.session_state.assistant_key = a
        st.session_state.tool_key = t
        st.session_state.assistant_radio = ASSISTANTS[a]["label"]
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
        default_idx = 0
        if st.session_state.tool_key in tool_keys:
            current_label = tools_meta[st.session_state.tool_key]["label"]
            default_idx = placeholder.index(current_label)

        def _on_tool_changed():
            sel = st.session_state.tool_radio
            if sel == "— Kies tool —":
                st.session_state.tool_key = ""
            else:
                idx = placeholder.index(sel) - 1
                st.session_state.tool_key = tool_keys[idx]
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
    # Zorg dat URL sync
    st.query_params["assistant"] = st.session_state.assistant_key
    st.query_params["tool"] = st.session_state.tool_key or ""
    st.query_params["page"] = "Assistenten"

    return "Assistenten", st.session_state.assistant_key, st.session_state.tool_key
