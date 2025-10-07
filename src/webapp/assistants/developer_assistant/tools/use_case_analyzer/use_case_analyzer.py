# use_case_analyzer.py
# Streamlit-app voor inladen, genereren en exporteren van use-case templates.
# Aangepaste versie: Groq mag optioneel zijn — als beschikbaar geeft Groq een volledig ingevulde template terug.
# UI: 2 kolommen, links input, rechts output. Geen copy/download-knop en geen "gereed"-banner.

import os
import re
import json
import textwrap
from typing import Dict, Tuple, Optional, Any
import streamlit as st

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
    """Robuuste extractie van tekst uit diverse SDK response vormen."""
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


def _strip_code_fence(s: str) -> str:
    """Verwijder eventueel aanwezige markdown code fences en trimming."""
    if not isinstance(s, str):
        return str(s)
    s = s.strip()
    # verwijder triple backticks met mogelijke language hint
    if s.startswith("```") and s.endswith("```"):
        # verwijder eerste line (code fence) en laatste line
        parts = s.splitlines()
        # vind eerste line not empty after fence
        if len(parts) >= 3:
            inner = "\n".join(parts[1:-1])
            return inner.strip()
    # ook verwijder enkelvoudige backticks en quotes (veilig)
    return s


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
    text = _resp_to_text(resp)
    return _strip_code_fence(text)


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


def generate_filled_template_with_groq(short_input: str, template_str: str, template_name: str, placeholders: Tuple[str, ...]) -> Optional[str]:
    """
    Vraag Groq om **de volledig ingevulde template** terug te geven.
    Retourneert de ingevulde template als string, of None als Groq faalt.
    """
    try:
        # Construct prompt: geef zowel de template als de placeholders en omschrijving
        # Geef duidelijke instructie om alleen de ingevulde template terug te geven, zonder extra uitleg.
        prompt = textwrap.dedent(f"""
            Je krijgt hieronder een template met placeholders in de vorm {{ {{ key }} }}.
            Vul het template volledig in op basis van de korte omschrijving. 
            Geef **alleen** de ingevulde template terug — geen uitleg, geen extra commentaar, en behoud de structuur van het template.
            
            Template naam: {template_name}
            
            Template:
            {template_str}
            
            Placeholder keys: {', '.join(placeholders) if placeholders else '(geen)'}
            
            Omschrijving:
            {short_input}
        """)
        raw = call_groq(prompt)
        # raw is de ingevulde template (of iets wat er op lijkt). Strip code fences en return.
        return raw.strip()
    except Exception as e:
        # bewaar debug info voor UI, maar return None zodat fallback gebruikt wordt.
        st.session_state['last_groq_error'] = str(e)
        st.session_state['last_groq_raw'] = st.session_state.get('last_groq_raw', '')
        return None


def generate_for_template(short_input: str, template_name: str, templates_dir: str, use_groq: bool = True) -> str:
    """
    Genereer de uiteindelijke content voor een template.
    Als Groq beschikbaar is en use_groq=True, probeer Groq de volledige ingevulde template te laten retourneren.
    Anders: vul lokaal placeholders in (via JSON/Groq-JSON-fallback of local mapping).
    Retourneert de finally-rendered tekst.
    """
    templates = load_templates(templates_dir)
    tpl = templates.get(template_name)
    if tpl is None:
        raise FileNotFoundError(f"Template '{template_name}' niet gevonden.")
    placeholders = extract_placeholders(tpl)

    # 1) Probeer Groq volledige template te laten invullen
    if use_groq and _get_groq_client() is not None:
        filled = generate_filled_template_with_groq(short_input, tpl, template_name, placeholders)
        if filled:
            return filled
        # anders: fallback naar lokale route (en debug info is in session_state)

    # 2) Lokale route: probeer eerst Groq JSON aanpak (oude gedrag) indien Groq beschikbaar maar vul niet de hele template
    data: Dict[str, str] = {}
    if use_groq and _get_groq_client() is not None:
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

    # 3) Vul ontbrekende placeholders lokaal
    missing = [ph for ph in placeholders if not data.get(ph)]
    if missing:
        data.update(local_generate_mapping(short_input, tuple(missing)))

    # 4) Render met lokale mapping
    content = render_template(tpl, data)
    return content


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
        '4. Bekijk het resultaat aan de rechterkant'
    )

    here = os.path.dirname(__file__)
    templates_dir = os.path.join(here, 'templates')
    templates = load_templates(templates_dir)
    if not templates:
        st.error("Geen templates in 'templates/'. Plaats .txt/.md templates in de templates-map.")
        return

    # layout: 2 kolommen - links input + knop, rechts output (alleen weergave)
    left_col, right_col = st.columns([1, 1.1])

    with left_col:
        st.header("Input")
        choice = st.selectbox('Kies template', list(templates.keys()))
        desc = st.text_area('Korte omschrijving', height=180, placeholder="Omschrijf kort wat je wil: bv. 'Schrijf epic voor tender-indiening feature'")

        gen = st.button('Genereer use-case')

    with right_col:
        st.header("Output")
        output_placeholder = st.empty()
        debug_exp = st.expander("Debug / Groq info", expanded=False)
        with debug_exp:
            st.write("Als Groq iets teruggeeft of errors optreden, worden hier details getoond.")
            if 'last_groq_error' in st.session_state:
                st.error(st.session_state.get('last_groq_error'))
            if 'last_groq_raw' in st.session_state:
                st.caption("Raw Groq response:")
                st.code(st.session_state.get('last_groq_raw', ''), language='json')

    if gen:
        # reset vorige debug info
        st.session_state.pop('last_groq_error', None)
        st.session_state.pop('last_groq_raw', None)

        progress = st.progress(0)
        status = st.empty()

        try:
            status.info("Stap 1/4 — voorbereiden...")
            progress.progress(10)

            # bepaal of Groq zal worden gebruikt (automatisch als beschikbaar)
            use_groq = _get_groq_client() is not None

            if use_groq:
                status.info("Stap 2/4 — aanroepen van LLM (groq)...")
            else:
                status.info("Stap 2/4 — Groq niet beschikbaar, lokale generatie wordt gebruikt...")
            progress.progress(35)

            # Stap 3: generatie (LLM of lokaal)
            with st.spinner(text="Genereren — even geduld aub..."):
                status.info("Stap 3/4 — genereren...")
                content = generate_for_template(desc, choice, templates_dir, use_groq=use_groq)
            progress.progress(70)

            # Stap 4: tonen (in rechterkolom)
            status.info("Stap 4/4 — tonen resultaat...")
            output_placeholder.code(content, language='markdown')
            progress.progress(100)

            # geen extra 'gereed' banner en geen copy/download knop zoals gevraagd

        except Exception as e:
            progress.progress(0)
            status.error(f'Fout tijdens generatie: {e}')
            # toon raw response / error indien aanwezig in debug expander (blijft beschikbaar)

# Run app when file executed directly (useful for `streamlit run`)
if __name__ == "__main__":
    app()
