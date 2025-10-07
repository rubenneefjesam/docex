# use_case_analyzer.py
# Streamlit-app voor inladen, genereren en exporteren van use-case templates.
# Aangepaste versie: twee-koloms layout, copy-button, progress indicator, Groq optioneel.

import os
import re
import json
import textwrap
import io
from typing import Dict, Tuple, Optional, Any
import streamlit as st
import streamlit.components.v1 as components

# Optionele imports
try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    Groq = None
    _HAS_GROQ = False

# Regex voor placeholders {{ key }}
_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


# ---------------------------
# Helper / Core functies
# ---------------------------

def load_templates(templates_dir: str) -> Dict[str, str]:
    if not os.path.isdir(templates_dir):
        return {}
    templates = {}
    for fn in sorted(os.listdir(templates_dir)):
        path = os.path.join(templates_dir, fn)
        if fn.startswith('.') or not os.path.isfile(path):
            continue
        key = os.path.splitext(fn)[0]
        with open(path, encoding='utf-8') as f:
            templates[key] = f.read()
    return templates


def extract_placeholders(template_str: str) -> Tuple[str, ...]:
    found = _PLACEHOLDER_RE.findall(template_str)
    seen, ordered = set(), []
    for ph in found:
        if ph not in seen:
            seen.add(ph)
            ordered.append(ph)
    return tuple(ordered)


def render_template(template_str: str, context: Dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        return context.get(m.group(1), '')
    return _PLACEHOLDER_RE.sub(repl, template_str)


def _get_groq_client() -> Optional[Groq]:
    if not _HAS_GROQ:
        return None
    api_key = os.environ.get('GROQ_API_KEY', '').strip()
    try:
        api_key = api_key or st.secrets.get('groq', {}).get('api_key', '').strip()
    except Exception:
        pass
    if not api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


def _extract_first_json_object(s: str) -> Optional[str]:
    start = s.find('{')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None


def _resp_to_text(resp: Any) -> str:
    try:
        if hasattr(resp, 'choices'):
            choices = getattr(resp, 'choices')
            if choices and len(choices) > 0:
                choice = choices[0]
                msg = getattr(choice, 'message', None)
                if msg is not None:
                    content = getattr(msg, 'content', None)
                    if content:
                        return content
                content = getattr(choice, 'text', None) or getattr(choice, 'content', None)
                if content:
                    return content
        if isinstance(resp, dict):
            choices = resp.get('choices') or []
            if choices:
                c0 = choices[0]
                if isinstance(c0, dict):
                    msg = c0.get('message') or {}
                    content = msg.get('content') if isinstance(msg, dict) else None
                    if content:
                        return content
                    for key in ('text', 'content'):
                        if key in c0 and c0[key]:
                            return c0[key]
        return str(resp)
    except Exception:
        return str(resp)


def call_groq(prompt: str, model: str = 'llama-3.1-8b-instant', temperature: float = 0.2) -> str:
    client = _get_groq_client()
    if not client:
        raise RuntimeError('Groq client niet beschikbaar. Controleer GROQ_API_KEY in omgeving of st.secrets.')
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {'role': 'system', 'content': 'Je bent een ervaren IT Business Analyst.'},
                {'role': 'user', 'content': prompt}
            ]
        )
    except Exception as e:
        raise RuntimeError(f'Fout bij aanroepen van Groq API: {e}')
    return _resp_to_text(resp)


def local_generate_mapping(short_input: str, placeholders: Tuple[str, ...]) -> Dict[str, str]:
    first = short_input.strip().splitlines()[0] if short_input else 'Onbekende story'
    mapping = {}
    for ph in placeholders:
        low = ph.lower()
        if low == 'title':
            mapping[ph] = first
        elif low == 'role':
            mapping[ph] = 'Als gebruiker'
        elif low == 'goal':
            mapping[ph] = f'Wil ik {first.lower()} zodat ik waarde kan behalen.'
        elif low in ('steps', 'main_flow'):
            mapping[ph] = textwrap.dedent(
                '1. Gebruiker opent de feature.\n'
                '2. Gebruiker voert input in.\n'
                '3. Systeem valideert en bevestigt.\n'
                '4. Actie voltooid.'
            )
        else:
            mapping[ph] = first
    return mapping


def generate_for_template(short_input: str, template_name: str, templates_dir: str, use_groq: bool = True) -> Dict[str, str]:
    templates = load_templates(templates_dir)
    tpl = templates.get(template_name)
    if tpl is None:
        raise FileNotFoundError(f"Template '{template_name}' niet gevonden.")
    placeholders = extract_placeholders(tpl)
    if not placeholders:
        return {}
    data: Dict[str, str] = {}
    if use_groq:
        try:
            prompt = textwrap.dedent(f"""
                Geef **alleen** geldig JSON met velden: {', '.join(placeholders)}
                Template: {template_name}
                Omschrijving: {short_input}
            """)
            raw = call_groq(prompt)
            parsed = None
            try:
                parsed = json.loads(raw)
            except Exception:
                blob = _extract_first_json_object(raw)
                if blob:
                    try:
                        parsed = json.loads(blob)
                    except Exception:
                        parsed = None
            if isinstance(parsed, dict):
                data = {k: str(parsed.get(k, '')) for k in placeholders}
            else:
                st.session_state['last_groq_raw'] = raw
        except Exception as e:
            st.session_state['last_groq_error'] = str(e)
            st.session_state['last_groq_raw'] = st.session_state.get('last_groq_raw', '')
            data = {}
    # fallback voor ontbrekende velden
    missing = [ph for ph in placeholders if not data.get(ph)]
    if missing:
        data.update(local_generate_mapping(short_input, tuple(missing)))
    return data


def render_template_to_text(short_input: str, template_name: str, templates_dir: str, use_groq: bool = True) -> str:
    templates = load_templates(templates_dir)
    if template_name not in templates:
        raise FileNotFoundError(f"Template '{template_name}' niet gevonden.")
    data_map = generate_for_template(short_input, template_name, templates_dir, use_groq)
    tpl = templates[template_name]
    content = render_template(tpl, data_map)
    return content


# ---------------------------
# Small helper: copy-to-clipboard button using components.html
# ---------------------------

def copy_button_html(text: str, button_text: str = "Kopieer naar klembord", key: str = "copybtn"):
    # Escape for JS
    escaped = json.dumps(text)
    html = f"""
    <div>
      <button id="{key}">{button_text}</button>
    </div>
    <script>
    const btn = document.getElementById('{key}');
    btn.addEventListener('click', async () => {{
        const text = {escaped};
        try {{
            await navigator.clipboard.writeText(text);
            btn.innerText = 'Gekopieerd ✅';
            setTimeout(()=> btn.innerText = '{button_text}', 2000);
        }} catch (e) {{
            btn.innerText = 'Kopieer mislukt';
            setTimeout(()=> btn.innerText = '{button_text}', 2000);
        }}
    }});
    </script>
    """
    return html


# ---------------------------
# Streamlit UI: main page layout
# ---------------------------

def app():
    st.set_page_config(page_title='Use-case Analyzer', layout='wide')
    st.title('📋 Use-case Analyzer')
    st.markdown(
        '## Werkwijze  \n'
        '1. Selecteer een template  \n'
        '2. Vul een korte omschrijving in  \n'
        '3. Klik op **Genereer use-case**  \n'
        '4. Bekijk en kopieer het resultaat'
    )

    here = os.path.dirname(__file__)
    templates_dir = os.path.join(here, 'templates')
    templates = load_templates(templates_dir)
    if not templates:
        st.error("Geen templates in 'templates/'. Plaats .txt/.md templates in de templates-map.")
        return

    # layout: 2 kolommen - links input, rechts output
    left_col, right_col = st.columns([1, 1.1])

    with left_col:
        st.header("Input")
        choice = st.selectbox('Kies template', list(templates.keys()))
        desc = st.text_area('Korte omschrijving', height=180, placeholder="Omschrijf kort wat je wil: bv. 'Schrijf epic voor tender-indiening feature'")

        # Optioneel: toon status of Groq client beschikbaar is (voor transparantie)
        groq_available = _get_groq_client() is not None
        if groq_available:
            st.success("Groq LLM: beschikbaar (wordt gebruikt voor generatie).")
        else:
            st.info("Groq LLM: niet beschikbaar — er wordt lokaal gegenereerd als fallback.")

        gen = st.button('Genereer use-case')

    with right_col:
        st.header("Output")
        # Placeholder voor inhoud
        output_area = st.empty()
        # Placeholder voor copy button area
        copy_area = st.empty()
        # Optioneel debug expander
        debug_exp = st.expander("Debug / Groq info", expanded=False)
        with debug_exp:
            st.write("Als Groq iets teruggeeft of errors optreden, worden hier details getoond.")
            if 'last_groq_error' in st.session_state:
                st.error(st.session_state.get('last_groq_error'))
            if 'last_groq_raw' in st.session_state:
                st.caption("Raw Groq response:")
                st.code(st.session_state.get('last_groq_raw', ''), language='json')

    # Generatie flow met progress feedback
    if gen:
        # reset vorige debug info
        st.session_state.pop('last_groq_error', None)
        st.session_state.pop('last_groq_raw', None)

        progress = st.progress(0)
        status = st.empty()

        try:
            # stap 1: initialiseren
            status.info("Stap 1/4 — voorbereiden...")
            progress.progress(10)

            use_groq = groq_available  # automatisch gebruiken als beschikbaar, anders fallback

            # stap 2: verbinden / (indien Groq) check
            if use_groq:
                status.info("Stap 2/4 — verbinden met Groq en aanvragen voorbereiden...")
            else:
                status.info("Stap 2/4 — Groq niet beschikbaar, lokale generator wordt gebruikt...")
            progress.progress(30)

            # stap 3: generatie (kan langer duren)
            with st.spinner(text="Genereren — even geduld aub..."):
                status.info("Stap 3/4 — genereren (LLM of lokaal)...")
                # hier wordt de daadwerkelijke generatie gedaan
                content = render_template_to_text(desc, choice, templates_dir, use_groq=use_groq)
            progress.progress(70)

            # stap 4: render & tonen
            status.info("Stap 4/4 — renderen en tonen resultaat...")
            # toon content in code-block en geef copy button
            output_area.code(content, language='markdown')

            # copy button via components.html
            html = copy_button_html(content, button_text="Kopieer naar klembord", key=f"copy_{choice}")
            copy_area.components = components.html(html, height=50)

            progress.progress(100)
            status.success("Gereed — resultaat getoond. Gebruik de knop om te kopiëren.")
        except Exception as e:
            progress.progress(0)
            status.error(f'Fout tijdens generatie: {e}')
            # toon raw response / error indien aanwezig
            if 'last_groq_raw' in st.session_state:
                with st.expander('Raw Groq response (debug)'):
                    st.code(st.session_state.get('last_groq_raw', ''), language='json')
            if 'last_groq_error' in st.session_state:
                with st.expander('Groq error (debug)'):
                    st.write(st.session_state.get('last_groq_error'))

# Run app when file executed (useful for local streamlit run)
if __name__ == "__main__":
    app()
