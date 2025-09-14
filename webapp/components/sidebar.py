from pathlib import Path
import streamlit as st
from webapp.registry import ASSISTANTS

def _qp_get_str(qp, key: str, default: str = "") -> str:
    val = qp.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val if isinstance(val, str) else default

def _first_tool_key(assistant_key: str) -> str:
    tools = ASSISTANTS.get(assistant_key, {}).get("tools", {})
    return next(iter(tools.keys()), "")

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

    # ---------- Bootstrap session_state eenmaal uit query params ----------
    if "assistant_key" not in st.session_state or "tool_key" not in st.session_state:
        qp = st.query_params
        a = _qp_get_str(qp, "assistant", default_assistant)
        if a not in ASSISTANTS:
            a = default_assistant
        t = _qp_get_str(qp, "tool", default_tool or "")
        if t not in ASSISTANTS.get(a, {}).get("tools", {}):
            t = _first_tool_key(a)
        st.session_state.assistant_key = a
        st.session_state.tool_key = t

    # Huidige selectie uit state
    a_key = st.session_state.assistant_key
    t_key = st.session_state.tool_key

    # ---------- Assistent kiezen ----------
    assistant_keys = list(ASSISTANTS.keys())
    assistant_labels = [ASSISTANTS[k]["label"] for k in assistant_keys]
    a_idx = assistant_keys.index(a_key) if a_key in assistant_keys else 0

    sel_assistant_label = st.sidebar.radio(
        "Assistent voor:",
        assistant_labels,
        index=a_idx,
        label_visibility="collapsed",
        key="assistant_radio",
    )
    new_a_key = assistant_keys[assistant_labels.index(sel_assistant_label)]

    # Als assistent verandert -> tool resetten naar eerste beschikbare
    if new_a_key != a_key:
        t_key = _first_tool_key(new_a_key)

    # ---------- Tool kiezen voor gekozen assistent ----------
    tools_meta = ASSISTANTS[new_a_key].get("tools", {})
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]

    if tool_keys:
        t_idx = tool_keys.index(t_key) if t_key in tool_keys else 0
        sel_tool_label = st.sidebar.radio(
            "Kies tool:",
            tool_labels,
            index=t_idx,
            key="tool_radio",
        )
        new_t_key = tool_keys[tool_labels.index(sel_tool_label)]
    else:
        st.sidebar.info("Nog geen tools geconfigureerd voor deze assistant.")
        new_t_key = ""

    st.sidebar.markdown("---")

    # ---------- Update state ----------
    changed = (new_a_key != a_key) or (new_t_key != t_key)
    if changed:
        st.session_state.assistant_key = new_a_key
        st.session_state.tool_key = new_t_key

    # ---------- Sync terug naar URL (zonder flikkeren) ----------
    qp = st.query_params
    if qp.get("assistant", None) != new_a_key or qp.get("tool", None) != new_t_key:
        st.query_params["assistant"] = new_a_key
        st.query_params["tool"] = new_t_key

    return new_a_key, new_t_key
