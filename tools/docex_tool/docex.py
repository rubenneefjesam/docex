def run(show_nav: bool = True):
    steps.clear_steps()
    # let the outer app decide page config; keep it for standalone run
    st.set_page_config(page_title="DOCX Generator", layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        .stButton>button, .stDownloadButton>button {font-size:18px; font-weight:bold; padding:0.6em 1.2em;}
        .big-header {font-size:2.5rem; font-weight:bold; margin-bottom:0.3em;}
        .section-header {font-size:1.75rem; font-weight:600; margin-top:1em; margin-bottom:0.5em;}
        .stTextArea textarea {font-family:monospace;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    groq_client = get_groq_client()
    steps.record_step("Groq client aangemaakt")

    # If the calling app wants the tool's own navigation, show it.
    # Otherwise default to Generator page so the tool area is shown immediately.
    if show_nav:
        page = st.sidebar.radio("🔖 Navigatie", ("Home", "Generator", "Info"), index=0)
    else:
        page = "Generator"

    if page == "Home":
        st.markdown("<div class='big-header'>🏠 Welkom bij de DOCX Generator</div>", unsafe_allow_html=True)
        st.markdown(
            """
            Gebruik deze tool om snel **Word-templates** bij te werken met **nieuwe context**.
            
            - Ga naar **Generator**
            - Upload je **template** en **context**
            - Klik op **Genereer aangepast document**
            - Download en behoud je opmaak!
            """,
            unsafe_allow_html=True,
        )

    elif page == "Generator":
        st.markdown("<div class='big-header'>🚀 Generator</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        tpl_path = None
        context = ""
        with col1:
            st.markdown("<div class='section-header'>📄 Template Upload</div>", unsafe_allow_html=True)
            tpl_file = st.file_uploader("Kies .docx template", type="docx", key="tpl")
            if tpl_file:
                tpl_path_dir = tempfile.mkdtemp()
                tpl_path = os.path.join(tpl_path_dir, "template.docx")
                with open(tpl_path, "wb") as f:
                    f.write(tpl_file.getbuffer())
                tpl_text = _safe_read_docx_text(tpl_path)
                st.text_area("Template-inhoud", tpl_text, height=250, key="tpl_pre")
                steps.record_step("Template geüpload")
        with col2:
            st.markdown("<div class='section-header'>📝 Context Upload</div>", unsafe_allow_html=True)
            ctx_file = st.file_uploader("Kies .docx/.txt context", type=["docx", "txt"], key="ctx")
            if ctx_file:
                tmp_c = tempfile.mkdtemp()
                if ctx_file.type and ctx_file.type.endswith("document"):
                    cpath = os.path.join(tmp_c, "context.docx")
                    with open(cpath, "wb") as f:
                        f.write(ctx_file.getbuffer())
                    context = _safe_read_docx_text(cpath)
                    steps.record_step("Context (.docx) geüpload")
                else:
                    context = ctx_file.read().decode("utf-8", errors="ignore")
                    steps.record_step("Context (.txt) geüpload")
                st.text_area("Context-inhoud", context, height=250, key="ctx_pre")

    else:
        st.markdown("<div class='big-header'>ℹ️ Info & Tips</div>", unsafe_allow_html=True)
        st.markdown(
            """
            **Tips voor optimaal gebruik:**
            - Zorg voor unieke, duidelijke tekstfragmenten.
            - Houd context-bestanden kort en concreet.
            - Controleer altijd de uiteindelijke output.
            - Voor complexe documenten kun je secties apart bijwerken.
            """,
            unsafe_allow_html=True,
        )

    # Sidebar: uitvoerbare stappen (altijd tonen in de shared sidebar)
    st.sidebar.markdown("### Uitgevoerde stappen")
    for s in steps.get_steps():
        st.sidebar.markdown(f"- {s}")

if __name__ == "__main__":
    run()
