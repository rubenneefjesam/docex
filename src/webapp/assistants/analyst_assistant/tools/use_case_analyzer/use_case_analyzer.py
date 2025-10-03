"""
Korte, robuuste Streamlit app: linkerkolom invoer -> Groq -> rechterkolom resultaat.
Werkt veilig als Groq niet aanwezig is (laat dan korte lokale fallback zien).
Run: export GROQ_API_KEY=... && streamlit run use_case_analyzer_short.py
"""

import os
import textwrap
import streamlit as st

# Optioneel: Groq importeren (veilig bij ontbreken)
try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    Groq = None
    _HAS_GROQ = False


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
            {"role": "system", "content": "Je bent een ervaren IT Business Analyst. Geef een nette, gestructureerde use-case in het Nederlands."},
            {"role": "user", "content": prompt},
        ],
    )
    # compat met Groq response
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


def build_prompt(short_input: str, include_acceptance: bool) -> str:
    extra = "Voeg acceptatiecriteria toe." if include_acceptance else "Geen acceptatiecriteria nodig."
    return textwrap.dedent(f"""
    Schrijf een volledige use-case in het Nederlands met duidelijke kopjes (Titel, Korte samenvatting,
    Scope, Actoren, Precondities, Hoofdscenario, Alternatieve flows, Acceptatiecriteria, Data & Integraties).

    Input: {short_input}

    {extra}
    """)


def app():
    st.set_page_config(page_title="Use Case Analyzer", layout="wide")
    st.title("📝 Use-case Analyzer (kort)")

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Invoer")
        user_input = st.text_area("Korte omschrijving (1–4 regels)", height=150, max_chars=600)
        include_acceptance = st.checkbox("Voeg acceptatiecriteria toe", value=True)
        if st.button("Schrijf use-case uit"):
            if not (user_input and user_input.strip()):
                st.warning("Vul eerst een korte omschrijving in.")
            else:
                prompt = build_prompt(user_input, include_acceptance)
                with st.spinner("Genereren via Groq…"):
                    try:
                        text = call_groq(prompt)
                    except Exception as e:
                        st.error(f"Groq mislukte: {e}. Gebruik lokale fallback.")
                        text = local_fallback(user_input)
                st.session_state["latest"] = text

    with right:
        st.subheader("Uitgewerkte use-case")
        out = st.session_state.get("latest")
        if out:
            st.markdown("---")
            st.write(out)
        else:
            groq_ok = bool(os.environ.get("GROQ_API_KEY", "").strip()) and _HAS_GROQ
            st.info("Klik links op 'Schrijf use-case uit' om te genereren.\nGroq beschikbaar: %s" % ("ja" if groq_ok else "nee"))


if __name__ == "__main__":
    app()

# exposeer eenvoudige descriptor voor registries die 'app' verwachten
app_descriptor = {"type": "streamlit", "module": __name__, "run_cmd": f"streamlit run {__file__}"}
