import streamlit as st
from pathlib import Path

# basis config
st.set_page_config(page_title="Document generator-app", layout="wide")

# --- Helper: init session_state defaults ---
if "main_nav" not in st.session_state:
    st.session_state["main_nav"] = "Home"
if "assistant_nav" not in st.session_state:
    st.session_state["assistant_nav"] = "General support"
if "tool_nav" not in st.session_state:
    st.session_state["tool_nav"] = "— Kies tool —"

# --- SIDEBAR (navigatie) ---
with st.sidebar:
    st.markdown("## Hoofdmenu")
    page = st.radio(
        label="",
        options=["Home", "Assistants", "Info", "Contact"],
        index=["Home", "Assistants", "Info", "Contact"].index(st.session_state["main_nav"]),
        key="main_nav"
    )
    st.markdown("---")

    # Alleen tonen wanneer "Assistants" geselecteerd is
    if st.session_state["main_nav"] == "Assistants":
        st.markdown("### Assistent voor:")
        assistant = st.radio(
            label="",
            options=[
                "General support",
                "Tender assistant",
                "Risk assistant",
                "Calculator assistant",
                "Legal assistant",
                "Project assistant",
                "Sustainability advisor"
            ],
            index=0 if st.session_state["assistant_nav"] not in [
                "General support",
                "Tender assistant",
                "Risk assistant",
                "Calculator assistant",
                "Legal assistant",
                "Project assistant",
                "Sustainability advisor"
            ] else [
                "General support",
                "Tender assistant",
                "Risk assistant",
                "Calculator assistant",
                "Legal assistant",
                "Project assistant",
                "Sustainability advisor"
            ].index(st.session_state["assistant_nav"]),
            key="assistant_nav"
        )

        st.markdown("### Kies tool:")
        tool = st.radio(
            label="",
            options=["— Kies tool —", "Document generator", "Document comparison"],
            index=["— Kies tool —", "Document generator", "Document comparison"].index(st.session_state["tool_nav"]),
            key="tool_nav"
        )
    else:
        # Zorg dat sidebar-keuzes geen oude state houden als we niet op Assistants staan
        # (optioneel: uncomment om te clearen)
        # st.session_state["assistant_nav"] = "General support"
        # st.session_state["tool_nav"] = "— Kies tool —"
        assistant = None
        tool = None

# --- MAIN RENDER FUNCTIES ---
def render_home():
    st.title("🏠 Home")
    st.write("Welkom bij de **Document generator-app**. Kies een assistent via het zijmenu.")
    st.markdown("---")
    st.subheader("Beschikbare assistenten")
    st.write(
        "- General support  \n"
        "- Document generator  \n"
        "- Document comparison  \n"
        "- Tender assistant  \n"
        "- Risk assistant  \n"
        "- Calculator assistant  \n"
        "- Legal assistant  \n"
        "- Project assistant  \n"
        "- Sustainability advisor"
    )
    st.info("Tip: ga naar *Assistants* in het zijmenu om per assistent specifieke tools en content te zien.")

def render_info():
    st.title("ℹ️ Info")
    st.write("Informatie over de app, versie, changelog en instructies.")
    st.write("- Versie: 1.0.0")
    st.write("- Auteur: Team X")
    st.write("- Laatste wijziging: 2025-09-XX")

def render_contact():
    st.title("📬 Contact")
    st.write("Neem contact op met de support of PO AI.")
    st.write("- E-mail: support@example.com")
    st.write("- Interne chat: #ai-innovation")
    st.write("- Telefoon: 012-3456789")

# Per-assistent renderers (voorbeeldcontent)
def render_general(assistant, tool):
    st.title(f"{assistant}")
    st.write("Korte omschrijving van General support.")
    st.write("Gekozen tool:", tool)
    if tool == "Document generator":
        st.write("Hier kun je documenten genereren — formulier/inputs ...")
        # voorbeeldform
        name = st.text_input("Documentnaam", value="nieuw_document.docx")
        prompt = st.text_area("Prompt / instructies", value="Maak een samenvatting van ...")
        if st.button("Genereer document"):
            st.success(f"Document `{name}` gegenereerd met prompt (simulatie).")
    elif tool == "Document comparison":
        st.write("Vergelijk twee documenten (PDF/DOCX) — upload hieronder:")
        col1, col2 = st.columns(2)
        with col1:
            doc_a = st.file_uploader("Upload document A", type=["pdf", "docx"], key="a")
        with col2:
            doc_b = st.file_uploader("Upload document B", type=["pdf", "docx"], key="b")
        if doc_a and doc_b:
            st.write("Start vergelijking... (simulatie)")
            st.success("Vergelijking klaar — wijzigingen: 3 paragrafen gewijzigd")
    else:
        st.write("Selecteer een tool om verder te gaan.")

def render_tender(assistant, tool):
    st.title(f"{assistant}")
    st.write("Specifieke workflows en templates voor tender-begeleiding.")
    st.write("Gekozen tool:", tool)
    st.button("Open tender-template (voorbeeld)")

# Dispatcher: wat renderen we in main area?
if st.session_state["main_nav"] == "Home":
    render_home()
elif st.session_state["main_nav"] == "Info":
    render_info()
elif st.session_state["main_nav"] == "Contact":
    render_contact()
elif st.session_state["main_nav"] == "Assistants":
    # Safety: als assistant None is, toon instructie
    chosen_assistant = st.session_state.get("assistant_nav", "General support")
    chosen_tool = st.session_state.get("tool_nav", "— Kies tool —")

    # render per assistant
    if chosen_assistant == "General support":
        render_general(chosen_assistant, chosen_tool)
    elif chosen_assistant == "Tender assistant":
        render_tender(chosen_assistant, chosen_tool)
    else:
        st.title(chosen_assistant)
        st.write("Content nog te implementeren voor deze assistent.")
else:
    st.write("Onbekende pagina.")
