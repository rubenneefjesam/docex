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

    st.sidebar.header("Hoofdmenu")

    # ---------- Hoofdmenu (bovenaan) ----------
    main_options = ["Home", "Assistenten", "Info", "Contact"]
    # bootstrap main menu from query param 'page' if present
    if "main_menu" not in st.session_state:
        qp = st.query_params
        page_q = qp.get("page", ["Assistenten"])[0] if "page" in qp else "Assistenten"
        if page_q not in main_options:
            page_q = "Assistenten"
        st.session_state.main_menu = page_q

    st.sidebar.radio(
        "",
        main_options,
        index=main_options.index(st.session_state.main_menu),
        key="main_menu_radio",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update({"main_menu": st.session_state.main_menu_radio}),
    )
    main_menu = st.session_state.main_menu

    st.sidebar.markdown("---")

    # If not in 'Assistenten' mode, we still want to expose the assistant/tool state
    # so returning code remains consistent.
    if main_menu != "Assistenten":
        # ensure assistant/tool in state exist (fallback)
        if "assistant_key" not in st.session_state:
            st.session_state.assistant_key = default_assistant
        if "tool_key" not in st.session_state:
            st.session_state.tool_key = ""
        # sync URL page param
        qp = st.query_params
        if qp.get("page", None) != main_menu:
            st.query_params["page"] = main_menu
        return main_menu, st.session_state.assistant_key, st.session_state.tool_key

    # ---------- Assistenten mode (zoals eerder) ----------
    st.sidebar.header("Assistent voor:")

    assistant_keys: List[str] = list(ASSISTANTS.keys())
    assistant_labels: List[str] = [ASSISTANTS[k]["label"] for k in assistant_keys]

    # Bootstrap assistant/tool from query params (only once)
    if "assistant_key" not in st.session_state or "tool_key" not in st.session_state:
        qp = st.query_params
        a_q = qp.get("assistant", [default_assistant])
        a = a_q[0] if isinstance(a_q, list) and a_q else (a_q if isinstance(a_q, str) else default_assistant)
        if a not in assistant_keys:
            a = default_assistant

        # tool: only honor qp if provided; otherwise start with NO tool selected
        if "tool" in qp and qp.get("tool") not in ([], ""):
            t_q = qp.get("tool")
            t = t_q[0] if isinstance(t_q, list) and t_q else (t_q if isinstance(t_q, str) else "")
            if t not in ASSISTANTS.get(a, {}).get("tools", {}):
                t = ""
        else:
            t = ""

        st.session_state.assistant_key = a
        st.session_state.tool_key = t
        st.session_state.assistant_radio = ASSISTANTS[a]["label"]
        st.session_state.tool_radio = ""

    current_assistant_key = st.session_state.assistant_key
    current_tool_key = st.session_state.tool_key

    # callbacks to keep session_state consistent and atomic
    def _on_assistant_changed():
        sel_label = st.session_state.get("assistant_radio", assistant_labels[0])
        try:
            new_a_key = assistant_keys[assistant_labels.index(sel_label)]
        except ValueError:
            new_a_key = default_assistant
        st.session_state.assistant_key = new_a_key
        st.session_state.tool_key = ""
        st.session_state.tool_radio = ""
        # ensure we are in Assistenten mode in URL
        st.query_params["page"] = "Assistenten"

    def _on_tool_changed():
        sel_tool_label = st.session_state.get("tool_radio", "")
        tools_meta = ASSISTANTS[st.session_state.assistant_key].get("tools", {})
        tool_keys = list(tools_meta.keys())
        tool_labels = [tools_meta[k]["label"] for k in tool_keys]
        if sel_tool_label == "— Kies tool —":
            st.session_state.tool_key = ""
            return
        try:
            new_t_key = tool_keys[tool_labels.index(sel_tool_label)]
        except ValueError:
            new_t_key = ""
        st.session_state.tool_key = new_t_key
        # sync page param
        st.query_params["page"] = "Assistenten"

    # Assistant radio (widget stores label)
    a_index = assistant_keys.index(current_assistant_key) if current_assistant_key in assistant_keys else 0
    st.sidebar.radio(
        "Assistent voor:",
        assistant_labels,
        index=a_index,
        key="assistant_radio",
        label_visibility="collapsed",
        on_change=_on_assistant_changed,
    )

    # Show tools for chosen assistant
    chosen_assistant = st.session_state.assistant_key
    tools_meta = ASSISTANTS.get(chosen_assistant, {}).get("tools", {})
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]

    if tool_keys:
        tool_labels_with_placeholder = ["— Kies tool —"] + tool_labels
        if st.session_state.tool_key:
            current_label = tools_meta.get(st.session_state.tool_key, {}).get("label", tool_labels_with_placeholder[0])
            default_index = tool_labels_with_placeholder.index(current_label) if current_label in tool_labels_with_placeholder else 0
        else:
            default_index = 0
            st.session_state.tool_radio = "— Kies tool —"

        st.sidebar.radio(
            "Kies tool:",
            tool_labels_with_placeholder,
            index=default_index,
            key="tool_radio",
            on_change=_on_tool_changed,
        )
    else:
        st.sidebar.info("Nog geen tools geconfigureerd voor deze assistant.")
        st.session_state.tool_key = ""
        st.session_state.tool_radio = ""

    st.sidebar.markdown("---")

    # Finally sync assistant/tool to URL if changed
    qp = st.query_params
    a_key = st.session_state.assistant_key
    t_key = st.session_state.tool_key or ""
    if qp.get("assistant", None) != a_key or qp.get("tool", None) != t_key:
        st.query_params["assistant"] = a_key
        st.query_params["tool"] = t_key
        st.query_params["page"] = "Assistenten"

    return "Assistenten", a_key, t_key
