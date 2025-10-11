# epic.py
import os, re, textwrap
from typing import Optional, Dict, Any

try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    Groq = None
    _HAS_GROQ = False

INSTRUCTIONS = (
    "Vul het onderstaande template EXACT in op basis van de korte omschrijving.\n"
    "- Geef alleen de ingevulde template terug, zonder extra toelichting.\n"
    "- Gebruik generieke IT-terminologie.\n"
    "- 'To do' 1–10 genummerde stappen.\n"
)

TEMPLATE = """Titel: {{title}}

Type: Epic

Doel:
{{goal}}

To do:
{{to_do}}

Scope:
{{scope}}

Dependencies:
{{dependencies}}

Background:
{{background}}
"""

# helpers (same as others)
def _get_groq_client() -> Optional[Groq]:
    if not _HAS_GROQ:
        return None
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    try:
        import streamlit as st
        api_key = api_key or st.secrets.get("groq", {}).get("api_key", "").strip()
    except Exception:
        pass
    return Groq(api_key=api_key) if api_key else None

def _resp_to_text(resp: Any) -> str:
    try:
        if hasattr(resp, "choices"):
            choices = getattr(resp, "choices")
            if choices:
                c = choices[0]
                msg = getattr(c, "message", None)
                if msg and getattr(msg, "content", None):
                    return getattr(msg, "content")
                return getattr(c, "text", None) or getattr(c, "content", None) or str(c)
        if isinstance(resp, dict):
            choices = resp.get("choices") or []
            if choices:
                c0 = choices[0]
                msg = c0.get("message") or {}
                if isinstance(msg, dict) and msg.get("content"):
                    return msg.get("content")
                return c0.get("text") or c0.get("content") or str(c0)
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
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r"\[\[[^\]]*\]\]", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\(\([^)]*\)\)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _has_minimum_structure(text: str) -> bool:
    low = text.lower()
    required = ["titel", "type", "doel", "to do", "scope", "dependencies", "background"]
    return all(k in low for k in required)

def _extract_todo_count(text: str) -> int:
    low = text.lower()
    idx = low.find("to do")
    if idx == -1:
        return 0
    rest = text[idx:]
    lines = rest.splitlines()
    count = 0
    for ln in lines[1:60]:
        ln_stripped = ln.strip()
        if re.match(r"^\d+\.", ln_stripped) or re.match(r"^[-*]\s+", ln_stripped):
            count += 1
        elif ln_stripped == "":
            continue
        else:
            break
    return count

def _truncate_todo_steps(text: str, max_steps: int = 10) -> str:
    import re as _re
    low = text.lower()
    m = _re.search(r"(to do)", low)
    if not m:
        return text
    start = m.start()
    header_match = _re.search(r"(?i)(to do)\s*[:\-]?\s*", text[m.start():])
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
        if _re.match(r"^\d+\.", ln_stripped) or _re.match(r"^[-*]\s+", ln_stripped):
            new_lines.append(ln)
            kept += 1
        elif ln_stripped == "":
            new_lines.append(ln)
        else:
            new_lines.append(ln)
    new_rest = "\n".join(new_lines)
    return text[:hdr_end] + new_rest

def _local_fill(template: str, short_input: str) -> str:
    def repl(m):
        key = m.group(1).lower()
        first = short_input.strip().splitlines()[0] if short_input else "Generieke taak"
        if key in ("title", "titel"):
            return first
        if key == "goal":
            return "Hoofddoel van de epic: enable brede capability X voor meerdere teams."
        if key in ("to_do", "todo", "steps"):
            return "1. Definieer backlog items en scope\n2. Prioritizeer & plan releases\n3. Maak architectonische designs\n4. Implementeer incrementally en test"
        if key == "scope":
            return "- Cross-team capability\n- Minimum viable scope voor eerste release"
        if key in ("dependencies", "blockers"):
            return "- Shared API contracts\n- Alignment met platform-team"
        if key == "background":
            return "Epics bundelen werk dat meerdere teams of sprints overspant. Focus op schaal en samenhang. Deze epic is generiek en gericht op het bieden van een herbruikbare capability."
        return first
    return re.sub(r"{{\s*([a-zA-Z0-9_]+)\s*}}", repl, template)

def generate(short_input: str) -> Dict[str, str]:
    result = ""
    raw = ""
    error = ""
    prompt = INSTRUCTIONS + "\n\nTEMPLATE:\n" + TEMPLATE + "\n\nOmschrijving:\n" + (short_input.strip() or "(geen omschrijving)")
    client = _get_groq_client()
    if client is not None:
        try:
            try:
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    temperature=0.15,
                    max_tokens=1400,
                    messages=[
                        {"role": "system", "content": "Je bent een beknopte assistant voor het genereren van generieke IT epics."},
                        {"role": "user", "content": prompt},
                    ],
                )
            except TypeError:
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    temperature=0.15,
                    messages=[
                        {"role": "system", "content": "Je bent een beknopte assistant voor het genereren van generieke IT epics."},
                        {"role": "user", "content": prompt},
                    ],
                )
            raw = _strip_code_fence(_resp_to_text(resp))
            sanitized = _sanitize_placeholders(raw)
            if len(sanitized) < 40 or not _has_minimum_structure(sanitized):
                return {"result": "", "raw": raw, "error": "LLM returned inadequate structure or too short response"}
            todo_count = _extract_todo_count(sanitized)
            if todo_count == 0:
                return {"result": "", "raw": raw, "error": "LLM output has no To do steps"}
            if todo_count > 10:
                sanitized = _truncate_todo_steps(sanitized, max_steps=10)
            return {"result": sanitized, "raw": raw, "error": ""}
        except Exception as e:
            raw = str(e)
            error = f"LLM call error: {e}"
    try:
        filled = _local_fill(TEMPLATE, short_input)
        result = _sanitize_placeholders(filled)
    except Exception as e:
        error = f"Local fallback error: {e}"
        result = ""
    return {"result": result, "raw": raw, "error": error}
