from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Optional
import streamlit as st

from webapp.registry import ASSISTANTS, AGENTS

PLACEHOLDER = "— Kies tool —"


def _load_logo() -> None:
    base_assets = Path(__file__).resolve().parents[1] / "assets"
    for name in ("beeldmerk.png", "Beeldmerk.png", "logo.png", "logo.svg"):
        p = base_assets / name
        if p.exists():
            st.sidebar.image(str(p), width=140)
            break


def _ensure_valid_key(key: str, valid_keys: List[str], fallback: str) -> str:
    return key if key in valid_keys else (fallback if fallback in valid_keys else valid_keys[0])


def _ensure_valid_tool(tools: dict, tool_key: Optional[str]) -> str:
    return tool_key if tool_key in tools else ""


def render_sidebar(
    default_assistant: str = "general_support",
    default_tool: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Renders the sidebar and returns (page, key, tool_key).

    If page == 'Assistenten', key is assistant_key and uses ASSISTANTS.
    If page == 'Agents', key is agent_key and uses AGENTS.
    Otherwise tool_key always '' and key unused.
    """
    _load_logo()

    # Appearance toggle
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

    # Main menu
    st.sidebar.header("Hoofdmenu")
    main_options = ["Home", "Assistenten", "Agents", "Info", "Contact"]
    if "main_menu" not in st.session_state:
        qp = st.query_params
        page_q = qp.get("page", ["Home"])
        initial = page_q[0] if page_q and isinstance(page_q, list) else "Home"
        st.session_state.main_menu = initial if initial in main_options else "Home"

    page = st.sidebar.radio(
        "Hoofdmenu",
        options=main_options,
        index=main_options.index(st.session_state.main_menu),
        key="main_menu_radio",
        on_change=lambda: st.session_state.update({"main_menu": st.session_state.main_menu_radio}),
    )
    st.session_state.main_menu = page
    st.sidebar.markdown("---")

    # Helper for modes outside Assistenten/Agents
    if page not in ("Assistenten", "Agents"):
        # clear keys
        st.session_state.tool_key = ""
        st.query_params["page"] = page
        return page, "", ""

    # Determine registry and session names
    is_agents = page == "Agents"
    registry = AGENTS if is_agents else ASSISTANTS
    state_key = "agent_key" if is_agents else "assistant_key"
    state_tool = "agent_tool" if is_agents else "tool_key"
    radio_key = "agent_radio" if is_agents else "assistant_radio"
    tool_radio_key = "agent_tool_radio" if is_agents else "tool_radio"
    header_label = "Agent voor:" if is_agents else "Assistent voor:"

    # Initialize state
    keys = list(registry.keys())
    labels = [registry[k]["label"] for k in keys]
    if state_key not in st.session_state or state_tool not in st.session_state:
        st.session_state[state_key] = _ensure_valid_key(default_assistant if not is_agents else keys[0], keys, keys[0])
        st.session_state[state_tool] = _ensure_valid_tool(registry[st.session_state[state_key]]["tools"], default_tool or "")
        st.session_state[radio_key] = registry[st.session_state[state_key]]["label"]
        st.session_state[tool_radio_key] = PLACEHOLDER

    # Selector header
    st.sidebar.header(header_label)

    def on_key_changed():
        sel = st.session_state[radio_key]
        idx = labels.index(sel) if sel in labels else 0
        st.session_state[state_key] = keys[idx]
        st.session_state[state_tool] = ""
        st.session_state[tool_radio_key] = PLACEHOLDER
        st.query_params.update({"page": page, "assistant" if not is_agents else "agent": keys[idx], "tool": ""})

    st.sidebar.radio(
        header_label,
        options=labels,
        index=keys.index(st.session_state[state_key]),
        key=radio_key,
        on_change=on_key_changed,
    )

    # Tool selector
    tools_meta = registry[st.session_state[state_key]]["tools"]
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]
    if tool_keys:
        placeholder = [PLACEHOLDER] + tool_labels
        if st.session_state[state_tool] in tool_keys:
            curr = tools_meta[st.session_state[state_tool]]["label"]
            default_idx = placeholder.index(curr)
        else:
            default_idx = 0
            st.session_state[tool_radio_key] = PLACEHOLDER

        def on_tool_changed():
            sel = st.session_state[tool_radio_key]
            if sel == PLACEHOLDER:
                st.session_state[state_tool] = ""
            else:
                st.session_state[state_tool] = tool_keys[placeholder.index(sel) - 1]
            st.query_params.update({"page": page, "assistant" if not is_agents else "agent": st.session_state[state_key], "tool": st.session_state[state_tool] or ""})

        st.sidebar.radio(
            "Kies tool",
            options=placeholder,
            index=default_idx,
            key=tool_radio_key,
            on_change=on_tool_changed,
        )
    else:
        st.sidebar.info(f"Nog geen tools geconfigureerd voor deze {'Agent' if is_agents else 'assistant'}.")

    st.sidebar.markdown("---")
    st.query_params.update({"page": page, "assistant" if not is_agents else "agent": st.session_state[state_key], "tool": st.session_state[state_tool] or ""})

    return page, st.session_state[state_key], st.session_state[state_tool]