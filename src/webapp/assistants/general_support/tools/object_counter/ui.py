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

    st.markdown(
        "<h1 style='margin-top:0'>🔢 Object Counter (OpenAI Vision)</h1>",
        unsafe_allow_html=True,
    )
    st.write(
        "Upload een afbeelding. Het model detecteert automatisch wat er te zien is. "
        "Daarna kun je het object laten tellen of zelf aanpassen."
    )

    # OpenAI client ophalen
    try:
        openai_client = get_openai_client()
    except Exception as e:
        st.error(f"❌ Kan OpenAI client niet initialiseren:\n\n{e}")
        return

    # Session state voor automatische detectie
    if "auto_detect" not in st.session_state:
        st.session_state.auto_detect = ""

    col_left, col_right = st.columns([1.2, 1])

    # -----------------------------
    # Upload sectie
    # -----------------------------
    with col_left:
        st.subheader("📸 Afbeelding uploaden")
        img = st.file_uploader(
            "Kies een afbeelding (JPEG, JPG, PNG)",
            type=["jpg", "jpeg", "png"],
            key="image_upload",
        )

        image_bytes = None
        image_mime = None

        if img:
            image_bytes = img.read()
            image_mime = img.type or "image/jpeg"

            st.image(image_bytes, use_container_width=True, caption=f"Geüploade afbeelding: {img.name}")

            # Automatisch analyseren
            with st.spinner("🔍 AI analyseert de afbeelding..."):
                detected_text = describe_image(openai_client, image_bytes, image_mime)

            # Opslaan
            st.session_state.auto_detect = detected_text

    # -----------------------------
    # Rechterkolom: detectie + invoerveld + tellen
    # -----------------------------
    with col_right:
        st.subheader("🎯 Wat wil je laten tellen?")

        if st.session_state.auto_detect:
            # AI detectie kaart
            st.markdown(
                f"""
                <div style="
                    padding: 12px 16px;
                    border: 1px solid #d3d3d3;
                    border-radius: 8px;
                    background: #f8f9fa;
                    margin-bottom: 12px;
                ">
                    <strong>🔍 AI detecteert:</strong><br>
                    {st.session_state.auto_detect}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Input met autosuggestie
        desc_input = st.text_input(
            "Beschrijf het object dat geteld moet worden",
            value=st.session_state.auto_detect,
            placeholder="Bijv. 'vierkanten', 'buizen', 'containers'",
            key="object_input",
        )

        # Tel-knop
        if st.button("🔢 Tel objecten", use_container_width=True):
            if not img:
                st.error("❌ Upload eerst een afbeelding.")
            elif not desc_input.strip():
                st.error("❌ Voer een objectbeschrijving in.")
            else:
                with st.spinner("Objecten tellen..."):
                    count = count_objects_in_image(
                        openai_client=openai_client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=desc_input.strip(),
                    )

                # Resultaat
                st.markdown("### ✅ Resultaat")
                st.write(
                    f"**AI waarneming:** {st.session_state.auto_detect}\n\n"
                    f"**Aantal getelde objecten voor ‘{desc_input}’:** {count}"
                )


def app():
    run()
