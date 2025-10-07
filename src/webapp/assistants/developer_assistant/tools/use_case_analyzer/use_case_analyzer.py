# use_case_analyzer.py
# Helpers voor inladen, genereren en exporteren van use-case templates.

import os
import re
import json
import textwrap
import io
from typing import Dict, Tuple, Optional

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

def load_templates(templates_dir: str) -> Dict[str, str]:
    """
    Lees alle niet-verborgen bestanden in de map en retourneer een dict naam -> inhoud.
    Naam is bestandsnaam zonder extensie.
    """
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
    """Geef unieke placeholder-namen in volgorde van voorkomen."""
    found = _PLACEHOLDER_RE.findall(template_str)
    seen = set()
    ordered = []
    for ph in found:
        if ph not in seen:
            seen.add(ph)
            ordered.append(ph)
    return tuple(ordered)

def render_template(template_str: str, context: Dict[str, str]) -> str:
    """
    Vervang elke {{key}} in de template door context[key] of lege string.
    """
    def _repl(match: re.Match) -> str:
        return context.get(match.group(1), '')
    return _PLACEHOLDER_RE.sub(_repl, template_str)

def _get_groq_client() -> Optional[Groq]:
    """Initialiseer Groq-client indien API key beschikbaar."""
    if not _HAS_GROQ:
        return None
    api_key = os.environ.get('GROQ_API_KEY', '').strip()
    try:
        import streamlit as st
        api_key = api_key or st.secrets.get('groq', {}).get('api_key', '').strip()
    except ImportError:
        pass
    if not api_key:
        return None
    return Groq(api_key=api_key)

def call_groq(prompt: str,
              model: str = 'llama-3.1-8b-instant',
              temperature: float = 0.2) -> str:
    """Roep Groq aan en geef de ruwe tekst terug."""
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

def local_generate_mapping(short_input: str,
                           placeholders: Tuple[str, ...]) -> Dict[str, str]:
    """Fallback mapping voor placeholders als Groq niet beschikbaar."""
    first = short_input.strip().splitlines()[0] if short_input else 'Onbekende story'
    mapping: Dict[str, str] = {}
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

def _build_groq_prompt(short_input: str,
                       placeholders: Tuple[str, ...],
                       template_name: str) -> str:
    """Maak prompt voor Groq JSON-output met gegeven placeholders."""
    keys = ', '.join(placeholders)
    return textwrap.dedent(f"""
        Geef **alleen** geldig JSON terug met velden: {keys}
        Template: {template_name}
        Omschrijving: {short_input}
    """)

def generate_for_template(short_input: str,
                          template_name: str,
                          templates_dir: str,
                          use_groq: bool = True) -> Dict[str, str]:
    """Genereer waarden voor alle placeholders via Groq of fallback."""
    templates = load_templates(templates_dir)
    tpl = templates.get(template_name)
    if tpl is None:
        raise FileNotFoundError(f"Template '{template_name}' niet gevonden.")
    placeholders = extract_placeholders(tpl)
    if not placeholders:
        return {}
    data: Dict[str, str] = {}
    # Probeer Groq
    if use_groq:
        try:
            prompt = _build_groq_prompt(short_input, placeholders, template_name)
            raw = call_groq(prompt)
            json_blob = raw[raw.find('{'): raw.rfind('}')+1]
            parsed = json.loads(json_blob)
            data = {k: str(parsed.get(k, '')) for k in placeholders}
        except Exception:
            data = {}
    # Vul fallback voor ontbrekende
    missing = [ph for ph in placeholders if not data.get(ph)]
    if missing:
        fallback = local_generate_mapping(short_input, tuple(missing))
        data.update(fallback)
    return data

def render_and_export(short_input: str,
                      template_name: str,
                      templates_dir: str,
                      use_groq: bool = True) -> Tuple[str, bytes]:
    """
    Genereer placeholders, render template en maak docx (of bytes text).
    Retourneer (gerenderde tekst, binaire data).
    """
    templates = load_templates(templates_dir)
    tpl = templates.get(template_name)
    if tpl is None:
        raise FileNotFoundError(f"Template '{template_name}' niet gevonden.")
    mapping = generate_for_template(short_input, template_name, templates_dir, use_groq)
    content = render_template(tpl, mapping)
    # Document export
    if _HAS_DOCX:
        doc = Document()
        doc.add_heading(mapping.get('title', template_name), level=1)
        for block in content.split('\n\n'):
            if ':' in block.splitlines()[0]:
                h, *rest = block.splitlines()
                doc.add_heading(h.rstrip(':'), level=2)
                for line in rest:
                    if line.strip():
                        doc.add_paragraph(line)
            else:
                for line in block.splitlines():
                    if line.strip():
                        doc.add_paragraph(line)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        data = buf.read()
    else:
        data = content.encode('utf-8')
    return content, data
