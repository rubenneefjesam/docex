#!/usr/bin/env python3
# enrich_review_queue.py
# Usage: python tools/enrich_review_queue.py index_review_queue.csv > index_review_queue.enriched.csv

import sys
import csv
import hashlib
from pathlib import Path

sys.path.insert(0, "src")
from webapp.assistants.project_assistant.tools.chatbot.indexer.io_utils_extended import read_and_meta

if len(sys.argv) != 2:
    print("Usage: python tools/enrich_review_queue.py path/to/index_review_queue.csv", file=sys.stderr)
    sys.exit(2)

infile = Path(sys.argv[1])
if not infile.exists():
    print("Input CSV not found:", infile, file=sys.stderr)
    sys.exit(1)

outpath = infile.with_suffix(".enriched.csv")

rows = []
with infile.open("r", encoding="utf-8") as fh:
    r = csv.DictReader(fh)
    fieldnames = list(r.fieldnames or [])
    # add new fields if not present
    for add in ("file_fingerprint_current", "extractor_counts", "extractor_sample"):
        if add not in fieldnames:
            fieldnames.append(add)
    for row in r:
        fp = row.get("filepath") or row.get("path") or row.get("filepath")
        if not fp:
            row["file_fingerprint_current"] = ""
            row["extractor_counts"] = ""
            row["extractor_sample"] = ""
            rows.append(row)
            continue
        p = Path(fp)
        if p.exists():
            try:
                data = p.read_bytes()
                sha = hashlib.sha1(data).hexdigest()
            except Exception:
                sha = ""
            try:
                txt, meta = read_and_meta(p)
                counts = meta.get("extractor_counts") or {}
                sample = (meta.get("sample") or "")[:400].replace("\n", " ")
            except Exception:
                counts = {}
                sample = ""
        else:
            sha = ""
            counts = {}
            sample = ""
        row["file_fingerprint_current"] = sha
        row["extractor_counts"] = repr(counts)
        row["extractor_sample"] = sample
        rows.append(row)

with outpath.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print("Wrote enriched CSV:", outpath)
