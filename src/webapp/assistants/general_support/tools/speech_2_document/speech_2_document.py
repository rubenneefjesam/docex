import os
import io
import streamlit as st
from groq import Groq
from docx import Document

# ─── Streamlit Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Meeting2Document",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Groq Client Initialisatie ─────────────────────────────────────────
def init_groq_client():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        key = st.secrets.get("groq", {}).get("api_key", "").strip()
    if not key:
        st.warning("⚠️ Geen Groq-key gevonden. Documentgeneratie werkt niet.")
        return None
    try:
        client = Groq(api_key=key)
        return client
    except Exception:
        st.error("❌ Groq API key ongeldig.")
        return None

client = init_groq_client()

# ─── Sidebar Navigatie ─────────────────────────────────────────────────
st.sidebar.title("📝 Meeting2Document Tool")
page = st.sidebar.radio(
    "📑 Pagina",
    ["Home", "Upload & Generate", "Over"]
)

# ─── Pagina: Home ───────────────────────────────────────────────────────
if page == "Home":
    st.title("✨ Welkom bij Meeting2Document")
    st.markdown(
        """
        Deze tool zet je **meeting transcript** of **notities** om in een
        professioneel **vergaderverslag** (Word .docx).

        • Ga naar **Upload & Generate**
        • Upload je transcript of notities (TXT)
        • Klik op **Genereer verslag**
        • Download je .docx-verslag
        """
    )

# ─── Pagina: Upload & Generate ─────────────────────────────────────────
elif page == "Upload & Generate":
    st.title("📂 Upload je notities / transcript")
    transcript_text = ""

    # Upload tekst
    uploaded = st.file_uploader(
        label="🗒️ Kies je meeting transcript (.txt)",
        type=["txt"],
        key="meeting_uploader"
    )
    if uploaded:
        transcript_text = uploaded.read().decode("utf-8", errors="ignore")
        st.subheader("📄 Transcript Preview")
        st.text_area("", transcript_text, height=200)

    # Generate knop
    if st.button("✅ Genereer vergaderverslag"):
        if not transcript_text:
            st.error("Upload eerst een transcript in TXT-formaat.")
        elif not client:
            st.error("Geen geldige Groq-client. Controleer je API-key.")
        else:
            st.info("Bezig met genereren, even geduld...")
            # Maak prompt
            system_msg = "Je bent een assistent voor het maken van vergaderverslagen."
            user_msg = (
                f"Maak op basis van de volgende meeting transcriptie een gestructureerd verslag."
                f" Gebruik kopjes: Samenvatting, Aanwezigen, Actiepunten, Besluiten."
                f" Transcriptie:\n{transcript_text}"
            )
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0.3,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            minutes = resp.choices[0].message.content.strip()
            st.subheader("🧾 Vergaderverslag")
            st.write(minutes)

            # Bouw Word-document
            buffer = io.BytesIO()
            doc = Document()
            for line in minutes.split("\n"):
                if line.strip().startswith("#"):
                    doc.add_heading(line.lstrip("# "), level=2)
                else:
                    doc.add_paragraph(line)
            doc.save(buffer)
            buffer.seek(0)

            st.download_button(
                label="⬇️ Download verslag (.docx)",
                data=buffer.read(),
                file_name="vergaderverslag.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

# ─── Pagina: Over ──────────────────────────────────────────────────────
elif page == "Over":
    st.title("ℹ️ Over deze tool")
    st.markdown(
        """
        Meeting2Document zet meetingnotities om in een professioneel verslag.

        **Features:**
        - Samenvatting van de meeting
        - Overzicht van aanwezigen
        - Lijst met actiepunten en besluiten
        - Downloadbaar als Word-document
        """
    )

# ─── End of App ───────────────────────────────────────────────────────
