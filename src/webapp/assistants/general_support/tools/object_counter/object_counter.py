# tools/object_counter/object_counter.py

import streamlit as st
from tools.object_counter.client import get_openai_client
from tools.object_counter.vision import count_objects_in_image


# -----------------------------------
# Streamlit UI
# -----------------------------------

def run(show_nav: bool = True):
    st.set_page_config(
        page_title="Object Counter",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .stButton>button {
            font-size:18px;
            font-weight:bold;
            padding:0.6em 1.2em;
        }
        .big-header {
            font-size:2.5rem;
            font-weight:bold;
            margin-bottom:0.3em;
        }
        .section-header {
            font-size:1.75rem;
            font-weight:600;
            margin-top:1em;
            margin-bottom:0.5em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='big-header'>🔢 Object Counter (OpenAI)</div>", unsafe_allow_html=True)
    st.write(
        "Upload een foto en beschrijf welk type object je wilt laten tellen. "
        "De app gebruikt het OpenAI Vision-model om objecten te tellen."
    )

    # OpenAI-client ophalen
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
        st.markdown("<div class='section-header'>📸 Afbeelding uploaden</div>", unsafe_allow_html=True)
        img_file = st.file_uploader(
            "Kies een afbeelding (JPEG, JPG, PNG)",
            type=["jpg", "jpeg", "png"],
            key="obj_image",
        )
        if img_file:
            image_bytes = img_file.read()
            image_mime = img_file.type or "image/jpeg"
            st.image(
                image_bytes,
                caption=f"Geüploade afbeelding: {img_file.name}",
                use_container_width=True,
            )

    # -----------------------------
    # Object description
    # -----------------------------
    with col2:
        st.markdown("<div class='section-header'>🎯 Wat wil je laten tellen?</div>", unsafe_allow_html=True)
        object_description = st.text_input(
            "Beschrijf het object dat geteld moet worden",
            placeholder="Bijv. 'hekpanelen', 'balken', 'buizen', 'helmen'",
            key="obj_desc",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🔍 Tel objecten"):
            if not image_bytes:
                st.error("Upload eerst een afbeelding voordat je gaat tellen.")
            elif not object_description.strip():
                st.error("Voer een beschrijving in van het object dat je wilt tellen.")
            else:
                # Vision call uitvoeren
                with st.spinner("Bezig met tellen..."):
                    count = count_objects_in_image(
                        openai_client=openai_client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=object_description.strip(),
                    )

                st.markdown("<div class='section-header'>✅ Resultaat</div>", unsafe_allow_html=True)
                st.write(
                    f"Ik heb **{count}** object(en) gevonden voor: "
                    f"**{object_description.strip()}**"
                )


# entrypoint voor standalone run
if __name__ == "__main__":
    run()


def app():
    """Voor jouw multipage Streamlit setup."""
    st.header("🔢 Object Counter")
    st.write("Upload een afbeelding en laat OpenAI Vision objecten tellen.")
    run(show_nav=False)
