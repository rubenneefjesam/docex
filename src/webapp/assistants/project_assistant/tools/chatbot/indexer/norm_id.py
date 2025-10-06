# norm_id.py
from typing import Optional

def norm_id(val: Optional[str], kind: str) -> Optional[str]:
    """
    Normaliseert client- of project-ID's.
    - client: 'C123' of '123' -> 'C123'
    - project: 'P123' or '123' -> 'P123'
    Returns None bij lege input.
    """
    if val is None:
        return None
    v = str(val).strip().upper().replace(" ", "")
    if not v:
        return None
    if kind == "client":
        if v.startswith("C"):
            return v
        if v.isdigit():
            return "C" + v
    if kind == "project":
        if v.startswith("P"):
            return v
        if v.isdigit():
            return "P" + v
    return v
