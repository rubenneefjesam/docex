# webapp/assistants/general_support/document_generator.py
import streamlit as st
from webapp.core.tool_loader import load_tool_module_candidate, call_first_callable

def render():
    st.markdown("### 🧩 Document generator")
    st.caption("Start de generator-tool hieronder. (Deze pagina is de UI/glue; de implementatie zit in /tools.)")

    # Probeer meest specifieke → generiek (zoals je nu al doet)
    docmod = load_tool_module_candidate(
        "Document generator",
        "tools.plan_creator.dogen",
        "tools.plan_creator",
        "tools.doc_generator.docgen",
        "tools.doc_generator",
        "tools.docgen_tool.dogen",
    )

    if docmod:
        try:
            call_first_callable(docmod, "Document generator")
        except Exception as e:
            st.error(f"Fout bij starten Document generator: {e}")
    else:
        st.error("Geen module voor Document generator gevonden.\n"
                 "Geprobeerd: tools.plan_creator(.dogen), tools.doc_generator(.docgen), tools.docgen_tool.dogen")
