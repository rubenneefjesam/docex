# chatbot/index_builder.py
"""
FINAL INDEX BUILDER
-------------------
Indexeert alle documenten in ./data en slaat embeddings + metadata op in ./index.
Gebruikt bestaande hulpfuncties in io_utils, embed_utils en index_utils.

Gebruik:
    python -m chatbot.index_builder --data-dir ./chatbot/data --output-dir ./chatbot/index
"""

import argparse
import traceback
from pathlib import Path
from tqdm import tqdm

# interne imports
from io_utils import read_text_from_file, chunk_text
from embed_utils import Embedder
from index_utils import save_index


def build_index(data_dir: Path, output_dir: Path):
    """Doorzoekt alle bestanden in data_dir, maakt embeddings en slaat de index op."""
    print(f"🚀 Start indexeren van documenten in: {data_dir.resolve()}")
    output_dir.mkdir(parents=True, exist_ok=True)

    embedder = Embedder()
    all_texts, all_meta = [], []
    counters = {"pdf": 0, "docx": 0, "csv": 0, "txt": 0, "other": 0}

    # doorzoek alle submappen
    all_files = list(data_dir.rglob("*"))
    print(f"📂 {len(all_files)} bestanden gevonden om te verwerken...\n")

    for file_path in tqdm(all_files, desc="Bestanden verwerken"):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if ext not in [".pdf", ".docx", ".txt", ".csv"]:
            counters["other"] += 1
        elif ext == ".pdf":
            counters["pdf"] += 1
        elif ext == ".docx":
            counters["docx"] += 1
        elif ext == ".csv":
            counters["csv"] += 1
        elif ext == ".txt":
            counters["txt"] += 1

        try:
            text = read_text_from_file(file_path)
            if not text.strip():
                continue

            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_texts.append(chunk)
                all_meta.append({
                    "source": str(file_path),
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                })

        except Exception as e:
            print(f"⚠️  Fout bij lezen van {file_path.name}: {e}")
            traceback.print_exc()

    if not all_texts:
        print("❌ Geen tekst gevonden om te indexeren.")
        return

    print(f"\n📊 Statistieken:")
    for k, v in counters.items():
        print(f"   • {k.upper():<5}: {v}")

    print(f"\n🧩 Totaal {len(all_texts)} tekstblokken gevonden — embeddings genereren...")

    # embeddings maken
    embeddings = embedder.embed_texts(all_texts)

    # index opslaan
    save_index(output_dir, embeddings, all_meta)

    print(f"\n✅ Indexeren voltooid!")
    print(f"   → Embeddings & metadata opgeslagen in: {output_dir.resolve()}")
    print(f"   → Aantal chunks: {len(all_texts)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexeer documenten in een opgegeven map.")
    parser.add_argument("--data-dir", type=Path, required=True, help="Pad naar de map met documenten.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Pad waar de index wordt opgeslagen.")
    args = parser.parse_args()

    build_index(args.data_dir, args.output_dir)
