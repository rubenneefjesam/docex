import os
import re
import streamlit as st
import html
import uuid

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
# Model call: voeg comments toe
# ---------------------------
def _add_comments_with_llm(groq_client, code: str, language_hint: str | None):
    sys = (
        "Je bent een senior code reviewer. Voeg beknopte, nuttige inline comments toe "
        "in de bestaande code. Verander de code-structuur niet. Geef alleen de complete, "
        "becommentarieerde code terug, zonder uitleg en zonder markdown fences."
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

    # Pak grootste fenced code-blok indien aanwezig en strip fences
    fenced = re.findall(r"```(?:[\w+-]*)\n(.*?)```", content, flags=re.DOTALL)
    if fenced:
        content = max(fenced, key=len)
    content = content.replace("```", "").strip()
    return content


# ---------------------------
# Model call: vraag over code
# ---------------------------
def _ask_question_with_code(groq_client, code: str, question: str):
    sys = (
        "Je bent een behulpzame en technische code-reviewer. "
        "Krijg CODE en een VRAAG en antwoord concreet en praktisch. "
        "Verwijs waar nuttig naar regelnummers of korte voorbeelden."
    )

    code_ctx = code
    if len(code_ctx) > 20000:
        code_ctx = code_ctx[:20000] + "\n\n# ... (truncated)\n"

    prompt = f"""CODE:
{code_ctx}

VRAAG:
{question}

ANTWOORD:
"""

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"Fout bij model-aanroep: {e}"


# ---------------------------
# Pygments helper: produceer highlighted HTML (string)
# ---------------------------
def _get_highlighted_html(code: str, language: str | None = None, theme: str = "monokai", linenos: bool = False):
    if not PYGMENTS_AVAILABLE:
        return None

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
    return highlighted


# ---------------------------
# UI - hoofd
# ---------------------------
def app():
    st.markdown("<h2 style='margin-bottom:0.25rem'>🧑‍💻 Code Supporter</h2>", unsafe_allow_html=True)
    st.caption("Links: plak je broncode en genereer comments. Rechts: becommentarieerde code + QA.")

    # 2-koloms layout: left = input, right = output + QA
    col_left, col_right = st.columns([1, 1])

    # LEFT: input controls
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
            height=520,
            placeholder="Plak hier je broncode…"
        )
        gen = st.button("✨ Genereer comments", type="primary", disabled=not code_in.strip())

        theme = st.selectbox(
            "Weergave thema",
            ["monokai", "github", "solarized_dark", "native", "friendly"],
            index=0,
        )
        linenos = st.checkbox("Regelnummers tonen", value=False)

    # RIGHT: container voor code display en QA
    with col_right:
        st.write("**Resultaat**")
        code_display_container = st.container()  # code komt hierboven
        qa_container = st.container()  # QA komt onder de code

    # session state voor persistentie
    if 'code_out' not in st.session_state:
        st.session_state.code_out = ""
    if 'qa_answer' not in st.session_state:
        st.session_state.qa_answer = ""
    if 'last_question' not in st.session_state:
        st.session_state.last_question = ""

    # Genereer comments (LLM)
    if gen and code_in.strip():
        client = _get_groq_client()
        lang_hint = None if language == "(auto)" else language
        with st.spinner("Comments genereren…"):
            out = _add_comments_with_llm(client, code_in, lang_hint)
        st.session_state.code_out = out or "⚠️ Geen output ontvangen."
        # reset QA state bij nieuwe generatie
        st.session_state.qa_answer = ""
        st.session_state.last_question = ""

    # Render rechterkolom: eerst code (gehighlight), daarna QA UI
    with code_display_container:
        if st.session_state.code_out:
            code_text = st.session_state.code_out

            highlighted = _get_highlighted_html(code_text, language=(None if language == "(auto)" else language), theme=theme, linenos=linenos)

            unique_id = str(uuid.uuid4()).replace("-", "_")
            inner_id = f"code_inner_{unique_id}"
            copy_btn_id = f"copy_btn_{unique_id}"

            if highlighted:
                # render Pygments HTML + copy button (JS) inside this container
                safe_highlight = highlighted  # contains <div class="..."> with HTML
                html_snippet = f"""
                <div style="border-radius:6px; padding:8px; max-height:520px; overflow:auto; background: transparent;">
                  <div style="display:flex; align-items:flex-start; gap:10px;">
                    <div style="flex:1;">
                      <div id="{inner_id}">{safe_highlight}</div>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                      <button id="{copy_btn_id}" style="padding:8px 12px; border-radius:6px; background:#10B981; color:white; border:none; cursor:pointer;">
                        Kopieer code
                      </button>
                    </div>
                  </div>
                </div>
                <script>
                const btn = document.getElementById("{copy_btn_id}");
                const codeNode = document.getElementById("{inner_id}");
                btn.addEventListener("click", async () => {{
                    try {{
                        const text = codeNode.innerText;
                        await navigator.clipboard.writeText(text);
                        const old = btn.innerText;
                        btn.innerText = "Gekopieerd!";
                        setTimeout(()=>{{ btn.innerText = old }}, 1200);
                    }} catch (e) {{
                        alert("Kopiëren mislukt: " + e);
                    }}
                }});
                </script>
                """
                import streamlit.components.v1 as components
                # height tuned to number of lines (approx)
                height = 220 + min(800, code_text.count("\n") * 18)
                components.html(html_snippet, height=height, scrolling=True)
            else:
                # fallback plain pre + copy button
                escaped = html.escape(code_text)
                html_snippet = f"""
                <div style="border-radius:6px; padding:8px; max-height:520px; overflow:auto; background: transparent;">
                  <div style="display:flex; align-items:flex-start; gap:10px;">
                    <pre id="{inner_id}" style="margin:0; font-family: monospace; white-space: pre-wrap;">{escaped}</pre>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                      <button id="{copy_btn_id}" style="padding:8px 12px; border-radius:6px; background:#10B981; color:white; border:none; cursor:pointer;">
                        Kopieer code
                      </button>
                    </div>
                  </div>
                </div>
                <script>
                const btn = document.getElementById("{copy_btn_id}");
                const codeNode = document.getElementById("{inner_id}");
                btn.addEventListener("click", async () => {{
                    try {{
                        const text = codeNode.innerText;
                        await navigator.clipboard.writeText(text);
                        const old = btn.innerText;
                        btn.innerText = "Gekopieerd!";
                        setTimeout(()=>{{ btn.innerText = old }}, 1200);
                    }} catch (e) {{
                        alert("Kopiëren mislukt: " + e);
                    }}
                }});
                </script>
                """
                import streamlit.components.v1 as components
                height = 220 + min(800, code_text.count("\n") * 18)
                components.html(html_snippet, height=height, scrolling=True)
        else:
            st.info("Genereer eerst comments om hier de becommentarieerde code te zien.")

    # QA UI below the code (still in right column)
    with qa_container:
        st.markdown("---")
        st.markdown("### ❓ Stel een vraag over deze code")
        question = st.text_area("Type je vraag hier", height=100, placeholder="Bijv. 'Wat doet regel 20?' of 'Is deze functie thread-safe?'")
        ask = st.button("Vraag stellen", type="secondary", disabled=not st.session_state.code_out or not question.strip())

        if ask and question.strip():
            client = _get_groq_client()
            with st.spinner("Model antwoord aan het genereren…"):
                ans = _ask_question_with_code(client, st.session_state.code_out, question.strip())
            st.session_state.qa_answer = ans or "⚠️ Geen antwoord ontvangen."
            st.session_state.last_question = question.strip()

        if st.session_state.qa_answer:
            # Toon vraag+antwoord (laat zien welke vraag beantwoord is)
            st.markdown(f"**Vraag:** {st.session_state.last_question}")
            st.markdown("**Antwoord van de reviewer:**")
            st.write(st.session_state.qa_answer)
