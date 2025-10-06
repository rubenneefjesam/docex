# tests/test_indexer.py
"""
Robuuste integratietest die het indexer-module via zijn package-pad importeert.
- zoekt src/**/index_csvs_modular.py
- bepaalt het package-module pad t.o.v. src (bv. webapp.assistants.project_assistant.tools.chatbot.indexer.index_csvs_modular)
- importeert met importlib.import_module zodat relatieve imports in dat pakket werken
- gebruikt DummyEmbedder (geen externe deps)
"""

import tempfile
from pathlib import Path
import shutil
import sys
import importlib
import traceback
import os

# Zorg dat 'src' op sys.path staat zodat we webapp.* modules kunnen importeren
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if not SRC_DIR.exists():
    print(f"[ERROR] src directory niet gevonden: {SRC_DIR}")
    raise SystemExit(1)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Vind het concrete index_csvs_modular.py bestand ergens onder src
candidates = list(SRC_DIR.rglob("index_csvs_modular.py"))
if not candidates:
    print("[ERROR] kon index_csvs_modular.py niet vinden onder src/")
    raise SystemExit(1)

# Kies candidate die in een 'indexer' folder staat bij voorkeur
index_csv_path = None
for p in candidates:
    if "indexer" in [part.lower() for part in p.parts]:
        index_csv_path = p
        break
if index_csv_path is None:
    index_csv_path = candidates[0]

print(f"[INFO] Found index module file at: {index_csv_path}")

# Bepaal package/module naam t.o.v. SRC_DIR
try:
    rel = index_csv_path.relative_to(SRC_DIR).with_suffix("")  # remove .py
    module_name = ".".join(rel.parts)  # e.g. webapp.assistants....indexer.index_csvs_modular
except Exception as e:
    print("[ERROR] kon relatieve module-naam niet bepalen:", e)
    raise

print(f"[INFO] Importing module by name: {module_name}")

# Importeer het module via zijn package pad (zodat relatieve imports werken)
try:
    index_mod = importlib.import_module(module_name)
except Exception:
    print("[ERROR] Import via package-name mislukt; traceback:")
    traceback.print_exc()
    raise

# Verwachtte functies
if not hasattr(index_mod, "index_clients_projects_from_csv") or not hasattr(index_mod, "index_documents"):
    print("[ERROR] geladen module bevat niet de verwachte functies (index_clients_projects_from_csv/index_documents)")
    raise SystemExit(1)

# Dummy embedder minimale implementatie
class DummyEmbedder:
    def __init__(self, dim=384):
        self.dim = dim
    def embed(self, texts):
        return [[0.0]*self.dim for _ in texts]

# helper om csvs te schrijven
def write_csv(path: Path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(headers) + "\n")
        for r in rows:
            fh.write(",".join(r) + "\n")

def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="indexer_test_"))
    print("Temporary test dir:", tmpdir)
    data_dir = tmpdir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # create small clients CSV and projects CSV
    clients_csv = data_dir / "Clients_test.csv"
    projects_csv = data_dir / "Projects_test.csv"

    write_csv(clients_csv, ["KlantID","ProjectID","Name"], [
        ["C001","P1001","Client One"],
        ["C002","P1002","Client Two"]
    ])
    write_csv(projects_csv, ["ProjectID","ProjectName"], [
        ["P1001","Project One"],
        ["P1002","Project Two"]
    ])

    # create two small sample txt documents
    doc1 = data_dir / "woning_C001_P1001_document.txt"
    doc1.write_text("Dit is een test document\nBetreft project P1001\nKlant C001\nExtra tekst.", encoding="utf-8")

    doc2 = data_dir / "brief_C002_P1002_doc.txt"
    doc2.write_text("Correspondentie\nBetreft P1002\nKlant C002\nNog wat tekst.", encoding="utf-8")

    # instantiate dummy embedder and call functions from imported module
    embedder = DummyEmbedder(dim=8)

    try:
        proj_to_clients = index_mod.index_clients_projects_from_csv(clients_csv, projects_csv, embedder)
    except Exception:
        print("[ERROR] index_clients_projects_from_csv faalde; traceback:")
        traceback.print_exc()
        shutil.rmtree(tmpdir)
        raise

    print("proj_to_clients:", proj_to_clients)
    if not isinstance(proj_to_clients, dict):
        print("[ERROR] index_clients_projects_from_csv returned geen dict")
        shutil.rmtree(tmpdir)
        raise SystemExit(1)

    try:
        chunks_created = index_mod.index_documents(data_dir, proj_to_clients, embedder)
    except Exception:
        print("[ERROR] index_documents faalde; traceback:")
        traceback.print_exc()
        shutil.rmtree(tmpdir)
        raise

    print("chunks_created:", chunks_created)
    if not isinstance(chunks_created, int) or chunks_created < 0:
        print("[ERROR] index_documents returned onverwachte waarde:", chunks_created)

    # cleanup
    print("Cleaning up temporary test dir:", tmpdir)
    shutil.rmtree(tmpdir)
    print("Test completed OK.")

if __name__ == "__main__":
    main()
