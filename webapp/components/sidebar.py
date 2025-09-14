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

    st.sidebar.header("Assistent voor:")

    # Prepare lists
    assistant_keys: List[str] = list(ASSISTANTS.keys())
    assistant_labels: List[str] = [ASSISTANTS[k]["label"] for k in assistant_keys]

    # ---------- Bootstrap session_state from query params once ----------
    if "assistant_key" not in st.session_state or "tool_key" not in st.session_state:
        qp = st.query_params
        a_q = qp.get("assistant", [default_assistant])
        a = a_q[0] if isinstance(a_q, list) and a_q else (a_q if isinstance(a_q, str) else default_assistant)
        if a not in assistant_keys:
            a = default_assistant

        t_q = qp.get("tool", [default_tool or ""])
        t = t_q[0] if isinstance(t_q, list) and t_q else (t_q if isinstance(t_q, str) else default_tool or "")
        if t not in ASSISTANTS.get(a, {}).get("tools", {}):
            t = _first_tool_key(a)

        # store canonical keys
        st.session_state.assistant_key = a
        st.session_state.tool_key = t
        # also store the radio labels so widgets have a stable value
        st.session_state.assistant_radio = ASSISTANTS[a]["label"]
        tools_meta = ASSISTANTS[a].get("tools", {})
        st.session_state.tool_radio = tools_meta.get(t, {}).get("label", "") if tools_meta else ""

    # local convenience
    current_assistant_key = st.session_state.assistant_key
    current_tool_key = st.session_state.tool_key

    # ---------- callbacks ----------
    def _on_assistant_changed():
        sel_label = st.session_state.get("assistant_radio", assistant_labels[0])
        # map label back to key
        try:
            new_a_key = assistant_keys[assistant_labels.index(sel_label)]
        except ValueError:
            new_a_key = default_assistant
        # reset tool to first available for new assistant
        new_t_key = _first_tool_key(new_a_key)
        # update canonical state
        st.session_state.assistant_key = new_a_key
        st.session_state.tool_key = new_t_key
        # update the tool_radio label so the tool widget shows correct item
        tools_meta = ASSISTANTS[new_a_key].get("tools", {})
        st.session_state.tool_radio = tools_meta.get(new_t_key, {}).get("label", "")

    def _on_tool_changed():
        sel_tool_label = st.session_state.get("tool_radio", "")
        tools_meta = ASSISTANTS[st.session_state.assistant_key].get("tools", {})
        tool_keys = list(tools_meta.keys())
        tool_labels = [tools_meta[k]["label"] for k in tool_keys]
        try:
            new_t_key = tool_keys[tool_labels.index(sel_tool_label)]
        except ValueError:
            new_t_key = _first_tool_key(st.session_state.assistant_key)
        st.session_state.tool_key = new_t_key

    # ---------- Assistant radio (widget holds label) ----------
    a_index = assistant_keys.index(current_assistant_key) if current_assistant_key in assistant_keys else 0
    st.sidebar.radio(
        "Assistent voor:",
        assistant_labels,
        index=a_index,
        key="assistant_radio",
        label_visibility="collapsed",
        on_change=_on_assistant_changed,
    )
    # Determine tools for the currently selected assistant in state
    chosen_assistant = st.session_state.assistant_key
    tools_meta = ASSISTANTS.get(chosen_assistant, {}).get("tools", {})
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]

    # ---------- Tool radio ----------
    if tool_keys:
        # ensure tool_radio has a sensible default label
        if not st.session_state.get("tool_radio"):
            st.session_state.tool_radio = tool_labels[0]
        t_index = tool_keys.index(st.session_state.tool_key) if st.session_state.tool_key in tool_keys else 0
        st.sidebar.radio(
            "Kies tool:",
            tool_labels,
            index=t_index,
            key="tool_radio",
            on_change=_on_tool_changed,
        )
    else:
        st.sidebar.info("Nog geen tools geconfigureerd voor deze assistant.")
        # clear tool state
        st.session_state.tool_key = ""
        st.session_state.tool_radio = ""

    st.sidebar.markdown("---")

    # Sync to query params (do this last; Streamlit manages widget->session_state during this run)
    qp = st.query_params
    a_key = st.session_state.assistant_key
    t_key = st.session_state.tool_key or ""
    if qp.get("assistant", None) != a_key or qp.get("tool", None) != t_key:
        st.query_params["assistant"] = a_key
        st.query_params["tool"] = t_key

    return a_key, t_key
