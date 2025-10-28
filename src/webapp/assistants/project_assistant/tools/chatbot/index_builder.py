# index_builder.py
"""
Multi-index builder — maakt per client_id/project_id aparte indexbestanden aan.
Gebruik:
    python -m src.webapp.assistants.project_assistant.tools.chatbot.index_builder \
        --data-dir src/webapp/assistants/project_assistant/tools/chatbot/data \
        --output-dir src/webapp/assistants/project_assistant/tools/chatbot/index
"""

import argparse
import traceback
from pathlib import Path
from typing import Dict, List, Any
from tqdm import tqdm

try:
    from .io_utils import read_text_from_file, chunk_text
    from .embed_utils import Embedder, save_index
except ImportError:
    from io_utils import read_text_from_file, chunk_text
    from embed_utils import Embedder, save_index


SUPPORTED_EXTS = {".pdf", ".docx", ".txt", ".csv"}


def parse_client_project(filename: str) -> (str, str):
    """Zoek patronen als _C001_ en _P001_ in bestandsnamen."""
    import re
    c = re.search(r"C\d{3,}", filename.upper())
    p = re.search(r"P\d{3,}", filename.upper())
    return (c.group(0) if c else "LOCAL", p.group(0) if p else "INDEX")


def build_index(data_dir: Path, output_dir: Path) -> None:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Start multi-indexering in: {data_dir.resolve()}")

    embedder = Embedder()
    counters: Dict[str, int] = {}
    file_list = [p for p in data_dir.rglob("*") if p.is_file()]
    print(f"📂 {len(file_list)} bestanden gevonden...\n")

    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for f in tqdm(file_list, desc="Bestanden verwerken"):
        ext = f.suffix.lower()
        if ext not in SUPPORTED_EXTS:
            continue
        try:
            text = read_text_from_file(f)
            if not text.strip():
                continue
            chunks = chunk_text(text)
            cid, pid = parse_client_project(f.name)
            key = f"{cid}_{pid}"
            grouped.setdefault(cid, {}).setdefault(pid, [])
            for i, ch in enumerate(chunks):
                grouped[cid][pid].append(
                    {
                        "text": ch,
                        "source_path": str(f),
                        "chunk_id": i,
                        "total_chunks": len(chunks),
                        "ext": ext,
                    }
                )
        except Exception as e:
            print(f"⚠️  Fout bij {f.name}: {e}")
            traceback.print_exc()

    # Embeddings genereren en index per client/project opslaan
    total_chunks = 0
    for cid, projs in grouped.items():
        for pid, metas in projs.items():
            texts = [m["text"] for m in metas]
            embeddings = embedder.embed_texts(texts)
            save_index(cid, pid, metas, embeddings)
            total_chunks += len(metas)
            print(f"✅ {cid}/{pid} → {len(metas)} chunks opgeslagen")

    print(f"\n📊 Totaal {total_chunks} chunks geïndexeerd over {len(grouped)} clients.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_index(args.data_dir, args.output_dir)
