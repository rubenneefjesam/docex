from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict
import streamlit as st

from .readers import read_any

RISK_WORDS = {"risk","risico","concern","issue","threat","gevaar","knelpunt"}
ACTION_VERBS = {"implement","fix","resolve","aanpassen","configureren","reviewen",
                "plan","plannen","doen","uitvoeren","monitoren","beoordelen","opschonen"}

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
        if not s: continue
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

def summarize_text(file_name: str, text: str) -> StructuredSummary:
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

def app():
    st.header("📄 Structured Document Summary")
    st.write("Upload **PDF / DOCX / TXT**. We geven per document een gestandaardiseerde samenvatting.")

    uploads = st.file_uploader("Kies bestanden", type=["pdf","docx","txt","md"], accept_multiple_files=True)
    if not uploads:
        st.info("Nog geen bestanden geüpload.")
        return

    results: List[StructuredSummary] = []
    with st.spinner("Analyseren..."):
        for uf in uploads:
            name = uf.name
            tmp = Path(st.secrets.get("_tmp_dir", ".")) / f"__tmp_{name}"
            tmp.write_bytes(uf.getvalue())
            try:
                _, text = read_any(tmp)
                ss = summarize_text(name, text)
                results.append(ss)
            except Exception as e:
                st.error(f"Kon `{name}` niet verwerken: {e}")
            finally:
                try: tmp.unlink(missing_ok=True)
                except Exception: pass

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

            md = _to_markdown(ss).encode("utf-8")
            js = json.dumps(asdict(ss), ensure_ascii=False, indent=2).encode("utf-8")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button("⬇️ Download Markdown", data=md,
                                   file_name=f"{Path(ss.file_name).stem}_summary.md", mime="text/markdown", use_container_width=True)
            with d2:
                st.download_button("⬇️ Download JSON", data=js,
                                   file_name=f"{Path(ss.file_name).stem}_summary.json", mime="application/json", use_container_width=True)

def app():
    import streamlit as st
    st.header("📄 Document Summarizer")
    st.write("Upload documenten om een samenvatting te genereren.")
    # hier komt jouw UI/logic; tijdelijk placeholder:
    uploaded = st.file_uploader("Upload een bestand", type=["pdf", "docx", "txt"])
    if uploaded:
        st.success(f"Ontvangen: {uploaded.name}")