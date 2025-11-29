# tools/object_counter/ui_logic.py

import streamlit as st
from .client import get_openai_client
from .vision import describe_image, count_objects_in_image


def render_object_counter_ui():

    # OpenAI client ophalen
    try:
        client = get_openai_client()
    except Exception as e:
        st.error(f"❌ Kan OpenAI client niet initialiseren: {e}")
        return

    # Session state voor detectie
    if "auto_detect" not in st.session_state:
        st.session_state.auto_detect = ""
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

            # Alleen opnieuw detecteren bij nieuw bestand
            if st.session_state.uploaded_name != img_file.name:
                try:
                    with st.spinner("🔍 AI analyseert afbeelding..."):
                        detected = describe_image(
                            openai_client=client,
                            image_bytes=image_bytes,
                            image_mime=image_mime,
                        )
                    st.session_state.auto_detect = detected or "onbekend"
                    st.session_state.uploaded_name = img_file.name
                except Exception as e:
                    st.error(f"❌ Fout bij automatische detectie: {e}")
                    st.session_state.auto_detect = "onbekend"

    # -----------------------------
    # 2. Detectie + tellen
    # -----------------------------
    with col2:
        st.subheader("🎯 Waargenomen object")

        if st.session_state.auto_detect:
            st.markdown(
                f"""
                <div style="
                    padding: 12px;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    background: #f7f7f7;
                    margin-bottom: 16px;
                ">
                    <strong>🔍 AI detecteert:</strong><br>
                    {st.session_state.auto_detect}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Tel automatisch waargenomen object
        st.markdown("#### 1. Waargenomen object tellen")
        if st.button("🔢 Tel waargenomen object", use_container_width=True):
            if not image_bytes:
                st.error("Upload eerst een afbeelding.")
            else:
                with st.spinner("Objecten tellen..."):
                    count = count_objects_in_image(
                        openai_client=client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=st.session_state.auto_detect,
                    )
                st.success(f"Aantal (waargenomen object): {count}")

        st.markdown("---")

        # Aangepast object
        st.markdown("#### 2. Aangepast object tellen")

        custom_desc = st.text_input(
            "Aangepaste objectbeschrijving",
            placeholder="Bijv. 'buizen', 'platen', 'haken'",
        )

        if st.button("📏 Aangepast object tellen", use_container_width=True):
            if not image_bytes:
                st.error("Upload eerst een afbeelding.")
            elif not custom_desc.strip():
                st.error("Voer eerst een object in.")
            else:
                with st.spinner("Objecten tellen..."):
                    count = count_objects_in_image(
                        openai_client=client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=custom_desc.strip(),
                    )
                st.success(f"Aantal (‘{custom_desc}’): {count}")
