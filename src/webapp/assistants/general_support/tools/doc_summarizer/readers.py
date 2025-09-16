# src/webapp/assistants/general_support/tools/doc_summarize/doc_summarizer.py
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st

from .readers import read_any


RISK_WORDS = {"risk", "risico", "concern", "issue", "threat", "gevaar", "knelpunt"}
ACTION_VERBS = {"implement", "fix", "resolve", "aanpassen", "configureren", "reviewen",
                "plan", "plannen", "doen", "uitvoeren", "monitoren", "beoordelen", "opschonen"}


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
    # neem 1e niet-lege regel, liefst met titelachtige lengte
    for line in text.splitlines():
        s = line.strip()
        if len(s) >= 6 and len(s) <= 120:
            return s
    return Path(fallback).stem


def extract_key_points(text: str, max_points: int = 8) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # simpele bullet-achtige detectie
    bullets = [ln for ln in lines if re.match(r"^[-*•\d\)]\s", ln) or (" - " in ln)]
    # fallback: neem de meest informatieve zinnen (lengte filter)
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
        s = ln.strip()
        wl = s.lower()
        if any(w in wl for w in RISK_WORDS):
            items.append(s)
    return items[:max_items]


def extract_entities(text: str) -> Dict[str, List[str]]:
    # superlichte heuristiek; later vervangen door NER/LLM
    dates = sorted(set(re.findall(r"\b(20\d{2}|19\d{2})\b", text)))  # jaartallen
    euros = sorted(set(re.findall(r"\b€\s?\d[\d\.\,]*", text)))
    emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    urls = sorted(set(re.findall(r"https?://\S+", text)))
    return {"years": dates, "eur": euros, "emails": emails, "urls": urls}


def executive_summary(text: str, target_sentences: int = 5) -> str:
    # super simpel: pak de eerste N zinnen die lang genoeg zijn
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
    for k, vals in ss.entities.items():
        if vals:
            md.append(f"- **{k}**: " + ", ".join(vals))
    if md[-1] == "## Entities":  # geen entities
        md += ["_n.v.t._"]
    md += ["", f"_Word count: {ss.word_count}_"]
    return "\n".join(md)


def _download_bytes(filename: str, data: bytes, mime: str, label: str):
    st.download_button(label, data=data, file_name=filename, mime=mime, use_container_width=True)


def app():
    st.header("📄 Structured Document Summary")

    st.write(
        "Upload één of meerdere documenten (**PDF / DOCX / TXT**). "
        "We genereren per document een **gestandaardiseerde samenvatting** met executive summary, key points, acties, risico’s en entiteiten."
    )

    uploads = st.file_uploader(
        "Kies bestanden",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
    )

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
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass

    # Output tonen en downloads
    for ss in results:
        with st.expander(f"📘 {ss.file_name}", expanded=True):
            st.subheader(ss.title)
            cols = st.columns(3)
            cols[0].metric("Words", ss.word_count)
            cols[1].metric("Key points", len(ss.key_points))
            cols[2].metric("Actions", len(ss.actions))

            st.markdown("### Executive summary")
            st.write(ss.executive_summary or "_n.v.t._")

            st.markdown("### Key points")
            if ss.key_points:
                st.markdown("\n".join(f"- {p}" for p in ss.key_points))
            else:
                st.write("_n.v.t._")

            st.markdown("### Actions")
            if ss.actions:
                st.markdown("\n".join(f"- {a}" for a in ss.actions))
            else:
                st.write("_n.v.t._")

            st.markdown("### Risks")
            if ss.risks:
                st.markdown("\n".join(f"- {r}" for r in ss.risks))
            else:
                st.write("_n.v.t._")

            st.markdown("### Entities")
            if any(v for v in ss.entities.values()):
                for k, vals in ss.entities.items():
                    if vals:
                        st.write(f"- **{k}**: {', '.join(vals)}")
            else:
                st.write("_n.v.t._")

            # Downloads
            md = _to_markdown(ss).encode("utf-8")
            js = json.dumps(asdict(ss), ensure_ascii=False, indent=2).encode("utf-8")

            c1, c2 = st.columns(2)
            with c1:
                _download_bytes(f"{Path(ss.file_name).stem}_summary.md", md, "text/markdown", "⬇️ Download Markdown")
            with c2:
                _download_bytes(f"{Path(ss.file_name).stem}_summary.json", js, "application/json", "⬇️ Download JSON")

    # Batch download (alle resultaten samen)
    if results:
        bundle = {
            "items": [asdict(ss) for ss in results],
            "count": len(results),
        }
        js_all = json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ Download alle samenvattingen (JSON)",
                           data=js_all, file_name="summaries.json", mime="application/json", use_container_width=True)
