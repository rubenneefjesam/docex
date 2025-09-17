import os
import streamlit as st
from groq import Groq
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import (
    extract_pdf_lines,
    full_text,
)

# ─── Groq-client init ────────────────────────────────────────────
@st.cache_resource
def init_groq_client():
    key = (
        os.getenv("GROQ_API_KEY", "").strip()
        or st.secrets.get("groq", {}).get("api_key", "").strip()
    )
    if not key:
        st.error("Geen Groq-API-key gevonden; stop.")
        return None
    return Groq(api_key=key)

client = init_groq_client()
if client is None:
    st.stop()

# ─── Configuratie ────────────────────────────────────────────────
CHAT_MODEL           = "llama-3.1-8b-instant"
MAX_PDF_MB           = 10
MAX_CHARS_PER_PROMPT = 30000  # limiet voor prompt-size

# ─── Document inladen & taggen ───────────────────────────────────
@st.cache_data(show_spinner=False)
def load_and_tag(pdf_bytes: bytes) -> str:
    """
    Extraheert per pagina de tekst, voegt [pX] tags toe, en returned 
    één grote string met getagde paragrafen.
    """
    pages = extract_pdf_lines(pdf_bytes)  # lijst van lijsten: per pagina regels
    tagged = []
    for pi, lines in enumerate(pages, start=1):
        for ln in lines:
            ln = ln.strip()
            if ln:
                tagged.append(f"[p{pi}] {ln}")
    return "\n".join(tagged)

# ─── Samenvatting maken ──────────────────────────────────────────
@st.cache_data(show_spinner=False)
def build_summary(tagged_text: str) -> str:
    snippet = tagged_text
    if len(snippet) > MAX_CHARS_PER_PROMPT:
        snippet = "\n".join(snippet.splitlines()[:5000])  # eerste X regels
    prompt = (
        "Je bent een beknopte documentassistent. Geef een korte samenvatting "
        "van de onderstaande tekst (max. 5 zinnen), zonder citaties:\n\n"
        f"{snippet}\n"
    )
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

# ─── Q&A prompt bouwen ───────────────────────────────────────────
def build_qa_prompt(tagged_text: str, question: str) -> str:
    snippet = tagged_text
    if len(snippet) > MAX_CHARS_PER_PROMPT:
        snippet = "\n".join(snippet.splitlines()[-5000:])  # laatste X regels
    return (
        "Je bent een behulpzame assistent. Gebruik **uitsluitend** de tekst hieronder. "
        "Beantwoord de vraag en geef NA je antwoord een lijst met bronvermeldingen "
        "in de vorm [pX], corresponderend met de gebruikte paragrafen.\n\n"
        f"{snippet}\n\n"
        f"Vraag: {question}\n"
        "Antwoord (gevolgd door citaties):"
    )

def ask_chat(prompt: str) -> str:
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

# ─── Streamlit UI ───────────────────────────────────────────────
def app():
    st.set_page_config(layout="wide")
    st.title("🗂️ Document Q&A & Samenvatting (zonder embeddings)")

    col1, col2 = st.columns([1,1])

    with col1:
        st.header("📥 Upload & Vraag")
        up = st.file_uploader("Upload PDF", type="pdf")
        if not up:
            st.info("Upload een PDF om te beginnen.")
            return
        if up.size > MAX_PDF_MB * 1024**2:
            st.error(f"Max bestandsgrootte is {MAX_PDF_MB} MB.")
            return

        pdf_bytes = up.getvalue()
        try:
            tagged = load_and_tag(pdf_bytes)
        except Exception as e:
            st.error(f"Fout bij PDF-verwerking: {e}")
            return

        st.success("Document geladen en getagd met paginanummers.")
        question = st.text_input("Stel je vraag")

        answer, citations = None, []
        if question:
            prompt = build_qa_prompt(tagged, question)
            with st.spinner("Bezig met beantwoorden…"):
                try:
                    raw = ask_chat(prompt)
                except Exception as e:
                    st.error(f"Fout bij chat-aanroep: {e}")
                    return
            # split het antwoord in twee delen: vóór de citaties en de citaties-lijst
            if "\n[" in raw:
                ans_part, cit_part = raw.split("\n[", 1)
                answer = ans_part.strip()
                # reconstruct list van [pX]
                citations = ["[" + c.strip("[] ") for c in cit_part.replace("]", "").split("[") if c]
            else:
                answer = raw
                citations = []

        with st.expander("🔍 Antwoord & Citaten", expanded=bool(question)):
            if not question:
                st.info("Typ een vraag om te starten.")
            else:
                st.markdown("**Antwoord:**")
                st.write(answer)
                if citations:
                    st.markdown("**Bronvermeldingen:**")
                    for c in citations:
                        st.markdown(f"- {c}")

    with col2:
        st.header("📝 Korte Samenvatting")
        if 'tagged' not in locals():
            st.info("Wacht op upload om samenvatting te tonen…")
        else:
            with st.spinner("Samenvatting genereren…"):
                try:
                    summary = build_summary(tagged)
                except Exception as e:
                    st.error(f"Fout bij samenvatting: {e}")
                    return
            st.markdown(summary)

if __name__ == "__main__":
    app()
