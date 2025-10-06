# tests/test_indexer.py
"""
Eenvoudige integratietest voor de indexer:
- maakt tijdelijke data map met small CSVs en 1 txt-document
- gebruikt DummyEmbedder (geen dependencies)
- roept index_clients_projects_from_csv() en index_documents()
- printt resultaten en doet eenvoudige assertions
"""

import tempfile
from pathlib import Path
import shutil
import os
import sys
import json

# voeg project root toe zodat imports werken als je vanuit repository root runt
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# import de modules (passen bij jouw package-structuur)
try:
    from indexer.index_csvs_modular import index_clients_projects_from_csv, index_documents, DATA_DIR as IDX_DATA_DIR
except Exception as e:
    print("Fout bij import indexer modules:", e)
    raise

# Dummy embedder (eenvoudig, constant-dim)
class DummyEmbedder:
    def __init__(self, dim=8):
        self.dim = dim
    def embed(self, texts):
        # return fixed-dimension zero-vectors for each input
        return [[0.0]*self.dim for _ in texts]

def write_csv(path: Path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(headers) + "\n")
        for r in rows:
            fh.write(",".join(r) + "\n")

def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="indexer_test_"))
    print("Temporary test dir:", tmpdir)
    data_dir = tmpdir / "data"
    data_dir.mkdir()
    # create small clients CSV and projects CSV
    clients_csv = data_dir / "Clients_test.csv"
    projects_csv = data_dir / "Projects_test.csv"

    # CSV headers tolerant to parser (KlantID and ProjectID)
    write_csv(clients_csv, ["KlantID","ProjectID","Name"], [
        ["C001","P1001","Client One"],
        ["C002","P1002","Client Two"]
    ])
    write_csv(projects_csv, ["ProjectID","ProjectName"], [
        ["P1001","Project One"],
        ["P1002","Project Two"]
    ])

    # create a sample txt file for client C001 (filename contains client id)
    doc1 = data_dir / "woning_C001_P1001_document.txt"
    doc1.write_text("Dit is een test document\nBetreft project P1001\nKlant C001\nExtra tekst.", encoding="utf-8")

    # create another sample for C002
    doc2 = data_dir / "brief_C002_P1002_doc.txt"
    doc2.write_text("Correspondentie\nBetreft P1002\nKlant C002\nNog wat tekst.", encoding="utf-8")

    # now run the indexers using DummyEmbedder
    embedder = DummyEmbedder(dim=8)

    # call CSV indexer
    proj_to_clients = index_clients_projects_from_csv(clients_csv, projects_csv, embedder)
    print("proj_to_clients:", proj_to_clients)
    assert isinstance(proj_to_clients, dict), "proj_to_clients should be dict"
    assert "P1001" in proj_to_clients and "C001" in proj_to_clients["P1001"]

    # call document indexer
    chunks_created = index_documents(data_dir, proj_to_clients, embedder)
    print("chunks_created:", chunks_created)
    assert isinstance(chunks_created, int)
    assert chunks_created > 0, "Expected at least some chunks created"

    # basic check for index files in index folder (best-effort)
    # the index modules often write to index folder relative to module; search for files containing "C001" or "P1001"
    index_folder = REPO_ROOT / "indexer" / "index"
    found = []
    if index_folder.exists():
        for p in index_folder.iterdir():
            if p.is_file() and ("C001" in p.name or "P1001" in p.name):
                found.append(p)
    print("index files found (sample):", found[:10])

    # cleanup
    print("Cleaning up temporary test dir:", tmpdir)
    shutil.rmtree(tmpdir)
    print("Test completed OK.")

if __name__ == "__main__":
    main()
