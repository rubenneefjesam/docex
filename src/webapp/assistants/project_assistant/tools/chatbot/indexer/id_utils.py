# id_utils.py
from pathlib import Path
from typing import Tuple, Optional
import re

# hergebruikt door modules: deze wrapper verzamelt ID-hulpen
from .norm_id import norm_id
from .parse_ids_from_path import parse_ids_from_path

def parse_ids_from_filename_or_path(path_like: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Wrapper: probeer meerdere strategieën op het pad/filename:
      1) parse_ids_from_path (bestandspad + naam)
      2) losse parse op filename
    Retourneert genormaliseerde ids (via norm_id).
    """
    cid, pid = parse_ids_from_path(path_like)
    if cid:
        cid = norm_id(cid, "client")
    if pid:
        pid = norm_id(pid, "project")

    if cid or pid:
        return cid, pid

    # fallback: snel parse filename alleen (extra tolerantie)
    try:
        s = Path(path_like).name.upper()
        m_c = re.search(r"(C\d{1,6})", s)
        m_p = re.search(r"(P\d{1,6})", s)
        if m_c:
            cid = norm_id(m_c.group(1), "client")
        if m_p:
            pid = norm_id(m_p.group(1), "project")
    except Exception:
        pass

    return cid, pid


def find_pid_from_ancestors(path_like: Path) -> Optional[str]:
    """
    Kijk in parent en grandparent mapnamen naar P\d+.
    Return genormaliseerde Pxxx of None.
    """
    p = Path(path_like)
    for anc in (p.parent, p.parent.parent):
        if not anc:
            continue
        m = re.search(r"(P\d{1,6})", anc.name.upper())
        if m:
            return norm_id(m.group(1), "project")
    return None


def find_pid_in_text(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\b(P\d{1,6})\b", text.upper())
    if m:
        return norm_id(m.group(1), "project")
    return None
