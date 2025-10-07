# story.py
import os
import re
import textwrap
from typing import Optional, Dict, Any

# optional Groq client
try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    Groq = None
    _HAS_GROQ = False

# ===== MODULE-LOCAL TEMPLATE & INSTRUCTIONS (edit here) =====
INSTRUCTIONS = (
    "Vul het onderstaande template EXACT in op basis van de korte omschrijving.\n"
    "- Geef alleen de ingevulde template terug, zonder extra toelichting of voorbeelden.\n"
    "- Gebruik generieke IT-terminologie; voeg geen domein-specifieke voorbeelden toe.\n"
    "- Zorg dat 'To do' 1 tot maximaal 10 concrete genummerde stappen bevat.\n"
    "- Laat geen placeholders of bracket-teksten in de output achter.\n"
    "- Houd de structuur van het template aan (sectiekoppen en volgorde).\n"
)

TEMPLATE = """Titel: {{title}}

Type: User Story

Als: {{als}}
Wil ik: {{wil_ik}}
Zodat: {{zodat}}

To do:
{{to_do}}

Scope:
{{scope}}

Dependencies:
{{dependencies}}

Background:
{{background}}
"""
# ===== end local prompt/template =====

# Helper utilities
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
                if msg:
                    content = getattr(msg, "content", None)
                    if content:
                        return content
                return getattr(c, "text", None) or getattr(c, "content", None) or str(c)
        if isinstance(resp, dict):
            choices = resp.get("choices") or []
            if choices:
                c0 = choices[0]
                if isinstance(c0, dict):
                    msg = c0.get("message", {})
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
    required = ["titel", "type", "als", "wil ik", "zodat", "to do", "scope", "dependencies", "background"]
    return all(k in low for k in required)

def _extract_todo_count(text: str) -> int:
    low = text.lower()
    idx = low.find("to do")
    if idx == -1:
        return 0
    rest = text[idx:]
    lines = rest.splitlines()
    count = 0
    for ln in lines[1:40]:
        ln_stripped = ln.strip()
        if re.match(r"^\d+\.", ln_stripped) or re.match(r"^[-*]\s+", ln_stripped):
            count += 1
        elif ln_stripped == "":
            continue
        else:
            break
    return count

def _truncate_todo_steps(text: str, max_steps: int = 10) -> str:
    low = text.lower()
    m = re.search(r"(to do)", low)
    if not m:
        return text
    start = m.start()
    header_match = re.search(r"(?i)(to do)\s*[:\-]?\s*", text[m.start():])
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
        if re.match(r"^\d+\.", ln_stripped) or re.match(r"^[-*]\s+", ln_stripped):
            new_lines.append(ln)
            kept += 1
        elif ln_stripped == "":
            new_lines.append(ln)
        else:
            new_lines.append(ln)
    new_rest = "\n".join(new_lines)
    return text[:hdr_end] + new_rest

# Local generic filler (fallback)
def _local_fill(template: str, short_input: str) -> str:
    def repl(m):
        key = m.group(1).lower()
        first = short_input.strip().splitlines()[0] if short_input else "Generieke taak"
        if key in ("title", "titel"):
            return first
        if key == "als":
            return "Als gebruiker"
        if key in ("wil_ik", "wil", "want"):
            return "Wil ik functionaliteit X in het systeem"
        if key in ("zodat", "so_that"):
            return "Zodat deze waarde of business outcome bereikt wordt"
        if key in ("to_do", "todo", "steps", "main_flow"):
            return "1. Definieer testcases en fixtures\n2. Implementeer mocks voor externe afhankelijkheden\n3. Schrijf unit tests met duidelijke assertions"
        if key == "scope":
            return "- Valideert data-preprocessing en prompt-contract\n- Test edge-cases en ontbrekende velden"
        if key in ("dependencies", "blockers"):
            return "- Mockable retrieval API\n- CI pipeline voor testuitvoering"
        if key == "background":
            return (
                "Deze taak zorgt ervoor dat regressies in data-preprocessing en prompt-contract vroegtijdig worden gedetecteerd. "
                "Unit tests zijn deterministisch en vermijden flakiness door gebruik van mocks. "
                "Focus ligt op generieke checks zodat deze test op elk IT-project toepasbaar is."
            )
        return first
    return re.sub(r"{{\s*([a-zA-Z0-9_]+)\s*}}", repl, template)

# Public generate function
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
                    max_tokens=1200,
                    messages=[
                        {"role": "system", "content": "Je bent een beknopte assistant voor het genereren van generieke IT user stories."},
                        {"role": "user", "content": prompt},
                    ],
                )
            except TypeError:
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    temperature=0.15,
                    messages=[
                        {"role": "system", "content": "Je bent een beknopte assistant voor het genereren van generieke IT user stories."},
                        {"role": "user", "content": prompt},
                    ],
                )
            raw = _strip_code_fence(_resp_to_text(resp))
            sanitized = _sanitize_placeholders(raw)

            if len(sanitized) < 40 or not _has_minimum_structure(sanitized):
                error = "LLM returned inadequate structure or too short response"
                return {"result": "", "raw": raw, "error": error}

            todo_count = _extract_todo_count(sanitized)
            if todo_count == 0:
                return {"result": "", "raw": raw, "error": "LLM output has no To do steps"}
            if todo_count > 10:
                sanitized = _truncate_todo_steps(sanitized, max_steps=10)

            return {"result": sanitized, "raw": raw, "error": ""}

        except Exception as e:
            raw = str(e)
            error = f"LLM call error: {e}"

    # fallback
    try:
        filled = _local_fill(TEMPLATE, short_input)
        result = _sanitize_placeholders(filled)
    except Exception as e:
        error = f"Local fallback error: {e}"
        result = ""

    return {"result": result, "raw": raw, "error": error}
