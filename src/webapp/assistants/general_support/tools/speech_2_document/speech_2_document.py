import os
import io
import streamlit as st
from groq import Groq
from docx import Document
import tempfile
import textwrap

# ─── Vereiste installatie (requirements.txt) ──────────────────────────
# Pip install:
# groq, python-docx, pydub
# en zorg dat ffmpeg in PATH staat

# ----------------------------------
# EntryPoint functie
# ----------------------------------
def run():
    # ─── Streamlit Page Config ─────────────────────────────────────────
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
            return Groq(api_key=key)
        except Exception:
            st.error("❌ Groq API key ongeldig.")
            return None

    client = init_groq_client()

    # ─── Navigatie met tabs ──────────────────────────────────────────────
    tabs = st.tabs(["Home", "Upload & Generate", "Over"])

    # Pagina: Home
    with tabs[0]:
        st.title("✨ Welkom bij Meeting2Document")
        st.markdown(
            """
            Deze tool zet je **meeting transcript** of **notities** om in een
            professioneel **vergaderverslag** (Word .docx).

            • Ga naar **Upload & Generate**
            • Upload je transcript (.txt) of audio (.wav, .mp3)
            • Klik op **Genereer verslag**
            • Download je .docx-verslag
            """
        )

    # Pagina: Upload & Generate
    with tabs[1]:
        st.title("📂 Upload je notities of audio")
        transcript_text = st.session_state.get("transcript_text", "")

        # Audio upload en transcriptie
        st.subheader("🎤 Upload audio (.wav, .mp3)")
        audio_file = st.file_uploader(
            label="Kies audiobestand",
            type=["wav", "mp3"],
            key="audio_uploader"
        )
        if audio_file and client:
            audio_data = audio_file.read()
            st.audio(audio_data, format=audio_file.type)
            st.info("Transcriberen audio…")
            try:
                res = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=(audio_file.name, audio_data)
                )
                transcript_text = res.text
                st.success("Transcriptie audio voltooid ✅")
                st.session_state["transcript_text"] = transcript_text
            except Exception as e:
                st.error(f"Transcriptie mislukt: {e}")

        # Tekst upload als fallback
        st.subheader("🗒️ Upload meeting transcript (.txt)")
        text_file = st.file_uploader(
            label="Kies je meeting transcript",
            type=["txt"],
            key="text_uploader"
        )
        if text_file:
            transcript_text = text_file.read().decode("utf-8", errors="ignore")
            st.session_state["transcript_text"] = transcript_text

        # Toon preview
        if transcript_text:
            st.subheader("📄 Transcript Preview")
            st.text_area("", transcript_text, height=200)

        # Generate knop
        if st.button("✅ Genereer vergaderverslag"):
            if not transcript_text:
                st.error("Upload eerst audio of transcriptie.")
            elif not client:
                st.error("Geen geldige Groq-client. Controleer je API-key.")
            else:
                st.info("Bezig met genereren, even geduld...")
                system_msg = "Je bent een assistent voor het maken van vergaderverslagen."
                user_msg = textwrap.dedent(f"""
                    Maak op basis van de volgende meeting transcriptie een gestructureerd verslag.
                    Gebruik kopjes: Samenvatting, Aanwezigen, Actiepunten, Besluiten.

                    Transcriptie:
                    {transcript_text}
                """)
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
                    if line.startswith("Samenvatting"):
                        doc.add_heading("Samenvatting", level=2)
                        content = line.split(":", 1)[1].strip() if ":" in line else line
                        doc.add_paragraph(content)
                    elif line.startswith("Aanwezigen"):
                        doc.add_heading("Aanwezigen", level=2)
                        content = line.split(":", 1)[1].strip() if ":" in line else line
                        doc.add_paragraph(content)
                    elif line.startswith("Actiepunten"):
                        doc.add_heading("Actiepunten", level=2)
                        content = line.split(":", 1)[1].strip() if ":" in line else line
                        doc.add_paragraph(content)
                    elif line.startswith("Besluiten"):
                        doc.add_heading("Besluiten", level=2)
                        content = line.split(":", 1)[1].strip() if ":" in line else line
                        doc.add_paragraph(content)
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

    # Pagina: Over
    with tabs[2]:
        st.title("ℹ️ Over deze tool")
        st.markdown(
            """
            Meeting2Document zet meetingnotities om in een professioneel verslag.

            **Features:**
            - Samenvatting van de meeting
            - Overzicht van aanwezigen
            - Lijst met actiepunten en besluiten
            - Ondersteuning voor audio (.wav, .mp3) met automatische transcriptie
            - Downloadbaar als Word-document
            """
        )

# ----------------------------------
# Script entry
# ----------------------------------
if __name__ == "__main__":
    run()