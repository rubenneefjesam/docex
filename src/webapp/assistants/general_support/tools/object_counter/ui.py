# tools/object_counter/ui.py

import streamlit as st
from .client import get_openai_client
from .vision import describe_image, count_objects_in_image


def run(show_nav: bool = True):
    st.set_page_config(
        page_title="Object Counter",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("<h1>🔢 Object Counter (OpenAI Vision)</h1>", unsafe_allow_html=True)
    st.write(
        "Upload een afbeelding. Het model analyseert automatisch wat er op staat, "
        "en je kunt daarna het gewenste object laten tellen."
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

    # Hou automatische tekst in session state
    if "auto_detect" not in st.session_state:
        st.session_state.auto_detect = ""

    # -----------------------------
    # Afbeelding upload
    # -----------------------------
    with col1:
        st.subheader("📸 Afbeelding uploaden")
        img = st.file_uploader(
            "Kies een afbeelding (JPEG/JPG/PNG)",
            type=["jpg", "jpeg", "png"],
            key="image_upload",
        )
        if img:
            image_bytes = img.read()
            image_mime = img.type or "image/jpeg"
            st.image(image_bytes, use_container_width=True)

            # Automatisch analyseren
            with st.spinner("🔍 Automatische analyse..."):
                desc = describe_image(openai_client, image_bytes, image_mime)

            # Save in session state
            st.session_state.auto_detect = desc

            st.success(f"**AI herkent op de afbeelding:**  
                        {desc}")

    # -----------------------------
    # Objectbeschrijving
    # -----------------------------
    with col2:
        st.subheader("🎯 Wat wil je laten tellen?")

        desc_input = st.text_input(
            "Objectbeschrijving",
            value=st.session_state.auto_detect,
            placeholder="Bijv. 'containers', 'buizen', 'helmen'",
            key="object_desc",
        )

        if st.button("🔍 Tel objecten"):
            if not image_bytes:
                st.error("Upload eerst een afbeelding.")
            elif not desc_input.strip():
                st.error("Voer een objectbeschrijving in.")
            else:
                with st.spinner("Bezig met tellen..."):
                    count = count_objects_in_image(
                        openai_client=openai_client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=desc_input.strip(),
                    )

                st.subheader("✅ Resultaat")
                st.write(
                    f"Ik heb **{count}** object(en) gevonden voor: **{desc_input}**"
                )


def app():
    run()
