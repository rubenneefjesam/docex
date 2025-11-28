# tools/object_counter/object_counter.py

import os
import base64
import json
import streamlit as st
from groq import Groq


# -----------------------------
# Helper: Groq client ophalen
# -----------------------------

def get_groq_client() -> Groq:
    """
    Maak en retourneer een Groq-client gebaseerd op een API key.

    - Eerst kijken naar env var GROQ_API_KEY
    - Anders proberen uit .streamlit/secrets.toml > [groq].api_key
    - Bij fouten of ontbrekende key: nette foutmelding + st.stop()
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if api_key:
        try:
            return Groq(api_key=api_key)
        except Exception as e:
            st.sidebar.error(f"❌ Fout bij verbinden met Groq API (env): {e}")
            st.stop()

    possible = [
        os.path.expanduser("~/.streamlit/secrets.toml"),
        os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
    ]
    api_key = ""
    if any(os.path.exists(p) for p in possible):
        try:
            api_key = st.secrets.get("groq", {}).get("api_key", "").strip()
        except Exception:
            api_key = ""

    if not api_key:
        st.sidebar.error(
            "❌ Groq API key niet gevonden. "
            "Zet GROQ_API_KEY als env var of maak `.streamlit/secrets.toml` "
            "met [groq] api_key = \"...\""
        )
        st.stop()

    try:
        return Groq(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()


# -----------------------------
# Core helpers
# -----------------------------

def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Converteer rauwe image bytes naar een base64-string.
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def count_objects_in_image(
    groq_client: Groq,
    image_bytes: bytes,
    image_mime: str,
    object_description: str,
) -> int:
    """
    Tel het aantal objecten op een afbeelding met een Groq vision-model.

    Parameters:
    - groq_client: Groq client instance
    - image_bytes: ruwe bytes van de geüploade afbeelding
    - image_mime: mimetype, bijv. "image/jpeg" of "image/png"
    - object_description: beschrijving van het type object dat geteld moet worden
      (bijv. "buizen", "rode veiligheidshelmen", "blauwe emmers")

    Retour:
    - Integer met het aantal gevonden objecten (0 bij fout).
    """
    if not image_bytes:
        return 0

    image_b64 = encode_image_to_base64(image_bytes)
    mime = image_mime or "image/jpeg"
    data_url = f"data:{mime};base64,{image_b64}"

    # Prompt: model in JSON-modus laten tellen
    prompt = (
        "You are an AI vision model that counts objects in images.\n"
        "Task: Count how many objects of a specific type appear in the image.\n\n"
        f"Only count objects that match this description: {object_description}.\n"
        "If you are unsure, return your best estimate.\n\n"
        "Respond strictly as a JSON object with this schema:\n"
        '{"count": <number_of_objects>}\n'
        "Do not include any extra keys or explanations."
    )

    try:
        completion = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        st.error(f"❌ Fout bij model-aanroep: {e}")
        return 0

    content = completion.choices[0].message.content

    # content zou een JSON-string moeten zijn door response_format=json_object
    try:
        if isinstance(content, str):
            data = json.loads(content)
        else:
            # fallback: als het een lijst/dict is, naar string converteren
            data = json.loads(str(content))
        count = int(data.get("count", 0))
        if count < 0:
            count = 0
        return count
    except Exception as e:
        st.warning(f"⚠️ Kon JSON-resultaat niet parsen: {e}")
        st.text(f"Ruwe model-output: {content}")
        return 0


# -----------------------------
# Streamlit UI - hoofdfunctie
# -----------------------------

def run(show_nav: bool = True):
    """
    Entrypoint voor de Streamlit-app voor objecttelling.

    Flow:
    - Upload een afbeelding (JPEG/JPG/PNG)
    - Beschrijf wat je wilt laten tellen (bijv. 'buizen', 'rode helmen')
    - Klik op 'Tel objecten'
    - Resultaat: het getelde aantal
    """
    st.set_page_config(
        page_title="Object Counter",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .stButton>button, .stDownloadButton>button {
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

    st.markdown("<div class='big-header'>🔢 Object Counter</div>", unsafe_allow_html=True)
    st.write(
        "Upload een foto (JPEG/JPG/PNG) en beschrijf welk type object je wilt laten tellen. "
        "De app stuurt de afbeelding naar een Groq vision-model en geeft het aantal terug."
    )

    groq_client = get_groq_client()

    col1, col2 = st.columns(2)
    image_bytes = None
    image_mime = None

    # --- Linkerkolom: afbeelding uploaden ---
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
                use_container_width=True,   # i.p.v. use_column_width (deprecated)
            )

    # --- Rechterkolom: objectbeschrijving + actie ---
    with col2:
        st.markdown("<div class='section-header'>🎯 Wat wil je laten tellen?</div>", unsafe_allow_html=True)
        object_description = st.text_input(
            "Beschrijf het object dat geteld moet worden",
            placeholder="Bijv. 'buizen', 'rode veiligheidshelmen', 'blauwe emmers'",
            key="obj_desc",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🔍 Tel objecten"):
            if not image_bytes:
                st.error("Upload eerst een afbeelding voordat je gaat tellen.")
            elif not object_description.strip():
                st.error("Voer een beschrijving in van het object dat je wilt laten tellen.")
            else:
                with st.spinner("Bezig met tellen..."):
                    count = count_objects_in_image(
                        groq_client=groq_client,
                        image_bytes=image_bytes,
                        image_mime=image_mime,
                        object_description=object_description.strip(),
                    )

                st.markdown("<div class='section-header'>✅ Resultaat</div>", unsafe_allow_html=True)
                st.write(
                    f"Ik heb **{count}** object(en) gevonden voor: "
                    f"**{object_description.strip()}**"
                )


if __name__ == "__main__":
    run()


def app():
    """
    Optionele wrapper voor een multi-page Streamlit setup.
    """
    st.header("🔢 Object Counter")
    st.write("Upload een afbeelding en laat Groq het aantal objecten tellen.")
    run(show_nav=False)
