# io_utils_extended.py
"""
Eenvoudige IO helpers used by the indexer.
- find_files_in_dir(data_dir, exts=None, recursive=True)
- read_and_meta(path) -> (text:str, meta:dict)

Deze implementatie gebruikt alleen stdlib, ondersteunt .txt/.md/.csv
en levert bruikbare metadata voor downstream logic (filename, size, cid/pid hints).
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict, Any
import fnmatch
import os

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


def find_files_in_dir(data_dir: str | Path,
                      exts: Optional[Iterable[str]] = None,
                      recursive: bool = True,
                      include_hidden: bool = False) -> List[Path]:
    """
    Return list of Path objects under data_dir matching extensions.
    exts: iterable like ['.txt', '.pdf'] or None => all files.
    recursive: use rglob if True, else glob in root only.
    """
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
    # stable order
    results.sort()
    return results


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # fallback: try latin-1
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return ""


def read_and_meta(path: str | Path) -> Tuple[str, Dict[str, Any]]:
    """
    Read a file and return (text, meta).
    - For .txt/.md/.csv returns text.
    - For other unknown types returns empty text but still returns meta.
    Meta contains:
      - filename, suffix, size, cid, pid, pid_from_ancestors
    """
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
        else:
            # Unknown binary types: try fallback to extract small text snippet (filename only)
            text = ""
    except Exception:
        text = ""

    # attempt to parse ids (best-effort)
    try:
        cid, pid = parse_ids_from_filename_or_path(p)
        meta["cid"] = cid
        meta["pid"] = pid
        if not pid:
            meta["pid_from_ancestors"] = find_pid_from_ancestors(p)
        # also check inside text for Pxxx patterns
        if not meta["pid"] and text:
            meta["pid_in_text"] = find_pid_in_text(text)
    except Exception:
        # ignore parsing problems
        pass

    return text, meta
