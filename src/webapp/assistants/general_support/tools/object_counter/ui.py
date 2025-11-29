# tools/object_counter/ui.py

import streamlit as st
from .client import get_openai_client
from .vision import count_objects_in_image


def run(show_nav: bool = True):
    st.set_page_config(
        page_title="Object Counter",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("<h1>🔢 Object Counter (OpenAI Vision)</h1>", unsafe_allow_html=True)
    st.write(
        "Upload een afbeelding en laat het OpenAI Vision-model individuele objecten tellen."
    )

    # OpenAI client ophalen
    try:
        openai_client = get_openai_client()
    except Exception as e:
        st.error(f"❌ Kan OpenAI client niet initialiseren: {e}")
        return

    col1, col2 = st.columns(2)

    image_bytes = None
    image_mime = None

    # -----------------------------
    # Afbeelding upload
    # -----------------------------
    with col1:
        st.subheader("📸 Afbeelding uploaden")
        img = st.file_uploader(
            "Kies een afbeelding (JPEG/JPG/PNG)",
            type=["jpg", "jpeg", "png"],
        )
        if img:
            image_bytes = img.read()
            image_mime = img.type or "image/jpeg"
            st.image(image_bytes, use_container_width=True)

    # -----------------------------
    # Objectbeschrijving
    # -----------------------------
    with col2:
        st.subheader("🎯 Wat wil je laten tellen?")
        desc = st.text_input(
            "Objectbeschrijving",
            placeholder="Bijv. 'hekpanelen', 'buizen', 'rode helmen'"
        )

        if st.button("🔍 Tel objecten"):
            if not image_bytes:
                st.error("Upload eerst een afbeelding.")
            elif not desc.strip():
                st.error("Voer een objectbeschrijving in.")
            else:
                with st.spinner("Bezig met tellen..."):
                    count = count_objects_in_image(
                        openai_client=openai_client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=desc.strip(),
                    )

                st.subheader("✅ Resultaat")
                st.write(f"Ik heb **{count}** object(en) gevonden voor: **{desc}**")


def app():
    run()
