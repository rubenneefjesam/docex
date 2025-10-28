"""
Verbeterde INDEX BUILDER
------------------------
Indexeert alle documenten in ./data, inclusief CSV's.
Koppelt automatisch ClientID ↔ ProjectID via bestandsnaam + mappingbestand.

Gebruik:
    python -m src.webapp.assistants.project_assistant.tools.chatbot.index_builder \
      --data-dir src/webapp/assistants/project_assistant/tools/chatbot/data \
      --output-dir src/webapp/assistants/project_assistant/tools/chatbot/index \
      --mapping-file src/webapp/assistants/project_assistant/tools/chatbot/data/project_mapping.csv
"""

import argparse
import traceback
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

try:
    from .io_utils import read_text_from_file, chunk_text, parse_ids_from_filename
    from .embed_utils import Embedder, save_index
except Exception:
    from io_utils import read_text_from_file, chunk_text, parse_ids_from_filename
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

    mapping = {
        str(row["KlantID"]).strip().upper(): str(row["ProjectID"]).strip().upper()
        for _, row in df.iterrows()
    }
    print(f"📖 Mapping geladen ({len(mapping)} regels). Voorbeeld: {list(mapping.items())[:3]}")
    return mapping


def resolve_client_project(file_path: Path, mapping: Dict[str, str]) -> tuple[str, str]:
    """Combineert bestandsnaam + mapping om client_id en project_id te bepalen."""
    name = file_path.name
    cid, pid = parse_ids_from_filename(name)

    # Probeer client_id te vinden als die nog ontbreekt
    if not cid:
        match = re.search(r"(C\d{3,})", name.upper())
        if match:
            cid = match.group(1)

    # Probeer project_id te halen uit mapping of mapnaam
    if cid and not pid:
        pid = mapping.get(cid, file_path.parent.name.upper())

    # Fallbacks
    if not cid:
        cid = "LOCAL"
    if not pid:
        pid = "INDEX"

    # ✅ Speciale case: CSV's met mapping of projectinfo krijgen een vaste code
    if file_path.suffix.lower() == ".csv" and pid == "INDEX":
        cid, pid = "C000", "P999"

    return cid, pid


def _count_file(counters: Dict[str, int], ext: str) -> None:
    ext = ext.lower()
    counters[ext] = counters.get(ext, 0) + 1


# -----------------------------------------------------
# Hoofdproces
# -----------------------------------------------------
def build_index(data_dir: Path, output_dir: Path, mapping_file: Path) -> None:
    """Doorzoekt alle bestanden in data_dir, koppelt client/project via mapping, embedt, en slaat op."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    mapping_path = Path(mapping_file)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Start indexering in: {data_dir.resolve()}")
    mapping = load_mapping(mapping_path)

    embedder = Embedder()
    all_files = [p for p in data_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    print(f"📂 {len(all_files)} bestanden gevonden...\n")

    stats: Dict[str, int] = {}
    unknowns: List[str] = []

    for file_path in tqdm(all_files, desc="Bestanden verwerken"):
        try:
            text = read_text_from_file(file_path)
            if not text.strip():
                continue

            client_id, project_id = resolve_client_project(file_path, mapping)
            if project_id in {"INDEX", "UNKNOWN"}:
                unknowns.append(f"{file_path.name} → {client_id}/{project_id}")

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

    # ----------------------------
    # Rapportage
    # ----------------------------
    print("\n✅ Indexatieoverzicht:")
    total = 0
    for k, v in sorted(stats.items()):
        print(f"   • {k:<20} → {v} chunks opgeslagen")
        total += v

    print(f"\n📊 Totaal {total} chunks geïndexeerd over {len(stats)} client/project-combinaties.")

    if unknowns:
        print("\n⚠️  Waarschuwing: bestanden met onduidelijk project_id:")
        for u in unknowns:
            print(f"   - {u}")
    else:
        print("\n✅ Geen onduidelijke client/project combinaties gevonden.")


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
