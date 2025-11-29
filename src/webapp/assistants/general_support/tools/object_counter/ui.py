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
        "Upload een afbeelding. De app detecteert automatisch wat er te zien is. "
        "Daarna kun je het waargenomen object direct laten tellen of een aangepast object invoeren."
    )

    # OpenAI client
    try:
        openai_client = get_openai_client()
    except Exception as e:
        st.error(f"❌ Kan OpenAI client niet initialiseren:\n\n{e}")
        return

    # Session state voor automatische detectie
    if "auto_detect" not in st.session_state:
        st.session_state.auto_detect = ""

    col_left, col_right = st.columns([1.2, 1])

    # --------------------------------------------------
    # LINKERKOLOM: Afbeelding uploaden + automatische analyse
    # --------------------------------------------------
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

            st.image(
                image_bytes,
                use_container_width=True,
                caption=f"Geüploade afbeelding: {img.name}",
            )

            # Automatische AI-analyse
            with st.spinner("🔍 AI analyseert de afbeelding..."):
                detected_text = describe_image(
                    openai_client=openai_client,
                    image_bytes=image_bytes,
                    image_mime=image_mime,
                )

            st.session_state.auto_detect = detected_text or ""

    # --------------------------------------------------
    # RECHTERKOLOM: Waargenomen object + twee tell-flows
    # --------------------------------------------------
    with col_right:
        st.subheader("🎯 Waargenomen object")

        # Kaart met AI-waarneming
        if st.session_state.auto_detect:
            st.markdown(
                f"""
                <div style="
                    padding: 12px 16px;
                    border: 1px solid #d3d3d3;
                    border-radius: 8px;
                    background: #f8f9fa;
                    margin-bottom: 16px;
                ">
                    <strong>🔍 AI detecteert:</strong><br>
                    {st.session_state.auto_detect}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "Upload een afbeelding om automatisch te laten detecteren welk object er op staat."
            )

        # ------------------------------
        # 1. Automatisch waargenomen object tellen
        # ------------------------------
        st.markdown("#### 1. Automatisch waargenomen object tellen")

        auto_button_disabled = not (img and st.session_state.auto_detect)

        if st.button(
            "🔢 Tel waargenomen object",
            use_container_width=True,
            disabled=auto_button_disabled,
        ):
            if not img:
                st.error("❌ Upload eerst een afbeelding.")
            elif not st.session_state.auto_detect:
                st.error("❌ Er is nog geen automatisch waargenomen object.")
            else:
                with st.spinner("Objecten tellen op basis van AI-waarneming..."):
                    count = count_objects_in_image(
                        openai_client=openai_client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=st.session_state.auto_detect,
                    )

                st.markdown("### ✅ Resultaat")
                st.write(
                    f"**AI-waarneming:** {st.session_state.auto_detect}\n\n"
                    f"**Aantal getelde objecten (waargenomen object):** {count}"
                )

        st.markdown("---")

        # ------------------------------
        # 2. Aangepast object tellen
        # ------------------------------
        st.markdown("#### 2. Ander object tellen")

        custom_desc = st.text_input(
            "Beschrijf het object dat je wilt laten tellen",
            placeholder="Bijv. 'buizen', 'betonnen platen', 'haken'",
            key="custom_object_input",
        )

        if st.button("📏 Aangepast object tellen", use_container_width=True):
            if not img:
                st.error("❌ Upload eerst een afbeelding.")
            elif not custom_desc.strip():
                st.error("❌ Voer een objectbeschrijving in.")
            else:
                with st.spinner("Objecten tellen op basis van aangepaste beschrijving..."):
                    count = count_objects_in_image(
                        openai_client=openai_client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=custom_desc.strip(),
                    )

                st.markdown("### ✅ Resultaat")
                st.write(
                    f"**AI-waarneming:** {st.session_state.auto_detect or 'onbekend'}\n\n"
                    f"**Aantal getelde objecten voor ‘{custom_desc.strip()}’:** {count}"
                )


def app():
    run()
