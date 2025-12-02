# tools/object_counter/ui_logic.py

import streamlit as st
from .client import get_openai_client
from .vision import analyze_image, count_objects_in_image


def render_object_counter_ui():
    """
    UI voor de nieuwe Object Analyzer.
    Functienaam blijft hetzelfde omdat jij dat zo wilt.
    """

    # OpenAI client ophalen
    try:
        client = get_openai_client()
    except Exception as e:
        st.error(f"❌ Kan OpenAI client niet initialiseren: {e}")
        return

    # Session state
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "uploaded_name" not in st.session_state:
        st.session_state.uploaded_name = None

    col1, col2 = st.columns(2)

    # -----------------------------
    # 1. Upload gedeelte
    # -----------------------------
    with col1:
        st.subheader("📸 Afbeelding uploaden")
        img_file = st.file_uploader(
            "Kies een afbeelding (JPEG/JPG/PNG)",
            type=["jpg", "jpeg", "png"],
        )

        image_bytes = None
        image_mime = None

        if img_file:
            image_bytes = img_file.read()
            image_mime = img_file.type or "image/jpeg"

            st.image(
                image_bytes,
                caption=f"Geüploade afbeelding: {img_file.name}",
                use_container_width=True,
            )

            # Automatische analyse bij nieuwe upload
            if st.session_state.uploaded_name != img_file.name:
                try:
                    with st.spinner("🔍 AI analyseert afbeelding..."):
                        result = analyze_image(
                            openai_client=client,
                            image_bytes=image_bytes,
                            image_mime=image_mime,
                        )
                    st.session_state.analysis_result = result
                    st.session_state.uploaded_name = img_file.name

                except Exception as e:
                    st.error(f"❌ Fout bij AI-analyse: {e}")
                    st.session_state.analysis_result = None

    # -----------------------------
    # 2. Analyse tonen
    # -----------------------------
    with col2:
        st.subheader("🧠 Analyse resultaten")

        result = st.session_state.analysis_result

        if not result:
            st.info("Upload een afbeelding om een analyse te starten.")
            return

        # Objectnaam + confidence
        st.markdown(
            f"""
            <div style="
                padding: 12px;
                border: 1px solid #ccc;
                border-radius: 8px;
                background: #f7f7f7;
                margin-bottom: 16px;
            ">
                <strong>🔍 Object:</strong> {result['object']}<br>
                <strong>📊 Match:</strong> {result['confidence']}%
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Status + toelichting
        st.markdown(
            f"""
            <div style="
                padding: 12px;
                border: 1px solid #ccc;
                border-radius: 8px;
                background: #eef7ff;
                margin-bottom: 16px;
            ">
                <strong>📌 Status:</strong> {result['status']}<br>
                <strong>ℹ️ Toelichting:</strong> {result['status_description']}
            </div>
            """,
            unsafe_allow_html=True,
        )
