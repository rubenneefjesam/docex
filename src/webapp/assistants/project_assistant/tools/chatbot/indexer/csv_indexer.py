# csv_indexer.py
"""
Lightweight CSV reader to build project -> clients mapping.

Exports:
    index_clients_projects_from_csv(clients_csv, projects_csv, embedder=None) -> Dict[str, List[str]]
"""
from pathlib import Path
from typing import Dict, List, Iterable, Any
import csv
import io

# Uitgebreidere aliassets (NL/EN varianten), case-insensitive
_CLIENT_KEYS = (
    "KlantID","ClientID","clientid","klantid","klant_id","client_id",
    "Klant","KlantNummer","Klantnummer","customer_id","customerid"
)
_PROJECT_KEYS = (
    "ProjectID","projectid","Project","project","project_id",
    "ProjectNr","ProjectNummer","Projectnummer","projectnr","projectnummer"
)

def _sniff_and_open(path: Path):
    """
    Open CSV met BOM- en delimiter-sniffing. Geeft (DictReader, filehandle) terug.
    Callers moeten filehandle open houden zolang reader gebruikt wordt.
    """
    p = Path(path)
    if not p.exists():
        return None, None
    raw = p.read_bytes()
    # BOM tolerant + text wrapper
    txt = raw.decode("utf-8-sig", errors="ignore")
    sample = txt[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except Exception:
        dialect = csv.get_dialect("excel")
    fh = io.StringIO(txt)
    reader = csv.DictReader(fh, dialect=dialect)
    return reader, fh

def _get_first_matching(row: Dict[str, Any], candidates: Iterable[str]) -> str:
    if not row:
        return ""
    # directe
    for k in candidates:
        if k in row and (row[k] is not None) and str(row[k]).strip():
            return str(row[k]).strip()
    # case-insensitive
    lower_map = {(k or "").strip().lower(): v for k, v in row.items()}
    for k in candidates:
        v = lower_map.get(k.lower())
        if v and str(v).strip():
            return str(v).strip()
    # tolerante match
    cand_lower = {c.lower() for c in candidates}
    for key, val in row.items():
        if key and key.strip().lower() in cand_lower and val and str(val).strip():
            return str(val).strip()
    return ""

def _norm_id(val: str, kind: str) -> str:
    """
    Normaliseer ID's: uppercase, verwijder spaties, forceer C/P prefix indien ontbreekt.
    """
    if not val:
        return ""
    v = str(val).strip().upper()
    v = v.replace(" ", "")
    if kind == "client" and not v.startswith("C") and v.isdigit():
        v = "C" + v
    if kind == "project" and not v.startswith("P") and v.replace("P","").isdigit() is False:
        # als bv. '1234' → 'P1234'
        digits = re_sub_digits(v)
        if digits:
            v = "P" + digits
    return v

def re_sub_digits(v: str) -> str:
    import re
    m = re.search(r"(\d{1,6})", v)
    return m.group(1) if m else ""

def _open_csv(path: Path):
    reader, fh = _sniff_and_open(path)
    if reader is None:
        return []
    rows = [dict(r) for r in reader]
    fh.close()
    return rows

def index_clients_projects_from_csv(clients_csv, projects_csv, embedder=None) -> Dict[str, List[str]]:
    """
    Lees clients_csv en projects_csv en return mapping: { ProjectID: [KlantID, ...] }.
    """
    clients = _open_csv(Path(clients_csv))
    projects = _open_csv(Path(projects_csv))

    proj_to_clients: Dict[str, List[str]] = {}
    missing_client, missing_project = 0, 0

    # Build mapping vanuit clients
    for r in clients:
        cid = _get_first_matching(r, _CLIENT_KEYS)
        pid = _get_first_matching(r, _PROJECT_KEYS)
        if not cid:
            missing_client += 1
        if not pid:
            missing_project += 1
        if cid and pid:
            cid_n = _norm_id(cid, "client")
            pid_n = _norm_id(pid, "project")
            if not cid_n or not pid_n:
                continue
            lst = proj_to_clients.setdefault(pid_n, [])
            if cid_n not in lst:
                lst.append(cid_n)

    # Zorg dat alle projecten bestaan als key
    total_projects_rows = 0
    for r in projects:
        pid = _get_first_matching(r, _PROJECT_KEYS)
        if pid:
            pid_n = _norm_id(pid, "project")
            proj_to_clients.setdefault(pid_n, proj_to_clients.get(pid_n, []))
            total_projects_rows += 1

    # Samenvatting
    print(
        f"[csv_indexer] loaded clients_rows={len(clients)} projects_rows={len(projects)} "
        f"mapped_projects={len(proj_to_clients)} "
        f"missing_client_fields={missing_client} missing_project_fields_in_clients={missing_project} "
        f"projects_present={total_projects_rows}"
    )

    return proj_to_clients
