import streamlit as st
from webapp.core.tool_loader import load_tool_module_candidate, call_first_callable

def render():
    st.markdown("### 🔍 Document comparison")
    st.caption("Vergelijk documenten en zie contextuele wijzigingen.")

    # 1) Naam van de tool
    # 2–5) De verschillende module-paden die we willen proberen
    cogemod = load_tool_module_candidate(
        "Document comparison",
        "tools.doc_comparison.doc_comparison",
        "tools.doc_comparison",
        "tools.coge_tool.coge",
        "tools.coge_tool",
    )

    if cogemod:
        try:
            call_first_callable(cogemod, "Document comparison")
        except Exception as e:
            st.error(f"Fout bij starten Document comparison: {e}")
    else:
        st.error(
            "Geen module voor Document comparison gevonden.\n"
            "Geprobeerd: tools.doc_comparison.doc_comparison, "
            "tools.doc_comparison, "
            "tools.coge_tool.coge, "
            "tools.coge_tool"
        )
