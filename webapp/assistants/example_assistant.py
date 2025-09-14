DISPLAY_NAME = "Voorbeeld assistant"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —", "Tool 1"]

# voorbeeldtemplate voor een assistant-module
DISPLAY_NAME = "Voorbeeld assistant"
TOOLS = ["— Kies tool —", "Tool 1", "Tool 2"]

import streamlit as st

def render(tool):
    st.title(DISPLAY_NAME)
    st.write("Korte omschrijving van deze assistant.")
    if tool is None or tool == "— Kies tool —":
        st.info("Selecteer een tool in de sidebar.")
        return

    st.write(f"Gekozen tool: **{tool}**")
    if tool == "Tool 1":
        st.write("UI + logica voor Tool 1")
    elif tool == "Tool 2":
        st.write("UI + logica voor Tool 2")
