# tools/docex_tool/tool.py
import os
import io
import tempfile
import re
import json
import streamlit as st
from groq import Groq
import docx
from docx.enum.text import WD_BREAK

from . import steps  # lokaal moduletje dat we hierboven maakten

# ---------------- Groq client helper (tries env then secrets) ----------------
def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if api_key:
        try:
            return Groq(api_key=api_key)
        except Exception as e:
            st.sidebar.error(f"Fout bij verbinden met Groq API (env): {e}")
            st.stop()

    # check mogelijk aanwezige secrets.toml (vermijdt directe st.secrets access fout)
    possible = [
        os.path.expanduser("~/.streamlit/secrets.toml"),
        os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
    ]
    api_key = ""
    if any(os.path.exists(p) for p in possible):
        try:
            api_key = st.secrets.get("groq", {}).get("api_key", "").strip()
        except Exception:
            api_key = ""

    if not api_key:
        st.sidebar.error(
            "Groq API key niet gevonden. Zet GROQ_API_KEY env var of maak `.streamlit/secrets.toml` met [groq] api_key = \"...\""
        )
        st.stop()

    try:
        return Groq(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"Fout bij verbinden met Groq API: {e}")
        st.stop()

# --------------- parsing helper voor model-output -> JSON-array ---------------
def parse_groq_json_array(content: str):
    cleaned = re.sub(r"\d+\s*:\s*{", "{", content)
    start, end = cleaned.find("["), cleaned.rfind("]") + 1
    json_str = cleaned[start:end] if start != -1 and end != -1 else cleaned
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        repls = []
        lines = cleaned.splitlines()
        for i, ln in enumerate(lines):
            if '"find"' in ln:
                fm = re.search(r'"find"\s*:\s*"([^"]*)"', ln)
                rm = None
                if fm:
                    for nxt in lines[i + 1 :]:
                        m = re.search(r'"replace"\s*:\s*"([^"]*)"', nxt)
                        if m:
                            rm = m.group(1)
                            break
                if fm and rm:
                    repls.append({"find": fm.group(1), "replace": rm})
        return repls

# ---------------- vraag het model om replacements (returns list of dict) ----
def get_replacements_from_model(groq_client: Groq, template_text: str, context_text: str):
    prompt = (
        "Gegeven TEMPLATE en CONTEXT, lever JSON-array met objecten {find, replace}."
        f"\n\nTEMPLATE:\n{template_text}\n\nCONTEXT:\n{context_text}"
    )
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Antwoord alleen JSON-array, geen extra tekst."},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as e:
        st.error(f"Fout bij model-aanroep: {e}")
        return []

    content = resp.choices[0].message.content
    repls = parse_groq_json_array(content)
    return [r for r in repls if r.get("find") and r.get("find") != r.get("replace")]

# ---------------- apply replacements (werkt op file path) -------------------
def apply_replacements_to_doc_and_bytes(doc_path: str, replacements: list[dict], include_changes_overview: bool = True) -> bytes:
    """
    Eenvoudige run-level replacement: leest doc_path, vervangt placeholders en
    voegt optioneel een overzicht (incl. stappen) toe. Retourneert bytes.
    """
    doc = docx.Document(doc_path)

    def repl(runs):
        if not runs:
            return
        txt = "".join(r.text for r in runs)
        for rp in replacements:
            txt = txt.replace(rp["find"], rp["replace"])
        runs[0].text = txt
        for r in runs[1:]:
            r.text = ""

    # paragraphs
    for p in doc.paragraphs:
        repl(p.runs)

    # tables
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    repl(p.runs)

    # append a new page + steps overview
    if include_changes_overview:
        try:
            p_br = doc.add_paragraph()
            run = p_br.add_run()
            run.add_break(WD_BREAK.PAGE)
        except Exception:
            pass

        try:
            doc.add_paragraph("Aangepaste onderdelen", style="Heading 1")
        except Exception:
            doc.add_paragraph("Aangepaste onderdelen")

        for rp in replacements:
            para = doc.add_paragraph(f"• {rp['find']} → {rp['replace']}")
            try:
                para.style = "List Bullet"
            except Exception:
                pass

        # voeg ook onze stap-logger toe
        step_lines = steps.get_steps()
        if step_lines:
            try:
                doc.add_paragraph("Uitgevoerde stappen", style="Heading 2")
            except Exception:
                doc.add_paragraph("Uitgevoerde stappen")
            for s in step_lines:
                doc.add_paragraph(f"• {s}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --------------------------- Streamlit UI (alle in run()) --------------------
def run():
    # clear s
