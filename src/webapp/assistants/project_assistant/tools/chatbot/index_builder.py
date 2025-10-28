# chatbot/index_builder.py
"""
INDEX BUILDER (met Excel/CSV mapping)
-------------------------------------
Indexeert alle documenten in ./data, koppelt automatisch ClientID ↔ ProjectID
via een mappingbestand (CSV of Excel), en slaat embeddings + metadata per
(client, project) op in ./index.

Gebruik:
    python -m src.webapp.assistants.project_assistant.tools.chatbot.index_builder \
      --data-dir src/webapp/assistants/project_assistant/tools/chatbot/data \
      --output-dir src/webapp/assistants/project_assistant/tools/chatbot/index \
      --mapping-file project_mapping.csv
"""

import argparse
import traceback
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

# Imports (werken in module- en standalone-modus)
try:
    from .io_utils import read_text_from_file, chunk_text
    from .embed_utils import Embedder, save_index
except Exception:
    from io_utils import read_text_from_file, chunk_text
    from embed_utils import Embedder, save_index


SUPPORTED_EXTS = {".pdf", ".docx", ".txt", ".csv"}


# -----------------------------------------------------
# Helpers
# -----------------------------------------------------
def load_mapping(mapping_path: Path) -> Dict[str, str]:
    """Lees KlantID → ProjectID mapping uit CSV of Excel."""
    if not mapping_path.exists():
        print(f"⚠️  Geen mappingbestand gevonden op {mapping_path}, gebruik INDEX als fallback.")
        return {}

    if mapping_path.suffix.lower() == ".csv":
        df = pd.read_csv(mapping_path)
    else:
        df = pd.read_excel(mapping_path)

    df.columns = [c.strip() for c in df.columns]
    if "KlantID" not in df.columns or "ProjectID" not in df.columns:
        raise ValueError("Mappingbestand mist kolommen 'KlantID' en/of 'ProjectID'.")

    mapping = {row["KlantID"].strip().upper(): row["ProjectID"].strip().upper() for _, row in df.iterrows()}
    print(f"📖 Mapping geladen ({len(mapping)} regels). Voorbeeld: {list(mapping.items())[:3]}")
    return mapping


def parse_client_project_with_mapping(filename: str, mapping: Dict[str, str]) -> tuple[str, str]:
    """Zoekt client_id in bestandsnaam en koppelt project_id via mapping."""
    fname = filename.upper()
    c = re.search(r"C\d{3,}", fname)
    client_id = c.group(0) if c else "LOCAL"
    project_id = mapping.get(client_id, "INDEX")
    return client_id, project_id


def _count_file(counters: Dict[str, int], ext: str) -> None:
    ext = ext.lower()
    if ext == ".pdf":
        counters["pdf"] += 1
    elif ext == ".docx":
        counters["docx"] += 1
    elif ext == ".csv":
        counters["csv"] += 1
    elif ext == ".txt":
        counters["txt"] += 1
    else:
        counters["other"] += 1


# -----------------------------------------------------
# Hoofdproces
# -----------------------------------------------------
def build_index(data_dir: Path, output_dir: Path, mapping_file: Path) -> None:
    """Doorzoekt alle bestanden in data_dir, koppelt client/project via mapping, embedt, en slaat op."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    mapping_path = Path(mapping_file)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Start multi-indexering in: {data_dir.resolve()}")
    mapping = load_mapping(mapping_path)

    embedder = Embedder()
    all_files = [p for p in data_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    print(f"📂 {len(all_files)} bestanden gevonden...\n")

    # counters per client/project
    stats: Dict[str, int] = {}

    for file_path in tqdm(all_files, desc="Bestanden verwerken"):
        try:
            text = read_text_from_file(file_path)
            if not text.strip():
                continue

            client_id, project_id = parse_client_project_with_mapping(file_path.name, mapping)
            chunks = chunk_text(text) or [text]
            embeddings = embedder.embed_texts(chunks)

            save_index(
                client_id=client_id,
                project_id=project_id,
                chunks=[{"text": c, "source_path": str(file_path)} for c in chunks],
                embeddings=embeddings,
            )

            key = f"{client_id}/{project_id}"
            stats[key] = stats.get(key, 0) + len(chunks)

        except Exception as e:
            print(f"⚠️  Fout bij {file_path.name}: {e}")
            traceback.print_exc()

    print("\n✅ Indexatieoverzicht:")
    total = 0
    for k, v in stats.items():
        print(f"   • {k:<15} → {v} chunks opgeslagen")
        total += v

    print(f"\n📊 Totaal {total} chunks geïndexeerd over {len(stats)} client/project-combinaties.\n")


# -----------------------------------------------------
# CLI
# -----------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexeer documenten met Client/Project mapping.")
    parser.add_argument("--data-dir", type=Path, required=True, help="Map met documenten (PDF/DOCX/TXT/CSV).")
    parser.add_argument("--output-dir", type=Path, required=True, help="Map waar index wordt opgeslagen.")
    parser.add_argument("--mapping-file", type=Path, required=True, help="Pad naar CSV/Excel mappingbestand.")
    args = parser.parse_args()

    build_index(args.data_dir, args.output_dir, args.mapping_file)
