import os
import streamlit as st
from pathlib import Path
from groq import Groq
from PyPDF2 import PdfReader
import docx

# ─── Groq Client Initialisatie ───────────────────────────────────
@st.cache_resource
def init_groq_client():
    key = (
        os.getenv("GROQ_API_KEY", "").strip()
        or st.secrets.get("groq", {}).get("api_key", "").strip()
    )
    if not key:
        st.error("⚠️ Geen Groq-API-key gevonden; samenvatting werkt niet.")
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        st.error("❌ Ongeldige Groq-API-key.")
        return None

client = init_groq_client()

# ─── Bestandstekst Inlezen ────────────────────────────────────────
def read_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        document = docx.Document(str(file_path))
        return "\n".join(p.text for p in document.paragraphs)
    elif suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Onbekend bestandstype: {suffix}")

# ─── Samenvatting via Groq LLM ────────────────────────────────────
def generate_summary(text: str) -> str:
    prompt = (
        "Je bent een documentassistent. Maak een heldere, gestructureerde samenvatting van de onderstaande tekst. "
        "Gebruik bulletpoints voor de belangrijkste punten en cursieve tekst voor opvallende bevindingen of waarschuwingen."
        f"\nTekst:\n{text[:4000]}\n"
        "Geef de output als markdown-formaat, zonder extra toelichting."
    )
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    # Strip mogelijke code fences
    if raw.startswith("```"):
        raw = raw.strip('`')
    return raw

# ─── Streamlit UI ──────────────────────────────────────────────────
def app():
    st.set_page_config(page_title="📄 Document Summarizer (Groq)", layout="wide")
    st.title("📄 Document Summarizer")
    st.write("Upload documenten en klik op ‘Genereer samenvatting’ om een gestructureerde samenvatting te ontvangen.")

    uploads = st.file_uploader(
        "Upload PDF / DOCX / TXT / MD", type=["pdf", "docx", "txt", "md"], accept_multiple_files=True
    )
    if not uploads:
        st.info("Nog geen bestanden geüpload.")
        return

    if not st.button("🚀 Genereer samenvatting via Groq"):
        return

    for uf in uploads:
        tmp = Path(f"/tmp/{uf.name}")
        tmp.write_bytes(uf.getvalue())
        text = read_text(tmp)
        summary = generate_summary(text)

        with st.expander(f"📘 {uf.name}", expanded=True):
            st.markdown(summary)
            # Download als markdown
            st.download_button(
                label="⬇️ Download Samenvatting",
                data=summary.encode("utf-8"),
                file_name=f"{uf.name}_summary.md",
                mime="text/markdown"
            )

if __name__ == '__main__':
    app()