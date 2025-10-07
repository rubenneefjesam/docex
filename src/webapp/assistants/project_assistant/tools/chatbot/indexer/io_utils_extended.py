# io_utils_extended.py
"""
Eenvoudige IO helpers used by the indexer.
- find_files_in_dir(data_dir, exts=None, recursive=True)
- read_and_meta(path) -> (text:str, meta:dict)

Deze versie is vereenvoudigd: we gebruiken alleen de ingebouwde tekstreaders
(plain text files) en PyPDF2 voor PDF-extractie. Geen pdftotext/pdfminer fallback.
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict, Any
import os
import logging
import unicodedata

# lokale id-helpers (in jouw repo)
try:
    from .id_utils import parse_ids_from_filename_or_path, find_pid_from_ancestors, find_pid_in_text
except Exception:
    # fallback no-op implementations if id_utils on path issues occur
    def parse_ids_from_filename_or_path(p):
        return (None, None)
    def find_pid_from_ancestors(p):
        return None
    def find_pid_in_text(t):
        return None

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)


def find_files_in_dir(data_dir: str | Path,
                      exts: Optional[Iterable[str]] = None,
                      recursive: bool = True,
                      include_hidden: bool = False) -> List[Path]:
    p = Path(data_dir)
    if not p.exists():
        return []
    if exts:
        norm_exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}
    else:
        norm_exts = None

    results: List[Path] = []
    if recursive:
        for f in p.rglob("*"):
            if not f.is_file():
                continue
            if not include_hidden and any(part.startswith(".") for part in f.parts):
                continue
            if norm_exts is None or f.suffix.lower() in norm_exts:
                results.append(f)
    else:
        for f in p.iterdir():
            if not f.is_file():
                continue
            if not include_hidden and f.name.startswith("."):
                continue
            if norm_exts is None or f.suffix.lower() in norm_exts:
                results.append(f)
    results.sort()
    return results


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return ""


def _normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    parts = s.split()
    return " ".join(parts).strip()


def _extract_with_pypdf2(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except Exception as e:
        logger.debug("PyPDF2 not available: %s", e)
        return ""
    try:
        r = PdfReader(str(path))
        out_parts: List[str] = []
        for i, page in enumerate(r.pages):
            try:
                t = page.extract_text() or ""
                out_parts.append(t)
            except Exception as e:
                logger.debug("PyPDF2 page %d error: %s", i, e)
        return "\n".join(out_parts)
    except Exception as e:
        logger.debug("PyPDF2 top-level error for %s: %s", path, e)
        return ""


def extract_text_multi(path: str | Path,
                       min_chars: int = 20) -> Tuple[str, Dict[str, Any]]:
    """
    Simplified extractor: try textfile first, then PyPDF2 for PDFs.
    Returns (normalized_text, meta) where meta contains extractor_used,
    extractor_counts and a short sample.
    """
    p = Path(path)
    extractor_counts: Dict[str, int] = {}
    raw_texts: Dict[str, str] = {}

    # Plain text files
    if p.suffix.lower() in {".txt", ".md", ".csv"}:
        raw = _read_text_file(p)
        extractor_counts["textfile"] = len(raw or "")
        raw_texts["textfile"] = raw or ""
        norm = _normalize_text(raw or "")
        meta = {
            "extractor_used": "textfile" if len(norm) >= min_chars else None,
            "extractor_counts": extractor_counts,
            "sample": (raw or "")[:200],
        }
        return (norm, meta)

    # PDFs: only PyPDF2
    raw = _extract_with_pypdf2(p)
    extractor_counts["pypdf2"] = len(raw or "")
    raw_texts["pypdf2"] = raw or ""
    if raw and len(_normalize_text(raw)) >= min_chars:
        norm = _normalize_text(raw)
        meta = {"extractor_used": "pypdf2", "extractor_counts": extractor_counts, "sample": raw[:200]}
        return (norm, meta)

    # nothing found
    meta = {"extractor_used": None, "extractor_counts": extractor_counts, "sample": ""}
    return ("", meta)


def read_and_meta(path: str | Path) -> Tuple[str, Dict[str, Any]]:
    p = Path(path)
    meta: Dict[str, Any] = {
        "filename": p.name,
        "path": str(p),
        "suffix": p.suffix.lower(),
        "size": None,
        "cid": None,
        "pid": None,
        "pid_from_ancestors": None,
    }
    try:
        meta["size"] = p.stat().st_size
    except Exception:
        meta["size"] = None

    text = ""
    try:
        if p.suffix.lower() in {".txt", ".md", ".csv"}:
            text = _read_text_file(p)
            meta.update({
                "extractor_used": "textfile",
                "extractor_counts": {"textfile": len(text or "")},
                "sample": (text or "")[:200],
            })
        elif p.suffix.lower() == ".pdf":
            txt, emeta = extract_text_multi(p)
            text = txt or ""
            meta.update(emeta)
        else:
            text = ""
    except Exception as e:
        logger.debug("read_and_meta error for %s: %s", p, e)
        text = ""

    # attempt to parse ids (best-effort)
    try:
        cid, pid = parse_ids_from_filename_or_path(p)
        meta["cid"] = cid
        meta["pid"] = pid
        if not pid:
            meta["pid_from_ancestors"] = find_pid_from_ancestors(p)
        if not meta.get("pid") and text:
            meta["pid_in_text"] = find_pid_in_text(text)
    except Exception:
        pass

    return text, meta
