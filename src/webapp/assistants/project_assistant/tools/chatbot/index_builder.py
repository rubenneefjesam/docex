# src/webapp/assistants/project_assistant/tools/chatbot/index_builder.py
"""
Verbeterde INDEX BUILDER (accumulerend per client/project)
----------------------------------------------------------
Voorkomt dat indexbestanden bij elke file-iteratie worden overschreven.
"""

import argparse
import traceback
import re
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
import pandas as pd
from tqdm import tqdm

try:
    from .io_utils import read_text_from_file, chunk_text, parse_ids_from_filename
    from .embed_utils import Embedder, save_index
except Exception:
    from io_utils import read_text_from_file, chunk_text, parse_ids_from_filename
    from embed_utils import Embedder, save_index


SUPPORTED_EXTS = {".pdf", ".docx", ".txt", ".csv"}


def load_mapping(mapping_path: Path) -> Dict[str, str]:
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


def detect_ids_in_text(text: str) -> tuple[str | None, str | None]:
    client_match = re.search(r"\bC\d{3,}\b", text.upper())
    project_match = re.search(r"\bP\d{4,}\b", text.upper())
    return (
        client_match.group(0) if client_match else None,
        project_match.group(0) if project_match else None,
    )


def resolve_client_project(file_path: Path, mapping: Dict[str, str]) -> tuple[str, str]:
    name = file_path.name
    cid, pid = parse_ids_from_filename(name)
    if not cid:
        m = re.search(r"(C\d{3,})", name.upper())
        if m:
            cid = m.group(1)
    if not pid:
        m = re.search(r"(P\d{4,})", name.upper())
        if m:
            pid = m.group(1)

    if not cid or not pid:
        try:
            preview_text = read_text_from_file(file_path)[:5000]
            t_cid, t_pid = detect_ids_in_text(preview_text)
            cid = cid or t_cid
            pid = pid or t_pid
        except Exception:
            pass

    if cid and not pid:
        pid = mapping.get(cid, file_path.parent.name.upper())
    if not cid:
        cid = "LOCAL"
    if not pid:
        pid = "INDEX"
    if file_path.suffix.lower() == ".csv" and pid == "INDEX":
        cid, pid = "C000", "P999"
    return cid, pid


def build_index(data_dir: Path, output_dir: Path, mapping_file: Path) -> None:
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
    aggregated: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"chunks": [], "embs": []})
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

            key = f"{client_id}/{project_id}"
            aggregated[key]["chunks"].extend(
                [{"text": c, "source_path": str(file_path)} for c in chunks]
            )
            aggregated[key]["embs"].extend(embeddings)
            stats[key] = stats.get(key, 0) + len(chunks)

        except Exception as e:
            print(f"⚠️  Fout bij {file_path.name}: {e}")
            traceback.print_exc()

    # 🔥 Schrijf alle combinaties pas hier weg
    for key, data in aggregated.items():
        cid, pid = key.split("/")
        save_index(cid, pid, data["chunks"], data["embs"])

    # Rapportage
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexeer documenten met Client/Project mapping of tekstdetectie.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mapping-file", type=Path, required=True)
    args = parser.parse_args()
    build_index(args.data_dir, args.output_dir, args.mapping_file)
