# src/webapp/components/sidebar.py
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
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


def _ensure_valid_tool(asst_key: str, tool_key: str | None) -> str:
    tools = ASSISTANTS.get(asst_key, {}).get("tools", {})
    if not tools:
        return ""
    if tool_key in tools:
        return tool_key  # geldig
    return ""  # liever leeg dan crashen


def render_sidebar(
    default_assistant: str = "general_support",
    default_tool: str | None = None,
) -> Tuple[str, str, str]:
    """Toont de volledige sidebar en retourneert (page, assistant_key, tool_key).
    Garanties:
      - assistant_key is altijd een geldige key uit ASSISTANTS
      - tool_key is '' of een geldige tool voor die assistant
    """
    _load_logo()

    # ---------------- Main menu ----------------
    st.sidebar.header("Hoofdmenu")
    main_options = ["Home", "Assistenten", "Info", "Contact"]

    # init main menu vanuit URL (query params) of fallback
    if "main_menu" not in st.session_state:
        qp = st.query_params
        page_q = qp.get("page", ["Home"])
        page = page_q[0] if isinstance(page_q, list) and page_q else "Home"
        st.session_state.main_menu = page if page in main_options else "Home"

    main_menu = st.sidebar.radio(
        label="Hoofdmenu",
        options=main_options,
        index=main_options.index(st.session_state.main_menu),
        key="main_menu_radio",
        on_change=lambda: st.session_state.update(
            {"main_menu": st.session_state.main_menu_radio}
        ),
        label_visibility="visible",
    )
    st.session_state.main_menu = main_menu
    st.sidebar.markdown("---")

    # --- buiten Assistenten-mode: behoud state & sync URL ---
    if main_menu != "Assistenten":
        # valideer (of initialiseer) assistant/tool
        st.session_state.assistant_key = _ensure_valid_assistant(
            st.session_state.get("assistant_key", default_assistant),
            default_assistant,
        )
        st.session_state.tool_key = _ensure_valid_tool(
            st.session_state.assistant_key, st.session_state.get("tool_key", default_tool or "")
        )

        st.query_params["page"] = main_menu
        return main_menu, st.session_state.assistant_key, st.session_state.tool_key

    # ---------------- Assistenten-mode ----------------
    st.sidebar.header("Assistent voor:")

    assistant_keys: List[str] = list(ASSISTANTS.keys())
    assistant_labels: List[str] = [ASSISTANTS[k]["label"] for k in assistant_keys]

    # init vanuit URL (query params)
    if "assistant_key" not in st.session_state or "tool_key" not in st.session_state:
        qp = st.query_params

        # assistant uit URL of default
        a_q = qp.get("assistant", [])
        a = a_q[0] if isinstance(a_q, list) and a_q else default_assistant
        st.session_state.assistant_key = _ensure_valid_assistant(a, default_assistant)

        # tool uit URL (alleen als geldig voor gekozen assistant)
        t_q = qp.get("tool", [])
        t = t_q[0] if isinstance(t_q, list) and t_q else (default_tool or "")
        st.session_state.tool_key = _ensure_valid_tool(st.session_state.assistant_key, t)

        # initialiseer radios met labels
        st.session_state.assistant_radio = ASSISTANTS[st.session_state.assistant_key]["label"]
        st.session_state.tool_radio = PLACEHOLDER

    # --- assistant selector ---
    def _on_assistant_changed():
        sel = st.session_state.assistant_radio
        # veilige mapping van label → key
        try:
            idx = assistant_labels.index(sel)
        except ValueError:
            idx = 0
        st.session_state.assistant_key = assistant_keys[idx]
        # wissel van assistant → reset tool
        st.session_state.tool_key = ""
        st.session_state.tool_radio = PLACEHOLDER
        st.query_params["page"] = "Assistenten"
        st.query_params["assistant"] = st.session_state.assistant_key
        st.query_params["tool"] = ""

    a_index = assistant_keys.index(st.session_state.assistant_key)
    st.sidebar.radio(
        label="Assistent voor",
        options=assistant_labels,
        index=a_index,
        key="assistant_radio",
        on_change=_on_assistant_changed,
        label_visibility="visible",
    )

    # --- tools selector ---
    chosen = st.session_state.assistant_key
    tools_meta = ASSISTANTS[chosen]["tools"]
    tool_keys = list(tools_meta.keys())
    tool_labels = [tools_meta[k]["label"] for k in tool_keys]

    if tool_keys:
        placeholder = [PLACEHOLDER] + tool_labels

        # default index op basis van huidige geldige tool_key
        if st.session_state.tool_key in tool_keys:
            curr_label = tools_meta[st.session_state.tool_key]["label"]
            try:
                default_idx = placeholder.index(curr_label)
            except ValueError:
                default_idx = 0
        else:
            default_idx = 0  # kies placeholder
            st.session_state.tool_radio = placeholder[0]

        def _on_tool_changed():
            sel = st.session_state.tool_radio
            if not sel or sel == placeholder[0]:
                st.session_state.tool_key = ""
            else:
                # veilige mapping label → key
                try:
                    st.session_state.tool_key = tool_keys[placeholder.index(sel) - 1]
                except ValueError:
                    st.session_state.tool_key = ""
            st.query_params["page"] = "Assistenten"
            st.query_params["assistant"] = st.session_state.assistant_key
            st.query_params["tool"] = st.session_state.tool_key or ""

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
        st.session_state.tool_radio = PLACEHOLDER
        st.query_params["tool"] = ""

    st.sidebar.markdown("---")
    # eind-sync URL
    st.query_params["assistant"] = st.session_state.assistant_key
    st.query_params["tool"] = st.session_state.tool_key or ""
    st.query_params["page"] = "Assistenten"

    return "Assistenten", st.session_state.assistant_key, st.session_state.tool_key
