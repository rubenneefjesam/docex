# src/.../indexer/utils.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterable, Sequence, Any
import csv

def row_to_text(prefix: str, row: Dict[str, Any]) -> str:
    """
    Zet een dict-row om naar een tekstblok:
    prefix
    key1: value1
    key2: value2
    """
    parts = [f"{k}: {v}" for k, v in row.items()]
    return f"{prefix}\n" + "\n".join(parts)

def write_csv(path: Path | str, headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    """
    Schrijft een CSV-bestand veilig weg:
    - path kan een Path of str zijn
    - values worden naar str geconverteerd
    - correcte quoting via csv.writer
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Use newline="" when writing CSV to avoid extra blank lines on Windows.
    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(list(headers))
        for r in rows:
            # convert values to strings, replace None -> empty string
            writer.writerow(["" if x is None else str(x) for x in r])
