# webapp/components/sidebar.py
from pathlib import Path
import streamlit as st
from webapp.registry import ASSISTANTS

def _qp_list(qp, key: str, default: str = ""):
    """Normalize st.query_params[key] to a one-item list."""
    val = qp.get(key, default)
    if isinstance(val, list):
        return val
    if val is None:
        return [default]
    return [val]

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

    qp = st.query_params
    a_qp = _qp_list(qp, "assistant", default_assistant)[0]
    t_qp = _qp_list(qp, "tool", default_tool or "")[0]

    # Assistent selecteren
    assistant_keys = list(ASSISTANTS.keys())
    if a_qp not in assistant_keys:
        a_qp = default_assistant
    labels = [ASSISTANTS[k]["label"] for k in assistant_keys]
    idx = assistant_keys.index(a_qp)
    sel_label = st.sidebar.radio(
        "Assistent voor:",
        labels,
        index=idx,
        label_visibility="collapsed",
    )
    assistant = assistant_keys[labels.index(sel_label)]

    # Tools voor gekozen assistent
    tools_meta = ASSISTANTS[assistant].get("tools", {})
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]

    # Kies default tool (eerste) als query param leeg of ongeldig is
    if t_qp not in tool_keys:
        t_qp = tool_keys[0] if tool_keys else ""

    if tool_keys:
        sel_tool_label = st.sidebar.radio("Kies tool:", tool_labels, index=tool_keys.index(t_qp))
        tool = tool_keys[tool_labels.index(sel_tool_label)]
    else:
        st.sidebar.info("Nog geen tools geconfigureerd voor deze assistant.")
        tool = ""

    st.sidebar.markdown("---")

    # Sync URL alleen als er iets veranderde
    if qp.get("assistant", None) != assistant or qp.get("tool", None) != tool:
        st.query_params["assistant"] = assistant
        st.query_params["tool"] = tool

    return assistant, tool
