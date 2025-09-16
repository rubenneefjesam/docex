from __future__ import annotations
import json, re, os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st

# --- Heuristics / keywords ---
RISK_WORDS = {"risk","risico","concern","issue","threat","gevaar","knelpunt"}
ACTION_VERBS = {"implement","fix","resolve","aanpassen","configureren","reviewen",
                "plan","plannen","doen","uitvoeren","monitoren","beoordelen","opschonen"}

DEFAULT_PROMPT = """Maak een beknopte, gestructureerde samenvatting met dit schema:
- Title
- Executive summary (3–6 zinnen)
- Key points (max 8 bullets)
- Actions (max 8 bullets, actiewoorden vooraan)
- Risks (max 8 bullets)
- Entities (zoals jaartallen, bedragen, e-mails, urls)
- Word count
Schrijf helder en bondig in het Nederlands. Gebruik, waar zinvol, de oorspronkelijke bewoordingen.
"""


# ===============================
#   Kern datamodel & helpers
# ===============================
@dataclass
class StructuredSummary:
    file_name: str
    title: str
    executive_summary: str
    key_points: List[str]
    actions: List[str]
    risks: List[str]
    entities: Dict[str, List[str]]
    word_count: int

def guess_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if 6 <= len(s) <= 120:
            return s
    return Path(fallback).stem

def extract_key_points(text: str, max_points: int = 8) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    bullets = [ln for ln in lines if re.match(r"^[-*•\d\)]\s", ln) or (" - " in ln)]
    if not bullets:
        bullets = [ln for ln in lines if 50 <= len(ln) <= 200]
    return bullets[:max_points]

def extract_actions(text: str, max_items: int = 8) -> List[str]:
    items = []
    for ln in text.splitlines():
        s = re.sub(r"^[*\-\d\)\.]+\s*", "", ln.strip())
        if not s:
            continue
        token = s.split()[0].lower()
        if token in ACTION_VERBS or any(s.lower().startswith(v) for v in ACTION_VERBS):
            items.append(s)
    return items[:max_items]

def extract_risks(text: str, max_items: int = 8) -> List[str]:
    items = []
    for ln in text.splitlines():
        s = ln.strip().lower()
        if any(w in s for w in RISK_WORDS):
            items.append(ln.strip())
    return items[:max_items]

def extract_entities(text: str) -> Dict[str, List[str]]:
    dates = sorted(set(re.findall(r"\b(20\d{2}|19\d{2})\b", text)))
    euros = sorted(set(re.findall(r"\b€\s?\d[\d\.\,]*", text)))
    emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    urls = sorted(set(re.findall(r"https?://\S+", text)))
    return {"years": dates, "eur": euros, "emails": emails, "urls": urls}

def executive_summary(text: str, target_sentences: int = 5) -> str:
    sents = re.split(r"(?<=[\.\!\?])\s+", text.strip())
    sents = [s.strip() for s in sents if len(s.strip()) >= 30]
    return " ".join(sents[:target_sentences])

def summarize_text(file_name: str, text: str, prompt: str) -> StructuredSummary:
    """
    Samenvat met heuristieken. 'prompt' wordt nu nog niet semantisch gebruikt,
    maar staat klaar voor LLM-integratie zonder UI-wijzigingen.
    """
    title = guess_title(text, file_name)
    return StructuredSummary(
        file_name=file_name,
        title=title,
        executive_summary=executive_summary(text),
        key_points=extract_key_points(text),
        actions=extract_actions(text),
        risks=extract_risks(text),
        entities=extract_entities(text),
        word_count=len(text.split()),
    )

def _to_markdown(ss: StructuredSummary) -> str:
    md = [f"# {ss.title}", "", f"**Bestand:** `{ss.file_name}`", "", "## Executive summary", ss.executive_summary]
    md += ["", "## Key points"] + [f"- {p}" for p in ss.key_points] if ss.key_points else ["", "## Key points", "_n.v.t._"]
    md += ["", "## Actions"] + [f"- {a}" for a in ss.actions] if ss.actions else ["", "## Actions", "_n.v.t._"]
    md += ["", "## Risks"] + [f"- {r}" for r in ss.risks] if ss.risks else ["", "## Risks", "_n.v.t._"]
    md += ["", "## Entities"]
    any_entity = False
    for k, vals in ss.entities.items():
        if vals:
            any_entity = True
            md.append(f"- **{k}**: " + ", ".join(vals))
    if not any_entity:
        md.append("_n.v.t._")
    md += ["", f"_Word count: {ss.word_count}_"]
    return "\n".join(md)


# ===============================
#   Streamlit UI (entrypoint)
# ===============================
def app():
    st.header("📄 Document Summarizer (gestructureerd)")

    # 1) Upload
    uploads = st.file_uploader(
        "Kies één of meerdere bestanden (PDF / DOCX / TXT / MD)",
        type=["pdf","docx","txt","md"],
        accept_multiple_files=True
    )

    # 2) Prompt (aanpasbaar door user)
    st.markdown("#### Samenvattingsprompt")
    prompt = st.text_area(
        "Pas de prompt naar wens aan (standaard voldoet in de meeste gevallen).",
        value=DEFAULT_PROMPT,
        height=180,
        label_visibility="collapsed",
        key="docsum_prompt",
    )

    # 3) Actie-knop om te starten
    generate = st.button("🔎 Genereer samenvatting", use_container_width=True)

    # Container waar we resultaten tonen (blijft onder de knop)
    output = st.container()

    # Bewaar resultaten in session state zodat ze zichtbaar blijven
    if "docsum_results" not in st.session_state:
        st.session_state.docsum_results = []

    if generate:
        if not uploads:
            st.warning("Upload eerst ten minste één document.")
            return

        results: List[StructuredSummary] = []
        with st.spinner("Bezig met verwerken..."):
            for uf in uploads:
                name = uf.name
                data = uf.getvalue()  # bytes

                # eenvoudige, dependency-vrije tekst-extractie:
                suffix = Path(name).suffix.lower()
                if suffix in {".txt", ".md"}:
                    try:
                        text = data.decode("utf-8")
                    except Exception:
                        text = data.decode("latin-1", errors="ignore")
                elif suffix in {".pdf", ".docx"}:
                    # geen externe parsers: geef een duidelijke placeholder
                    text = (
                        f"[Bestand {name} is een {suffix} — tekst-extractie voor dit type is niet ingeschakeld. "
                        "Upload een .txt/.md bestand of activeer document parsing (pymupdf / python-docx) om volledige extractie te krijgen.]"
                    )
                else:
                    # fallback: permissieve decode
                    try:
                        text = data.decode("utf-8")
                    except Exception:
                        text = data.decode("latin-1", errors="ignore")

                try:
                    ss = summarize_text(name, text, prompt=prompt)
                    results.append(ss)
                except Exception as e:
                    st.error(f"Kon `{name}` niet verwerken: {e}")

        # Sla op in session state (laatste run)
        st.session_state.docsum_results = results

    # 4) Toon resultaten onder de knop
    with output:
        results = st.session_state.docsum_results
        if not results:
            st.info("Nog geen samenvatting gegenereerd. Pas eventueel de prompt aan en klik op ‘Genereer samenvatting’.")
            return

        for ss in results:
            with st.expander(f"📘 {ss.file_name}", expanded=True):
                st.subheader(ss.title)
                c1, c2, c3 = st.columns(3)
                c1.metric("Words", ss.word_count)
                c2.metric("Key points", len(ss.key_points))
                c3.metric("Actions", len(ss.actions))

                st.markdown("### Executive summary")
                st.write(ss.executive_summary or "_n.v.t._")

                st.markdown("### Key points")
                st.markdown("\n".join(f"- {p}" for p in ss.key_points) if ss.key_points else "_n.v.t._")

                st.markdown("### Actions")
                st.markdown("\n".join(f"- {a}" for a in ss.actions) if ss.actions else "_n.v.t._")

                st.markdown("### Risks")
                st.markdown("\n".join(f"- {r}" for r in ss.risks) if ss.risks else "_n.v.t._")

                st.markdown("### Entities")
                any_entity = any(v for v in ss.entities.values())
                if any_entity:
                    for k, vals in ss.entities.items():
                        if vals:
                            st.write(f"- **{k}**: {', '.join(vals)}")
                else:
                    st.write("_n.v.t._")

                # Downloads
                md = _to_markdown(ss).encode("utf-8")
                js = json.dumps(asdict(ss), ensure_ascii=False, indent=2).encode("utf-8")

                st.download_button("Download .md", md, file_name=f"{Path(ss.file_name).stem}.md", mime="text/markdown")
                st.download_button("Download .json", js, file_name=f"{Path(ss.file_name).stem}.json", mime="application/json")