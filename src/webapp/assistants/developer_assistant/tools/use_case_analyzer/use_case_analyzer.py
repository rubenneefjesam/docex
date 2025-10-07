# use_case_analyzer.py
# Streamlit-app: automatisch genereren van generieke IT-stories, features en epics
# Belangrijkste punten:
# - Twee-koloms UI: links input (template + korte omschrijving + knop), rechts de uiteindelijke output (geen download/copy)
# - Houd de generator generiek: de LLM krijgt het template en een korte instructie om het template EXACT in te vullen zonder domein-specifieke voorbeelden
# - Geen acceptance criteria sectie automatisch toevoegen (volgens gebruiker)
# - 'To do' bevat 1-10 genummerde stappen (zoals gevraagd)
# - Robuuste fallback: als LLM niet beschikbaar of niet bruikbaar, render lokaal op basis van placeholders
# - Progress indicator en debug-expander (raw response alleen in debug)

import os
import re
import json
import textwrap
from typing import Dict, Tuple, Optional, Any
import streamlit as st

# Optionele Groq import
try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    Groq = None
    _HAS_GROQ = False

# Placeholder regex
_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

# Minimum output section headers (case-insensitive)
_REQUIRED_SECTIONS = [
    'titel',
    'type',
    'als',
    'wil ik',
    'zodat',
    'to do',
    'scope',
    'dependencies',
    'background',
]

# ---------------------------
# Utility & core functions
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


def _strip_code_fence(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    if s.startswith("```") and s.endswith("```"):
        parts = s.splitlines()
        if len(parts) >= 3:
            return "\n".join(parts[1:-1]).strip()
    return s


def _sanitize_placeholders(text: str) -> str:
    # verwijder bracket placeholders en condenseer lege regels
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r"\[\[[^\]]*\]\]", '', text)
    text = re.sub(r"\[[^\]]*\]", '', text)
    text = re.sub(r"\(\([^)]*\)\)", '', text)
    # collapse multiple blank lines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _has_required_sections(text: str) -> bool:
    low = text.lower()
    for sec in _REQUIRED_SECTIONS:
        if sec not in low:
            return False
    return True


def _extract_section_length(text: str, heading: str) -> int:
    # simple heuristic: find heading and count lines until next heading or end
    pattern = re.compile(re.escape(heading), re.IGNORECASE)
    m = pattern.search(text)
    if not m:
        return 0
    start = m.end()
    rest = text[start:]
    # stop at next blank line followed by capitalized word or next known heading
    # naive: count non-empty lines in the next 6 lines
    lines = [ln for ln in rest.splitlines() if ln.strip()]
    return len(lines)

# ---------------------------
# LLM interaction (generic prompt)
# ---------------------------

_FILL_TEMPLATE_PROMPT_TEMPLATE = (
    "Vul het onderstaande template EXACT in op basis van de korte omschrijving.\n"
    "- Geef **alleen** de ingevulde template terug, zonder extra toelichting of voorbeelden.\n"
    "- Gebruik generieke IT-terminologie; Voeg geen domein-specifieke voorbeelden toe.\n"
    "- Zorg dat 'To do' 1 tot max 10 concrete genummerde stappen bevat.\n"
    "- Laat geen placeholders of bracket-teksten in de output achter.\n\n"
    "Template naam: {template_name}\n\n"
    "TEMPLATE:\n{template_str}\n\n"
    "Omschrijving:\n{short_input}\n"
)


def call_groq(prompt: str, model: str = 'llama-3.1-8b-instant', temperature: float = 0.15, max_tokens: int = 1200) -> str:
    client = _get_groq_client()
    if not client:
        raise RuntimeError('Groq client niet beschikbaar')
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {'role': 'system', 'content': 'Je bent een beknopte en zakelijke assistant voor het genereren van generieke IT user stories/features/epics.'},
                {'role': 'user', 'content': prompt}
            ]
        )
    except TypeError:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {'role': 'system', 'content': 'Je bent een beknopte en zakelijke assistant voor het genereren van generieke IT user stories/features/epics.'},
                {'role': 'user', 'content': prompt}
            ]
        )
    except Exception as e:
        raise RuntimeError(f'LLM call failed: {e}')
    return _strip_code_fence(_resp_to_text(resp))


def try_fill_template_with_llm(short_input: str, template_str: str, template_name: str) -> Optional[str]:
    prompt = _FILL_TEMPLATE_PROMPT_TEMPLATE.format(
        template_name=template_name,
        template_str=template_str,
        short_input=short_input
    )
    try:
        raw = call_groq(prompt)
        raw = _sanitize_placeholders(raw)
        if not raw or len(raw) < 30:
            st.session_state['last_raw'] = raw
            st.session_state['last_error'] = 'LLM returned empty or too short output'
            return None
        if not _has_required_sections(raw):
            st.session_state['last_raw'] = raw
            st.session_state['last_error'] = 'LLM output missing required sections'
            return None
        # ensure 'To do' has 1-10 steps: naive count of numbered lines under 'to do'
        todo_count = _extract_todo_count(raw)
        if todo_count == 0:
            st.session_state['last_raw'] = raw
            st.session_state['last_error'] = 'LLM output has no To do steps'
            return None
        if todo_count > 10:
            # if too many, truncate after 10 steps in post-processing
            raw = _truncate_todo_steps(raw, max_steps=10)
        return raw
    except Exception as e:
        st.session_state['last_raw'] = st.session_state.get('last_raw', '')
        st.session_state['last_error'] = str(e)
        return None


def _extract_todo_count(text: str) -> int:
    low = text.lower()
    idx = low.find('to do')
    if idx == -1:
        return 0
    rest = text[idx:]
    # look for lines starting with digit + '.' or '- '
    lines = rest.splitlines()
    count = 0
    for ln in lines[1:40]:
        ln_stripped = ln.strip()
        if re.match(r'^\d+\.', ln_stripped) or re.match(r'^[-*]\s+', ln_stripped):
            count += 1
        elif ln_stripped == '':
            continue
        else:
            # stop at next section header approx
            if re.match(r'^[A-Z][a-z]+:', ln_stripped) or re.match(r'^[A-Za-z ]+$', ln_stripped) and ln_stripped.isupper():
                break
    return count


def _truncate_todo_steps(text: str, max_steps: int = 10) -> str:
    # naive: find 'To do' and keep only first max_steps numbered bullets
    low = text.lower()
    m = re.search(r'(to do)', low)
    if not m:
        return text
    start = m.start()
    header_match = re.search(r'(?i)(to do)\s*[:\-]?\s*', text[m.start():])
    if not header_match:
        return text
    hdr_end = m.start() + header_match.end()
    rest = text[hdr_end:]
    lines = rest.splitlines()
    new_lines = []
    kept = 0
    for ln in lines:
        if kept >= max_steps:
            break
        ln_stripped = ln.strip()
        if re.match(r'^\d+\.', ln_stripped) or re.match(r'^[-*]\s+', ln_stripped):
            new_lines.append(ln)
            kept += 1
        elif ln_stripped == '':
            new_lines.append(ln)
        else:
            new_lines.append(ln)
    new_rest = '\n'.join(new_lines)
    return text[:hdr_end] + new_rest

# ---------------------------
# Local fallback renderer
# ---------------------------

def local_generate_generic(template_str: str, short_input: str) -> str:
    # render by extracting placeholders and filling them with generic IT content
    placeholders = extract_placeholders(template_str)
    mapping = {}
    first_line = short_input.strip().splitlines()[0] if short_input else 'Generieke taak'
    for ph in placeholders:
        key = ph.lower()
        if key == 'title' or key == 'titel':
            mapping[ph] = f"{first_line}"
        elif key == 'type':
            mapping[ph] = 'User Story'
        elif key in ('als', 'role'):
            mapping[ph] = 'Als gebruiker'
        elif key in ('wil_ik', 'wil', 'want'):
            mapping[ph] = 'Wil ik functionaliteit X in het systeem'
        elif key in ('zodat', 'so_that'):
            mapping[ph] = 'Zodat deze waarde of business outcome bereikt wordt'
        elif key in ('to_do', 'todo', 'steps', 'main_flow'):
            mapping[ph] = textwrap.dedent(
                '1. Definieer testcases en fixtures\n'
                '2. Implementeer mocks voor externe afhankelijkheden\n'
                '3. Schrijf unit tests met duidelijke assertions\n'
            )
        elif key == 'scope':
            mapping[ph] = '- Valideert data-preprocessing en prompt-contract\n- Test edge-cases en ontbrekende velden'
        elif key == 'dependencies' or key == 'blockers':
            mapping[ph] = '- Mockable retrieval API\n- CI pipeline voor testuitvoering'
        elif key == 'background':
            mapping[ph] = 'Deze taak zorgt ervoor dat regressies in data-preprocessing en prompt-contract vroegtijdig worden gedetecteerd. Unit tests zijn deterministisch en vermijden flakiness door gebruik van mocks. De focus ligt op generieke checks zodat deze test op elk IT-project toepasbaar is. Dit helpt het team om snel regressies op te sporen en vertrouwen te hebben in wijzigingen.'
        else:
            mapping[ph] = first_line
    return render_template(template_str, mapping)

# ---------------------------
# Streamlit UI
# ---------------------------

def app():
    st.set_page_config(page_title='Use-case Generator', layout='wide')
    st.title('Use-case Generator — generieke IT stories / features / epics')
    st.markdown('Vul links een template en korte omschrijving in. Rechts verschijnt de uiteindelijke, gestructureerde output.')

    here = os.path.dirname(__file__)
    templates_dir = os.path.join(here, 'templates')
    templates = load_templates(templates_dir)
    if not templates:
        st.error("Geen templates gevonden in 'templates' map.")
        return

    left, right = st.columns([1, 1.1])

    with left:
        choice = st.selectbox('Kies template', list(templates.keys()))
        desc = st.text_area('Korte omschrijving', height=180, placeholder='Korte, generieke omschrijving van wat je wilt')
        gen = st.button('Genereer')

    with right:
        output_place = st.empty()
        debug = st.expander('Debug (raw response)', expanded=False)
        with debug:
            st.write('Raw output en eventuele errors worden hier getoond als debugging nodig is.')
            if 'last_raw' in st.session_state:
                st.code(st.session_state.get('last_raw', ''), language='text')
            if 'last_error' in st.session_state:
                st.error(st.session_state.get('last_error'))

    if gen:
        # reset debug
        st.session_state.pop('last_raw', None)
        st.session_state.pop('last_error', None)

        progress = st.progress(0)
        status = st.empty()
        try:
            status.info('Preparing generation...')
            progress.progress(10)

            template_str = templates[choice]

            # Try LLM first if available
            progress.progress(30)
            status.info('Generating — LLM attempt (if available)')
            use_llm = _get_groq_client() is not None
            generated = None
            if use_llm:
                generated = try_fill_template_with_llm(desc, template_str, choice)

            # If LLM didn't return a valid filled template, fallback local render
            if not generated:
                status.info('LLM fallback: local renderer')
                generated = local_generate_generic(template_str, desc)

            progress.progress(80)
            # Final sanitize
            generated = _sanitize_placeholders(generated)
            output_place.code(generated, language='markdown')
            progress.progress(100)
            status.empty()

        except Exception as e:
            progress.progress(0)
            status.error(f'Error during generation: {e}')
            st.session_state['last_error'] = str(e)


if __name__ == '__main__':
    app()