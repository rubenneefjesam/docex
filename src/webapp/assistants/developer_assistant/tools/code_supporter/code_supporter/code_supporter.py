import os
import re
import streamlit as st

# ---------------------------
# Groq client helper
# ---------------------------
def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        # probeer streamlit secrets
        try:
            api_key = st.secrets.get("groq", {}).get("api_key", "").strip()
        except Exception:
            api_key = ""
    if not api_key:
        st.sidebar.error("❌ Groq API key niet gevonden. Zet GROQ_API_KEY of voeg [groq].api_key toe aan .streamlit/secrets.toml")
        st.stop()

    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij Groq client: {e}")
        st.stop()

# ---------------------------
# Model call
# ---------------------------
def _add_comments_with_llm(groq_client, code: str, language_hint: str | None):
    """
    Vraagt de LLM om *dezelfde code terug te geven* maar met beknopte, nuttige inline comments.
    Output moet *puur code* zijn (geen markdown fences, geen uitleg).
    """
    # Heel korte, strakke instructie
    sys = (
        "Je bent een senior code reviewer. Voeg beknopte, nuttige comments toe "
        "in de bestaande code, zonder structuur te wijzigen. "
        "Geef uitsluitend de volledige, becommentarieerde code terug, zonder uitleg, "
        "zonder markdown of ``` fences."
    )
    # Eventuele hint (niet verplicht)
    hint = f" Programmeertaal: {language_hint}." if language_hint else ""

    prompt = f"""Voeg inline commentaar toe aan onderstaande code. Houd comments kort, technisch en relevant.{hint}

CODE:
{code}
"""

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        st.error(f"Fout bij model-aanroep: {e}")
        return ""

    # Soms sturen modellen toch ```…``` terug; strip die weg:
    # - verwijder alle ```...``` fences, pak de grootste code-sectie
    fenced = re.findall(r"```(?:[\w+-]*)\n(.*?)```", content, flags=re.DOTALL)
    if fenced:
        # neem de langste sectie
        content = max(fenced, key=len)

    # extra sanity: als er nog stray fences zijn
    content = content.replace("```", "").strip()
    return content

# ---------------------------
# UI
# ---------------------------
def app():
    st.markdown("<h2 style='margin-bottom:0.5rem'>🧑‍💻 Code Supporter</h2>", unsafe_allow_html=True)
    st.caption("Plak je code links, klik ‘Genereer comments’, en zie rechts het resultaat.")

    # Optioneel: page config hier niet doen als je elders ook set_page_config gebruikt
    col_left, col_right = st.columns(2)
    with col_left:
        language = st.selectbox(
            "Programmeertaal (optioneel, helpt het model):",
            ["(auto)", "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust", "PHP", "Kotlin", "Swift", "Bash", "SQL"],
            index=0
        )
        code_in = st.text_area(
            "Plak je code hier",
            height=420,
            placeholder="Plak hier je broncode…"
        )
        disabled = not code_in.strip()
        gen = st.button("✨ Genereer comments", type="primary", disabled=disabled)

    with col_right:
        st.write("**Resultaat**")
        result_placeholder = st.empty()

    # Actie
    if 'code_out' not in st.session_state:
        st.session_state.code_out = ""

    if gen and code_in.strip():
        client = _get_groq_client()
        lang_hint = None if language == "(auto)" else language
        with st.spinner("Comments genereren…"):
            out = _add_comments_with_llm(client, code_in, lang_hint)
        st.session_state.code_out = out or "⚠️ Geen output ontvangen."

    # Toon resultaat (ook na rerun)
    if st.session_state.code_out:
        # Toon als code-block (taal voor syntax highlight indien gekozen)
        lang = None if language == "(auto)" else language.lower()
        try:
            result_placeholder.code(st.session_state.code_out, language=lang)
        except Exception:
            result_placeholder.text(st.session_state.code_out)

        # Download-knopje
        ext_map = {
            "python": "py", "javascript": "js", "typescript": "ts",
            "java": "java", "c#": "cs", "c++": "cpp", "go": "go",
            "rust": "rs", "php": "php", "kotlin": "kt", "swift": "swift",
            "bash": "sh", "sql": "sql"
        }
        ext = ext_map.get((language or "").lower(), "txt")
        st.download_button(
            "⬇️ Download met comments",
            data=st.session_state.code_out.encode("utf-8"),
            file_name=f"code_with_comments.{ext}",
            mime="text/plain"
        )
PY
