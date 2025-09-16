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
    # Config
    st.set_page_config(page_title="Meeting2Document", page_icon="📝", layout="wide")
    st.title("📄 Meeting2Document")
    st.markdown("Deze tool zet je meeting transcript of notities om in een professioneel vergaderverslag (Word .docx).")

    # Uploaders in twee kolommen
    col1, col2 = st.columns(2)
    transcript_text = st.session_state.get("transcript_text", "")

    with col1:
        st.subheader("🎤 Upload audio (.wav, .mp3)")
        audio_file = st.file_uploader("Kies audiobestand", type=["wav","mp3"], key="audio_uploader")
        if audio_file and client:
            audio_data = audio_file.read()
            st.audio(audio_data, format=audio_file.type)
            st.info("Transcriberen audio…")
            try:
                res = client.audio.transcriptions.create(model="whisper-large-v3", file=(audio_file.name, audio_data))
                transcript_text = res.text
                st.success("Transcriptie voltooid ✅")
                st.session_state["transcript_text"] = transcript_text
            except Exception as e:
                st.error(f"Transcriptie mislukt: {e}")

    with col2:
        st.subheader("🗒️ Upload transcript (.txt)")
        text_file = st.file_uploader("Kies transcript", type=["txt"], key="text_uploader")
        if text_file:
            transcript_text = text_file.read().decode("utf-8", errors="ignore")
            st.session_state["transcript_text"] = transcript_text

    # Genereer knop
    if st.button("✅ Genereer verslag"):
        if not transcript_text:
            st.error("Upload eerst audio of transcriptie.")
        elif not client:
            st.error("Geen geldige Groq-client.")
        else:
            st.info("Genereren…")
            user_msg = textwrap.dedent(f"""
                Maak een gestructureerd vergaderverslag met kopjes: Samenvatting, Aanwezigen, Actiepunten, Besluiten.

                Transcriptie:
                {transcript_text}
            """)
            resp = client.chat.completions.create(model="llama-3.1-8b-instant", temperature=0.3,
                messages=[{"role":"system","content":"Assistent voor vergaderverslagen."},
                          {"role":"user","content":user_msg}])
            minutes = resp.choices[0].message.content.strip()
            st.markdown("## 🧾 Vergaderverslag")
            st.write(minutes)

            # Export Word
            buf = io.BytesIO()
            doc = Document()
            for line in minutes.split("\n"):
                if ":" in line:
                    title, body = line.split(":",1)
                    doc.add_heading(title.strip(), level=2)
                    doc.add_paragraph(body.strip())
                else:
                    doc.add_paragraph(line)
            doc.save(buf)
            buf.seek(0)
            st.download_button("⬇️ Download .docx", buf.read(), "verslag.docx",
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# Entry
if __name__ == "__main__":
    run()
    run()
