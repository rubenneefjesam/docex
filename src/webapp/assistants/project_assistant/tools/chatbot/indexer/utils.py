# src/.../indexer/utils.py
from typing import Dict
def row_to_text(prefix: str, row: Dict) -> str:
    parts = [f\"{k}: {v}\" for k, v in row.items()]
    return f\"{prefix}\\n\" + \"\\n\".join(parts)

def write_csv(path, headers, rows):
    \"\"\"Helper voor tests of review queue\"\"\"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, \"w\", encoding=\"utf-8\", newline=\"\") as fh:
        fh.write(\",\".join(headers) + \"\\n\")
        for r in rows:
            fh.write(\",\".join(r) + \"\\n\")