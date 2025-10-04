from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional
import streamlit as st

from webapp.registry import ASSISTANTS

PLACEHOLDER = "— Kies tool —"


def _load_logo() -> None:
    base_assets = Path(__file__).resolve().parents[1] / "assets"
    for name in ("beeldmerk.png", "Beeldmerk.png", "logo.png", "logo.svg"):
        p = base_assets / name
        if p.exists():
            st.sidebar.image(str(p), width=140)
            break


def _ensure_valid_assistant(key: str, fallback: str) -> str:
    keys = list(ASSISTANTS.keys())
    return key if key in keys else (fallback if fallback in keys else keys[0])


def _ensure_valid_tool(asst_key: str, tool_key: Optional[str]) -> str:
    tools = ASSISTANTS.get(asst_key, {}).get("tools", {})
    return tool_key if tool_key in tools else ""


def render_sidebar(
    default_assistant: str = "general_support",
    default_tool: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Renders the sidebar and returns (page, assistant_key, tool_key).

    Guarantees:
      - assistant_key is always a valid key in ASSISTANTS
      - tool_key is '' or a valid tool for that assistant
    """
    # ---- Logo ----
    _load_logo()

    # ---- Appearance toggle ----
    st.sidebar.title("Instellingen")
    appearance = st.sidebar.radio(
        "Uiterlijk",
        options=["Licht", "Donker"],
        index=0,
        key="appearance_toggle",
    )
    if appearance == "Donker":
        st.markdown(
            """
            <style>
            .reportview-container { background-color: #333; color: #eee; }
            .sidebar .sidebar-content { background-color: #444; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    st.sidebar.markdown("---")

    # ---- Main menu ----
    st.sidebar.header("Hoofdmenu")
    main_options = ["Home", "Assistenten", "Agents", "Info", "Contact"]
    if "main_menu" not in st.session_state:
        qp = st.query_params
        page_q = qp.get("page", ["Home"])
        initial = page_q[0] if page_q and isinstance(page_q, list) else "Home"
        st.session_state.main_menu = initial if initial in main_options else "Home"

    main_menu = st.sidebar.radio(
        "Hoofdmenu",
        options=main_options,
        index=main_options.index(st.session_state.main_menu),
        key="main_menu_radio",
        on_change=lambda: st.session_state.update({"main_menu": st.session_state.main_menu_radio}),
    )
    st.session_state.main_menu = main_menu
    st.sidebar.markdown("---")

    if main_menu != "Assistenten":
        asst_key = _ensure_valid_assistant(
            st.session_state.get("assistant_key", default_assistant), default_assistant
        )
        tool_key = _ensure_valid_tool(
            asst_key, st.session_state.get("tool_key", default_tool or "")
        )
        st.session_state.assistant_key, st.session_state.tool_key = asst_key, tool_key
        st.query_params["page"] = main_menu
        return main_menu, asst_key, tool_key

    # ---- Assistenten mode ----
    st.sidebar.header("Assistent voor:")
    assistant_keys: List[str] = list(ASSISTANTS.keys())
    assistant_labels: List[str] = [ASSISTANTS[k]["label"] for k in assistant_keys]

    if "assistant_key" not in st.session_state or "tool_key" not in st.session_state:
        qp = st.query_params
        a_q = qp.get("assistant", [])
        initial_asst = a_q[0] if a_q and isinstance(a_q, list) else default_assistant
        st.session_state.assistant_key = _ensure_valid_assistant(initial_asst, default_assistant)

        t_q = qp.get("tool", [])
        initial_tool = t_q[0] if t_q and isinstance(t_q, list) else (default_tool or "")
        st.session_state.tool_key = _ensure_valid_tool(st.session_state.assistant_key, initial_tool)

        st.session_state.assistant_radio = ASSISTANTS[st.session_state.assistant_key]["label"]
        st.session_state.tool_radio = PLACEHOLDER

    def _on_assistant_changed():
        sel = st.session_state.assistant_radio
        idx = assistant_labels.index(sel) if sel in assistant_labels else 0
        st.session_state.assistant_key = assistant_keys[idx]
        st.session_state.tool_key = ""
        st.session_state.tool_radio = PLACEHOLDER
        st.query_params.update({"page": "Assistenten", "assistant": st.session_state.assistant_key, "tool": ""})

    st.sidebar.radio(
        "Assistent voor",
        options=assistant_labels,
        index=assistant_keys.index(st.session_state.assistant_key),
        key="assistant_radio",
        on_change=_on_assistant_changed,
    )

    tools_meta = ASSISTANTS[st.session_state.assistant_key].get("tools", {})
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]
    if tool_keys:
        placeholder = [PLACEHOLDER] + tool_labels
        if st.session_state.tool_key in tool_keys:
            curr_label = tools_meta[st.session_state.tool_key]["label"]
            default_idx = placeholder.index(curr_label)
        else:
            default_idx = 0
            st.session_state.tool_radio = PLACEHOLDER

        def _on_tool_changed():
            sel = st.session_state.tool_radio
            key = "" if sel == PLACEHOLDER else tool_keys[placeholder.index(sel) - 1]
            st.session_state.tool_key = key
            st.query_params.update({"page": "Assistenten", "assistant": st.session_state.assistant_key, "tool": key or ""})

        st.sidebar.radio(
            "Kies tool",
            options=placeholder,
            index=default_idx,
            key="tool_radio",
            on_change=_on_tool_changed,
        )
    else:
        st.sidebar.info("Nog geen tools geconfigureerd voor deze assistant.")
        st.session_state.tool_key = ""
        st.session_state.tool_radio = PLACEHOLDER

    st.sidebar.markdown("---")
    st.query_params.update({
        "page": "Assistenten",
        "assistant": st.session_state.assistant_key,
        "tool": st.session_state.tool_key or ""
    })

    return "Assistenten", st.session_state.assistant_key, st.session_state.tool_key
