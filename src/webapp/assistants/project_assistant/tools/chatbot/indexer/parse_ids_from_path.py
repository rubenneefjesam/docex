# parse_ids_from_path.py
from pathlib import Path
import re
from typing import Tuple, Optional

def parse_ids_from_path(path_like: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse client and project ids from a Path (bestandspad en -naam).
    Zoekt naar patronen C\d{1,6} en P\d{1,6} in zowel filename als parent folders.
    Retourneert (client_id_or_None, project_id_or_None).
    """
    try:
        p = Path(path_like)
    except Exception:
        return None, None

    s = (p.name + " " + " ".join([part for part in p.parts[-3:]])).upper()  # naam + laatste mappen
    cid = None
    pid = None

    m_c = re.search(r"(C\d{1,6})", s)
    if m_c:
        cid = m_c.group(1)

    m_p = re.search(r"(P\d{1,6})", s)
    if m_p:
        pid = m_p.group(1)

    return cid, pid
