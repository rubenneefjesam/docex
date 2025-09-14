# webapp/components/sidebar.py
from pathlib import Path
import streamlit as st
from webapp.registry import ASSISTANTS

def render_sidebar(default_assistant: str = "general_support",
                   default_tool: str | None = None):
    """
    Bouwt de sidebar en retourneert (assistant_key, tool_key).
    - default_* worden gebruikt als query params ontbreken of ongeldige waarden hebben.
    """
    # Logo
    base_assets = Path(__file__).resolve().parents[1] / "assets"
    for name in ("beeldmerk.png", "Beeldmerk.png", "logo.png", "logo.svg"):
        p = base_assets / name
        if p.exists():
            st.sidebar.image(str(p), width=140)
            break

    st.sidebar.header("Assistent voor:")

    # Query params (dieplinks)
    qp = st.query_params
    a_qp = qp.get("assistant", [default_assistant])[0]
    t_qp = qp.get("tool", [default_tool or ""])[0]

    # Assistent radio
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
    tools_meta = ASSISTANTS[assistant]["tools"]
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]

    if t_qp not in tool_keys:
        # kies eerste tool als default (indien aanwezig)
        t_qp = tool_keys[0] if tool_keys else ""

    if tool_keys:
        sel_tool_label = st.sidebar.radio("Kies tool:", tool_labels, index=tool_keys.index(t_qp))
        tool = tool_keys[tool_labels.index(sel_tool_label)]
    else:
        st.sidebar.info("Nog geen tools geconfigureerd voor deze assistant.")
        tool = ""

    st.sidebar.markdown("---")
    # sync URL
    if qp.get("assistant", [None])[0] != assistant or qp.get("tool", [None])[0] != tool:
        st.query_params["assistant"] = assistant
        st.query_params["tool"] = tool

    return assistant, tool
