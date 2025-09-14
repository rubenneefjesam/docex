import streamlit as st
from pathlib import Path  # handig als je later templates/assets laadt

# -----------------------
# Config + defaults
# -----------------------
st.set_page_config(page_title="Document generator-app", layout="wide")

# veilige defaults (beste practice)
st.session_state.setdefault("main_nav", "Home")
st.session_state.setdefault("assistant_nav", "General support")
st.session_state.setdefault("tool_nav", "— Kies tool —")

# Optie: reset assistant/tool zodra je niet op 'Assistants' staat
RESET_ASSISTANT_ON_LEAVE = True

# -----------------------
# Opties / constanten
# -----------------------
PAGES = ["Home", "Assistants", "Info", "Contact"]
ASSISTANTS = [
    "General support",
    "Tender assistant",
    "Risk assistant",
    "Calculator assistant",
    "Legal assistant",
    "Project assistant",
    "Sustainability advisor",
]
TOOLS = ["— Kies tool —", "Document generator", "Document comparison"]

# -----------------------
# Helpers
# -----------------------
def safe_index(options, value, default=0):
    """Veilige index: return default als value niet in options staat."""
    try:
        return options.index(value)
    except ValueError:
        return default

# kleine helper voor path naar project root (optioneel)
ROOT = Path(__file__).resolve().parents[1]

# -----------------------
# Sidebar (navigatie)
# -----------------------
with st.sidebar:
    st.markdown("## Hoofdmenu")
    page_idx = safe_index(PAGES, st.session_state["main_nav"])
    page = st.radio("", options=PAGES, index=page_idx, key="main_nav")
    st.markdown("---")

    if st.session_state["main_nav"] == "Assistants":
        ass_idx = safe_index(ASSISTANTS, st.session_state["assistant_nav"])
        st.markdown("### Assistent voor:")
        assistant = st.radio("", options=ASSISTANTS, index=ass_idx, key="assistant_nav")

        tool_idx = safe_index(TOOLS, st.session_state["tool_nav"])
        st.markdown("### Kies tool:")
        tool = st.radio("", options=TOOLS, index=tool_idx, key="tool_nav")
    else:
        # optioneel resetten zodat oude keuzes niet blijven hangen
        if RESET_ASSISTANT_ON_LEAVE:
            st.session_state["assistant_nav"] = ASSISTANTS[0]
            st.session_state["tool_nav"] = TOOLS[0]
        assistant = None
        tool = None

# -----------------------
# Render-functies
# -----------------------
def render_header():
    # indien je een vaste header wil: logo, titel, kleine uitleg etc.
    col1, col2 = st.columns([1, 6])
    with col1:
        st.write("")  # ruimte voor logo: st.image(...)
    with col2:
        st.markdown("## Document generator-app")
        st.write("Kies links in het menu een pagina en, bij *Assistants*, een assistent en tool.")

def render_home():
    render_header()
    st.title("🏠 Home")
    st.write("Welkom bij de **Document generator-app**. Kies een assistent via het zijmenu.")
    st.markdown("---")
    st.subheader("Beschikbare assistenten")
    for a in ASSISTANTS:
        st.write(f"- {a}")
    st.info("Tip: ga naar *Assistants* in het zijmenu om per assistent specifieke tools en content te zien.")

def render_info():
    render_header()
    st.title("ℹ️ Info")
    st.write("Informatie over de app, versie en instructies.")
    st.write("- Versie: 1.0.0")
    st.write("- Auteur: Team X")
    st.write("- Documentatie: zie repo /docs")

def render_contact():
    render_header()
    st.title("📬 Contact")
    st.write("Support en contactinformatie.")
    st.write("- E-mail: support@example.com")
    st.write("- Interne chat: #ai-innovation")
    st.write("- Telefoon: 012-3456789")

# voorbeeld per-assistent content (breid uit per behoefte)
def render_general(assistant, tool):
    render_header()
    st.title(assistant)
    st.write("Korte omschrijving van General support.")
    st.write("Gekozen tool:", tool)

    if tool == "Document generator":
        with st.form("gen_form"):
            name = st.text_input("Documentnaam", value="nieuw_document.docx")
            prompt = st.text_area("Prompt / instructies", value="Maak een korte samenvatting van ...")
            submit = st.form_submit_button("Genereer document")
            if submit:
                # hier komt je generator-logica (simulatie placeholder)
                st.success(f"Document `{name}` gegenereerd (simulatie).")
                st.write("Prompt gebruikt:")
                st.code(prompt)
    elif tool == "Document comparison":
        st.write("Vergelijk twee documenten (PDF/DOCX) — upload hieronder:")
        col1, col2 = st.columns(2)
        with col1:
            doc_a = st.file_uploader("Upload document A", type=["pdf", "docx"], key="file_a")
        with col2:
            doc_b = st.file_uploader("Upload document B", type=["pdf", "docx"], key="file_b")
        if doc_a and doc_b:
            # plaats hier echte vergelijking; nu demo
            st.info("Bestanden geüpload — vergelijking wordt uitgevoerd (simulatie).")
            st.success("Vergelijking klaar — wijzigingen: 3 paragrafen gewijzigd (demo).")
    else:
        st.write("Selecteer een tool om verder te gaan.")

def render_tender(assistant, tool):
    render_header()
    st.title(assistant)
    st.write("Workflows en templates voor tender-begeleiding.")
    st.write("Gekozen tool:", tool)
    if st.button("Open tender-template (demo)"):
        st.write("Tender-template geopend (demo).")

# -----------------------
# Dispatcher (main area)
# -----------------------
current_page = st.session_state.get("main_nav", "Home")

if current_page == "Home":
    render_home()
elif current_page == "Info":
    render_info()
elif current_page == "Contact":
    render_contact()
elif current_page == "Assistants":
    chosen_assistant = st.session_state.get("assistant_nav", ASSISTANTS[0])
    chosen_tool = st.session_state.get("tool_nav", TOOLS[0])

    # kies rendering per assistent
    if chosen_assistant == "General support":
        render_general(chosen_assistant, chosen_tool)
    elif chosen_assistant == "Tender assistant":
        render_tender(chosen_assistant, chosen_tool)
    else:
        # fallback / placeholder
        render_header()
        st.title(chosen_assistant)
        st.write("Content nog te implementeren voor deze assistent.")
else:
    st.error("Onbekende pagina geselecteerd.")
