import os
import re
import streamlit as st

# Pygments (optioneel) voor mooie syntax highlighting in HTML
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except Exception:
    PYGMENTS_AVAILABLE = False

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
        st.sidebar.error(
            "❌ Groq API key niet gevonden. Zet GROQ_API_KEY of voeg [groq].api_key toe aan .streamlit/secrets.toml"
        )
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
    sys = (
        "Je bent een senior code reviewer. Voeg beknopte, nuttige comments toe "
        "in de bestaande code, zonder structuur te wijzigen. "
        "Geef uitsluitend de volledige, becommentarieerde code terug, zonder uitleg, "
        "zonder markdown of ``` fences."
    )
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

    # Soms sturen modellen toch ```…``` terug; pak de grootste code-sectie
    fenced = re.findall(r"```(?:[\w+-]*)\n(.*?)```", content, flags=re.DOTALL)
    if fenced:
        content = max(fenced, key=len)

    content = content.replace("```", "").strip()
    return content


# ---------------------------
# Pygments helper: toon als HTML met thema
# ---------------------------
def _show_highlighted(code: str, language: str | None = None, theme: str = "monokai", linenos: bool = False):
    """
    Render code as highlighted HTML using Pygments.
    - language: 'python','javascript',... of None -> probeer te raden
    - theme: Pygments style name (monokai, friendly, native, etc.)
    """
    if not PYGMENTS_AVAILABLE:
        # fallback
        try:
            st.code(code, language=language or None)
        except Exception:
            st.text(code)
        return

    # map user-facing names to pygments lexers where needed
    lang_map = {
        "c#": "csharp",
        "c++": "cpp",
        "js": "javascript",
        "ts": "typescript",
        "bash": "bash",
        "sql": "sql",
    }
    lexer = None
    if language and language != "(auto)":
        key = language.lower()
        key = lang_map.get(key, key)
        try:
            lexer = get_lexer_by_name(key)
        except Exception:
            lexer = None

    if lexer is None:
        try:
            lexer = guess_lexer(code)
        except Exception:
            lexer = TextLexer()

    formatter = HtmlFormatter(noclasses=True, style=theme, linenos=linenos)
    highlighted = highlight(code, lexer, formatter)

    # wrapper styling to mimic a VSCode-like panel and allow scrolling
    wrapper = f"""
    <div style="
        border-radius:8px;
        padding:12px;
        margin:6px 0;
        max-height:600px;
        overflow:auto;
    ">
      {highlighted}
    </div>
    """
    st.markdown(wrapper, unsafe_allow_html=True)


# ---------------------------
# UI
# ---------------------------
def app():
    st.markdown("<h2 style='margin-bottom:0.25rem'>🧑‍💻 Code Supporter</h2>", unsafe_allow_html=True)
    st.caption("Plak je code links, klik ‘Genereer comments’, en zie rechts het resultaat.")

    col_left, col_right = st.columns(2)
    with col_left:
        language = st.selectbox(
            "Programmeertaal (optioneel, helpt het model):",
            [
                "(auto)", "Python", "JavaScript", "TypeScript", "Java",
                "C#", "C++", "Go", "Rust", "PHP", "Kotlin", "Swift", "Bash", "SQL"
            ],
            index=0,
            help="Kies (auto) om automatisch te laten detecteren."
        )
        code_in = st.text_area(
            "Plak je code hier",
            height=420,
            placeholder="Plak hier je broncode…"
        )
        disabled = not code_in.strip()
        gen = st.button("✨ Genereer comments", type="primary", disabled=disabled)

        # extra: thema keuze voor weergave
        theme = st.selectbox(
            "Weergave thema",
            ["monokai", "github", "solarized_dark", "native", "friendly"],
            index=0,
            help="Thema voor syntax highlighting (monokai lijkt op veel IDE-thema's)."
        )
        linenos = st.checkbox("Regelnummers tonen", value=False)

    with col_right:
        st.write("**Resultaat**")
        result_placeholder = st.empty()

    # Actie state
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
        # toon met Pygments HTML (mooi, themable) of fallback
        lang_for_display = None if language == "(auto)" else language
        try:
            # gebruik onze helper die fallbackt naar st.code als pygments niet beschikbaar is
            _show_highlighted(st.session_state.code_out, language=lang_for_display, theme=theme, linenos=linenos)
        except Exception:
            # laatste redmiddel
            try:
                result_placeholder.code(st.session_state.code_out, language=(language.lower() if language != "(auto)" else None))
            except Exception:
                result_placeholder.text(st.session_state.code_out)

        # Download-knop (blijft plain text)
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
