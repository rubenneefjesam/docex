# webapp/app.py

import sys
from pathlib import Path

# --- projectroot aan sys.path toevoegen ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# /* CUSTOM-UI: sidebar-green */
st.markdown(
    """
    <style>
    :root { --sidebar-width: 300px; }

    body::before{
        content: "";
        position: fixed;
        left: 0;
        top: 0;
        bottom: 0;
        width: var(--sidebar-width);
        background: linear-gradient(180deg,#16a34a 0%, #059669 100%) !important;
        z-index: 0;
        pointer-events: none;
    }

    .css-1d391kg, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        position: relative;
        z-index: 1;
    }

    [data-testid="stSidebar"] > div[role="complementary"],
    .css-1d391kg .css-1d391kg,
    .css-1d391kg .css-hi6a2p {
        background-color: transparent !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] *,
    .stSidebar * {
        color: #ffffff !important;
    }

    .stRadio label, .stRadio div, [data-testid="stSidebar"] .stRadio label {
        color: #ffffff !important;
    }

    input[type="radio"] + label, .stRadio > label {
        color: #ffffff !important;
    }

    [data-testid="stAppViewContainer"], .block-container {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    .stButton>button, .stDownloadButton>button {
        color: #000000 !important;
    }

    .css-1d391kg, [data-testid="stSidebar"] {
        min-width: var(--sidebar-width) !important;
        max-width: var(--sidebar-width) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# end marker

with st.sidebar:
    st.header("Assistent voor:")
    top_choice = st.radio("", ["General support", "Tender assistant", "Risk assistant", "Calculator assistant", "Legal assistant"], index=0)
    st.markdown("---")
    sub_choice = None

    if top_choice == "General support":
        st.subheader("Actieve tools")
        # detect which tools are available (do not raise if import fails)
        import importlib
        docgen_available = False
        coge_available = False
        try:
            importlib.import_module("tools.doc_generator")
            docgen_available = True
        except Exception:
            docgen_available = False
        try:
            importlib.import_module("tools.doc_comparison")
            coge_available = True
        except Exception:
            coge_available = False

        options = []
        if docgen_available:
            options.append("Document generator")
        if coge_available:
            options.append("Document comparison")

        if options:
            sub_choice = st.radio("Kies tool:", options, index=0)
        else:
            st.info("Geen tools geactiveerd voor General support.")
    else:
        st.info("Nog geen tools geconfigureerd voor deze assistant.")

    # Map the assistant/sub-choice to the legacy 'choice' used by the main page logic
    if top_choice == "General support":
        if sub_choice == "Document generator":
            choice = "Docgen"
        elif sub_choice == "Document comparison":
            choice = "Coge"
        else:
            choice = "Home"
    else:
        # show Home / placeholder for non-configured assistants
        choice = "Home"

if choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de **Document generator-app**. Kies een tool via de sidebar.")

elif choice == "Informatie":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write("Info: **Document generator** = Document generator, **Document comparison** = compare (placeholder).")

elif choice == "Document generator":
    docmod = load_tool_module_candidate(
        "tools.doc_generator.Document generator",
        "tools.plan_creator.dogen",
        "tools.doc_generator",
        "tools.plan_creator"
    )
    if docmod:
        try:
            call_first_callable(docmod)
        except Exception as e:
            st.error(f"Fout bij starten Document generator: {e}")
    else:
        st.error("Document generator module niet gevonden (controleer tools/doc_generator of tools/plan_creator)")

elif choice == "Document comparison":
    st.markdown("<h1 style=\'font-size:28px; font-weight:700\'>🔍 Document comparison</h1>", unsafe_allow_html=True)
    cogemod = load_tool_module_candidate(
        "tools.doc_comparison.Document comparison",
#         "tools.doc_comparison.Document comparison",
        "tools.doc_comparison"
    )
    if cogemod:
        try:
            call_first_callable(cogemod)
        except Exception as e:
            st.error(f"Fout bij starten Document comparison: {e}")
    else:
        st.error("Document comparison module niet gevonden (controleer tools/doc_comparison)")
