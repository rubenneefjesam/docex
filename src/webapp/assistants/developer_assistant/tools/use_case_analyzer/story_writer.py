"""
Korte Streamlit app met 'Denk mee' flow + Groq-genereerde vragen + .docx download.
- 'Denk mee' roept Groq aan om 3 vragen te genereren op basis van de korte invoer (2 multiple-choice, 1 open).
- Groq wordt gevraagd de vragen in JSON terug te geven zodat parsing eenvoudig is.
- Antwoorden kunnen worden ingevuld en daarna gebruik je 'Schrijf use case uit' om de use-case te genereren.
- Rechterkolom toont resultaat en biedt .docx-download.

Run: export GROQ_API_KEY=... && streamlit run use_case_analyzer_short.py
"""

import os
import io
import json
import textwrap
import streamlit as st

# Optioneel: Groq importeren (veilig bij ontbreken)
try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    Groq = None
    _HAS_GROQ = False

# Optioneel: python-docx (voor download). Niet fataal als afwezig.
try:
    from docx import Document
    _HAS_DOCX = True
except Exception:
    Document = None
    _HAS_DOCX = False


def get_groq_client():
    if not _HAS_GROQ:
        return None
    key = os.environ.get("GROQ_API_KEY", "").strip()
    try:
        key = key or st.secrets.get("groq", {}).get("api_key", "").strip()
    except Exception:
        pass
    if not key:
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        return None


def call_groq(prompt: str) -> str:
    client = get_groq_client()
    if not client:
        raise RuntimeError("Groq client niet beschikbaar of GROQ_API_KEY niet gezet")
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Je bent een ervaren IT Business Analyst. Antwoord precies zoals gevraagd."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


def local_fallback(short_input: str) -> str:
    short = (short_input or "").strip()
    title = short.splitlines()[0][:60] if short else "Onbekende use-case"
    return textwrap.dedent(f"""
    Titel: {title}

    Korte samenvatting:
    {short}

    Hoofdscenario:
    1. Gebruiker start en geeft gegevens op.
    2. Systeem valideert en bevestigt.
    3. Actie wordt uitgevoerd en opgeslagen.

    Acceptatiecriteria:
    - Einde-tot-einde workflow werkt.
    """)


def create_docx_from_text(title: str, content: str) -> bytes:
    if not _HAS_DOCX:
        # fallback: return plain text bytes
        return content.encode("utf-8")
    doc = Document()
    doc.add_heading(title or "Use-case", level=1)
    for block in content.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        first_line = block.splitlines()[0]
        if ":" in first_line and len(first_line) < 80:
            heading = first_line.rstrip(":")
            rest = "\n".join(block.splitlines()[1:]).strip()
            doc.add_heading(heading, level=2)
            if rest:
                for line in rest.split("\n"):
                    if line.strip():
                        doc.add_paragraph(line)
        else:
            for line in block.split("\n"):
                if line.strip():
                    doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# --- Groq-driven question generation

def generate_questions_via_groq(short_input: str) -> dict:
    """
    Vraag Groq om 3 vragen (2 multiple choice, 1 open) gebaseerd op de korte invoer.
    Verwacht JSON terug:
    {
      "q1": "Vraag tekst",
      "options1": ["opt1","opt2","opt3","opt4"],
      "q2": "Vraag tekst",
      "options2": ["opt1","opt2","opt3","opt4"],
      "q3": "Open vraag tekst"
    }
    """
    prompt = textwrap.dedent(f"""
    Geef drie korte vragen om een use-case te specificeren op basis van de volgende korte omschrijving.
    - Q1 en Q2 moeten multiple-choice zijn met maximaal 4 opties.
    - Q3 moet een open tekstvraag.
    - Retourneer uitsluitend geldige JSON (geen extra tekst) met de velden: q1, options1, q2, options2, q3.

    Input: {short_input}
    """)
    resp = call_groq(prompt)
    # probeer JSON te parsen; Groq kan soms extra tekst leveren — probeer substring van eerste '{' tot laatste '}'.
    try:
        start = resp.index('{')
        end = resp.rindex('}')
        json_text = resp[start:end+1]
        data = json.loads(json_text)
        # minimale validatie
        if not all(k in data for k in ("q1","options1","q2","options2","q3")):
            raise ValueError("Ontbrekende velden in Groq-output")
        return data
    except Exception:
        # fallback: statische vragen
        return {
            "q1": "Wat is het belangrijkste doel?",
            "options1": ["Automatisering","Informatievoorziening","Compliance","Anders"],
            "q2": "Welke impact schaal is relevant?",
            "options2": ["Team","Afdeling","Organisatie","Extern"],
            "q3": "Zijn er nog belangrijke opmerkingen of randvoorwaarden?"
        }


# --- Streamlit app

def app():
    st.set_page_config(page_title="Use Case Analyzer", layout="wide")
    st.title("📝 Use-case Analyzer — Denk mee (Groq) ")

    left, right = st.columns([1, 1])

    # session state defaults
    ss = st.session_state
    ss.setdefault("show_questions", False)
    ss.setdefault("questions", None)  # will hold dict with q1/options1/q2/options2/q3
    ss.setdefault("answers", {})
    ss.setdefault("latest", None)
    ss.setdefault("short_input", "")

    with left:
        st.subheader("Invoer")
        user_input = st.text_area("Korte omschrijving (1–4 regels)", height=120, max_chars=600, value=ss.short_input)
        ss.short_input = user_input

        if st.button("Denk mee"):
            if not (user_input and user_input.strip()):
                st.warning("Vul eerst een korte omschrijving in voordat je 'Denk mee' gebruikt.")
            else:
                with st.spinner("Vragen genereren via Groq…"):
                    try:
                        q = generate_questions_via_groq(user_input)
                        ss.questions = q
                        # default picks
                        ss.answers["q1_choice"] = q["options1"][0] if q.get("options1") else None
                        ss.answers["q2_choice"] = q["options2"][0] if q.get("options2") else None
                        ss.answers["q3_text"] = ""
                        ss.show_questions = True
                    except Exception as e:
                        st.error(f"Vragen genereren mislukt: {e}")
                        ss.questions = None
                        ss.show_questions = False

        if ss.show_questions and ss.questions:
            st.markdown("**Vragen om de use-case te specificeren**")
            q = ss.questions
            ss.answers["q1_choice"] = st.radio(q["q1"], q["options1"], index=0)
            ss.answers["q2_choice"] = st.radio(q["q2"], q["options2"], index=0)
            ss.answers["q3_text"] = st.text_area(q["q3"], height=80, value=ss.answers.get("q3_text",""))

            st.markdown("**Geselecteerde samenvatting**")
            st.write(f"Doel: **{ss.answers['q1_choice']}** — Impact: **{ss.answers['q2_choice']}**")
            if ss.answers.get("q3_text"):
                st.write(f"Opmerkingen: {ss.answers['q3_text']}")

            if st.button("Schrijf use case uit"):
                prompt = textwrap.dedent(f"""
                Schrijf een volledige use-case in het Nederlands met duidelijke kopjes (Titel, Korte samenvatting,
                Scope, Actoren, Precondities, Hoofdscenario, Alternatieve flows, Acceptatiecriteria, Data & Integraties).

                Input: {user_input}
                Context: Doel='{ss.answers['q1_choice']}', Impact='{ss.answers['q2_choice']}', Opmerkingen='{ss.answers.get('q3_text','')}'
                """)
                with st.spinner("Genereren via Groq…"):
                    try:
                        text = call_groq(prompt)
                    except Exception as e:
                        st.warning(f"Groq mislukte of niet beschikbaar: {e}. Lokale fallback wordt gebruikt.")
                        text = local_fallback(user_input)
                ss.latest = text

    with right:
        st.subheader("Uitgewerkte use-case")
        out = ss.latest
        if out:
            st.markdown("---")
            st.write(out)

            # download .docx
            title = ss.short_input.splitlines()[0][:60] if ss.short_input else "Use-case"
            docx_bytes = create_docx_from_text(title, out)
            st.download_button(
                label="⬇️ Download use-case (Word)",
                data=docx_bytes,
                file_name="use_case.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        else:
            groq_ok = bool(os.environ.get("GROQ_API_KEY", "").strip()) and _HAS_GROQ
            st.info("Klik links op 'Denk mee' om te starten.\nGroq beschikbaar: %s" % ("ja" if groq_ok else "nee"))


if __name__ == "__main__":
    app()

# Eenvoudige descriptor voor registries die 'app' verwachten
app_descriptor = {"type": "streamlit", "module": __name__, "run_cmd": f"streamlit run {__file__}"}