# use_case_analyzer.py
# Streamlit-app voor inladen, genereren en exporteren van use-case templates.

import os
import re
import json
import textwrap
import io
from typing import Dict, Tuple, Optional
import streamlit as st

# Optionele imports
try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    Groq = None
    _HAS_GROQ = False

try:
    from docx import Document
    _HAS_DOCX = True
except ImportError:
    Document = None
    _HAS_DOCX = False

# Regex voor placeholders {{ key }}
_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

# ---------------------------
# Core functies
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
    return Groq(api_key=api_key) if api_key else None


def call_groq(prompt: str, model: str = 'llama-3.1-8b-instant', temperature: float = 0.2) -> str:
    client = _get_groq_client()
    if not client:
        raise RuntimeError('Groq client niet beschikbaar.')
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {'role': 'system', 'content': 'Je bent een ervaren IT Business Analyst.'},
            {'role': 'user', 'content': prompt}
        ]
    )
    return getattr(resp.choices[0].message, 'content', str(resp))


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
            """ )
            raw = call_groq(prompt)
            blob = raw[raw.find('{'): raw.rfind('}')+1]
            parsed = json.loads(blob)
            data = {k: str(parsed.get(k, '')) for k in placeholders}
        except Exception:
            data = {}
    missing = [ph for ph in placeholders if not data.get(ph)]
    if missing:
        data.update(local_generate_mapping(short_input, tuple(missing)))
    return data


def render_and_export(short_input: str, template_name: str, templates_dir: str, use_groq: bool = True) -> Tuple[str, bytes]:
    data_map = generate_for_template(short_input, template_name, templates_dir, use_groq)
    tpl = load_templates(templates_dir)[template_name]
    content = render_template(tpl, data_map)
    if _HAS_DOCX:
        doc = Document()
        doc.add_heading(data_map.get('title', template_name), level=1)
        for block in content.split('\n\n'):
            lines = block.splitlines()
            if ':' in lines[0]:
                doc.add_heading(lines[0].rstrip(':'), level=2)
                lines = lines[1:]
            for ln in lines:
                if ln.strip():
                    doc.add_paragraph(ln)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        data = buf.read()
    else:
        data = content.encode('utf-8')
    return content, data

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
        '4. Bekijk en download het resultaat'
    )

    # Input controls in hoofdvenster
    here = os.path.dirname(__file__)
    templates_dir = os.path.join(here, 'templates')
    templates = load_templates(templates_dir)
    if not templates:
        st.error("Geen templates in 'templates/'.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        choice = st.selectbox('Kies template', list(templates.keys()))
        desc = st.text_area('Korte omschrijving', height=150)
        groq_opt = st.checkbox('Gebruik Groq LLM-generatie', value=False)
        gen = st.button('Genereer use-case')

    if gen:
        try:
            content, filedata = render_and_export(desc, choice, templates_dir, groq_opt)
            st.subheader('Resultaat')
            st.code(content, language='markdown')
            ext = 'docx' if _HAS_DOCX else 'txt'
            mime = (
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                if ext == 'docx' else 'text/plain'
            )
            st.download_button(
                f'Download .{ext}', filedata,
                file_name=f'{choice}.{ext}', mime=mime
            )
        except Exception as e:
            st.error(f'Fout: {e}')