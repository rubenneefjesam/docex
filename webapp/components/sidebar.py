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

        # Determine if user explicitly provided query params
        has_qp_assistant = "assistant" in qp and qp.get("assistant") not in ([], "")
        has_qp_tool = "tool" in qp and qp.get("tool") not in ([], "")

        # assistant: from qp if present, otherwise default
        if has_qp_assistant:
            a_q = qp.get("assistant")
            a = a_q[0] if isinstance(a_q, list) and a_q else (a_q if isinstance(a_q, str) else default_assistant)
            if a not in assistant_keys:
                a = default_assistant
        else:
            a = default_assistant

        # tool: only honor qp if provided; otherwise start with NO tool selected (empty)
        if has_qp_tool:
            t_q = qp.get("tool")
            t = t_q[0] if isinstance(t_q, list) and t_q else (t_q if isinstance(t_q, str) else "")
            if t not in ASSISTANTS.get(a, {}).get("tools", {}):
                t = ""
        else:
            t = ""  # no tool selected by default -> Home

        # store canonical keys + widget label placeholders
        st.session_state.assistant_key = a
        st.session_state.tool_key = t
        st.session_state.assistant_radio = ASSISTANTS[a]["label"]
        st.session_state.tool_radio = ""  # we'll show a placeholder in the widget

    # local convenience
    current_assistant_key = st.session_state.assistant_key
    current_tool_key = st.session_state.tool_key

    # ---------- callbacks ----------
    def _on_assistant_changed():
        sel_label = st.session_state.get("assistant_radio", assistant_labels[0])
        try:
            new_a_key = assistant_keys[assistant_labels.index(sel_label)]
        except ValueError:
            new_a_key = default_assistant
        # DO NOT auto-select a tool: require explicit user action
        st.session_state.assistant_key = new_a_key
        st.session_state.tool_key = ""
        st.session_state.tool_radio = ""  # placeholder shown for tools

    def _on_tool_changed():
        sel_tool_label = st.session_state.get("tool_radio", "")
        # tool_labels_with_placeholder is built lower; we get real labels from tools_meta
        tools_meta = ASSISTANTS[st.session_state.assistant_key].get("tools", {})
        tool_keys = list(tools_meta.keys())
        tool_labels = [tools_meta[k]["label"] for k in tool_keys]
        # handle placeholder (we use special placeholder label at index 0)
        if sel_tool_label == "— Kies tool —":
            st.session_state.tool_key = ""
            return
        try:
            new_t_key = tool_keys[tool_labels.index(sel_tool_label)]
        except ValueError:
            new_t_key = ""
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

    # ---------- Tool radio with placeholder ----------
    if tool_keys:
        # Insert placeholder as first option so no tool is active until user chooses
        tool_labels_with_placeholder = ["— Kies tool —"] + tool_labels
        # Determine current label to show
        if st.session_state.tool_key:
            current_label = tools_meta.get(st.session_state.tool_key, {}).get("label", tool_labels_with_placeholder[0])
            default_index = tool_labels_with_placeholder.index(current_label) if current_label in tool_labels_with_placeholder else 0
        else:
            default_index = 0  # placeholder selected
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

    # Sync to query params (Streamlit manages widget->session_state)
    qp = st.query_params
    a_key = st.session_state.assistant_key
    t_key = st.session_state.tool_key or ""

    # If tool empty -> keep tool param empty (Home); ensure assistant param present
    if qp.get("assistant", None) != a_key or qp.get("tool", None) != t_key:
        st.query_params["assistant"] = a_key
        st.query_params["tool"] = t_key

    return a_key, t_key
