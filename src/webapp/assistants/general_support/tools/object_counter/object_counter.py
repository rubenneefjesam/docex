# tools/object_counter/object_counter.py

import os
import base64
import io
import streamlit as st
from groq import Groq


# -----------------------------
# Helper: Groq client ophalen
# -----------------------------

def get_groq_client():
    """
    Maak en retourneer een Groq-client gebaseerd op een API key.

    Dit is dezelfde logica als in doc_generator:
    - Eerst kijken naar env var GROQ_API_KEY
    - Anders in .streamlit/secrets.toml naar [groq].api_key
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
            "Zet GROQ_API_KEY als env var of maak `.streamlit/secrets.toml` met [groq] api_key = \"...\""
        )
        st.stop()

    try:
        return Groq(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()


# -----------------------------
# Core: objecten tellen op een afbeelding
# -----------------------------

def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Converteer rauwe image-bytes naar een base64-string.
    Handig als je later een vision-API gebruikt die base64 verwacht.
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def count_objects_in_image(
    groq_client: Groq,
    image_bytes: bytes,
    object_description: str,
) -> int:
    """
    Tel het aantal objecten op een afbeelding.

    Parameters:
    - groq_client: een Groq-client (nu vooral placeholder als je Azure Vision/OpenAI gaat gebruiken)
    - image_bytes: de ruwe bytes van de geüploade afbeelding
    - object_description: natuurlijke taal beschrijving van wat je wilt tellen
      bijv. "rode veiligheidshelmen", "waterflessen", "blauwe containers"

    Retour:
    - Een integer: het aantal gedetecteerde objecten (of 0 als er iets misgaat)

    LET OP:
    --------
    Groq biedt op dit moment vooral text-only modellen. Voor échte vision
    heb je normaliter een vision-API nodig (bijv. Azure AI Vision of Azure OpenAI met gpt-4o).

    In de placeholder hieronder kun je:
    - Óf een call naar je eigen vision-service inbouwen,
    - Óf later Groq gebruiken zodra er een vision-model beschikbaar is.

    Voor nu:
    - De code is zo opgezet dat de Streamlit-UI klaar is.
    - In de gemarkeerde sectie kun je je daadwerkelijke vision-call plaatsen.
    """

    # Base64-string (handig voor Azure/OpenAI vision als je die wilt gebruiken)
    image_b64 = encode_image_to_base64(image_bytes)

    # -------------------------------------------------------------
    # TODO: Vervang deze placeholder door jouw echte vision-aanroep
    # -------------------------------------------------------------
    #
    # Voorbeeldschets (PSEUDOCODE voor Azure OpenAI vision):
    #
    # from openai import AzureOpenAI
    # client = AzureOpenAI(
    #     api_key="...",
    #     api_version="2024-02-01",
    #     azure_endpoint="https://<jouw-resource>.openai.azure.com/"
    # )
    #
    # response = client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[
    #         {
    #             "role": "system",
    #             "content": "Je bent een vision-model dat objecten telt. "
    #                        "Geef alleen een JSON-antwoord met een integer count."
    #         },
    #         {
    #             "role": "user",
    #             "content": [
    #                 {
    #                     "type": "text",
    #                     "text": (
    #                         f"Tel het aantal objecten op deze foto. "
    #                         f"Tel alleen: {object_description}. "
    #                         "Geef als antwoord alleen JSON: {\"count\": <getal>}."
    #                     ),
    #                 },
    #                 {
    #                     "type": "image_url",
    #                     "image_url": {
    #                         "url": f"data:image/jpeg;base64,{image_b64}"
    #                     },
    #                 },
    #             ],
    #         },
    #     ],
    #     temperature=0,
    # )
    #
    # raw_content = response.choices[0].message.content
    # # verwacht iets als: {"count": 7}
    # data = json.loads(raw_content)
    # return int(data.get("count", 0))
    #
    # -------------------------------------------------------------
    # Tijdelijke placeholder: we geven 0 terug en tonen een waarschuwing
    # -------------------------------------------------------------

    st.warning(
        "⚠️ De vision-logica voor het tellen van objecten is nog niet geïmplementeerd.\n\n"
        "Pas `count_objects_in_image` aan om je echte vision-API (bijv. Azure OpenAI / Azure Vision) aan te roepen."
    )
    return 0


# -----------------------------
# Streamlit UI - hoofdfunctie
# -----------------------------

def run(show_nav: bool = True):
    """
    Entrypoint voor de Streamlit-app voor object telling.

    Flow:
    - Upload een afbeelding (JPEG/JPG/PNG)
    - Geef een korte beschrijving van wat je wilt tellen (bijv. 'rode helmen')
    - Klik op 'Tel objecten'
    - Resultaat: aantal gedetecteerde objecten
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
        "Upload een foto (JPEG/JPG) en beschrijf welk type object je wilt laten tellen. "
        "De app stuurt de afbeelding naar een vision-model (nog te implementeren) en geeft het aantal terug."
    )

    # Groq-client alvast beschikbaar (voor later integratie)
    groq_client = get_groq_client()

    col1, col2 = st.columns(2)
    image_bytes = None
    with col1:
        st.markdown("<div class='section-header'>📸 Afbeelding uploaden</div>", unsafe_allow_html=True)
        img_file = st.file_uploader(
            "Kies een afbeelding (JPEG, JPG, PNG)",
            type=["jpg", "jpeg", "png"],
            key="obj_image",
        )
        if img_file:
            image_bytes = img_file.read()
            st.image(image_bytes, caption="Geüploade afbeelding", use_column_width=True)

    with col2:
        st.markdown("<div class='section-header'>🎯 Wat wil je laten tellen?</div>", unsafe_allow_html=True)
        object_description = st.text_input(
            "Beschrijf het object dat geteld moet worden",
            placeholder="Bijv. 'rode veiligheidshelmen', 'blauwe emmers', 'waterflessen'",
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
    Optionele wrapper voor een multi-page Streamlit setup (zoals bij doc_generator).
    """
    st.header("🔢 Object Counter")
    st.write("Upload een afbeelding en laat een vision-model het aantal objecten tellen.")
    run(show_nav=False)
