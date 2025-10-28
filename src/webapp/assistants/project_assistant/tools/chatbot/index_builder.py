# index_builder.py
"""
Final index_builder.py
Doel: alle bestanden in ./data indexeren en opslaan in ./index
Gebruikt bestaande hulpfuncties in io_utils, embed_utils en index_utils.
"""

import argparse
from pathlib import Path
from io_utils import read_text_from_file, chunk_text
from embed_utils import Embedder
from index_utils import save_index
import traceback
from tqdm import tqdm


def build_index(data_dir: Path, output_dir: Path):
    """Doorzoekt alle bestanden, maakt embeddings en slaat index op."""
    embedder = Embedder()
    all_chunks, all_meta = [], []

    print(f"🔍 Start indexeren in: {data_dir.resolve()}")

    for file_path in tqdm(list(data_dir.rglob("*")), desc="📂 Bestanden verwerken"):
        if not file_path.is_file():
            continue
        try:
            text = read_text_from_file(file_path)
            if not text.strip():
                continue

            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_meta.append({
                    "source": str(file_path),
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                })

        except Exception as e:
            print(f"⚠️ Fout bij lezen van {file_path.name}: {e}")
            traceback.print_exc()

    print(f"📈 {len(all_chunks)} tekstblokken gevonden. Embeddings genereren...")

    embeddings = embedder.embed_texts(all_chunks)

    print(f"💾 Opslaan naar {output_dir.resolve()} ...")
    output_dir.mkdir(parents=True, exist_ok=True)
    save_index(output_dir, embeddings, all_meta)

    print("✅ Indexeren voltooid!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexeer alle documenten in een map.")
    parser.add_argument("--data-dir", type=Path, required=True, help="Pad naar data-map")
    parser.add_argument("--output-dir", type=Path, required=True, help="Pad naar index-map")
    args = parser.parse_args()

    build_index(args.data_dir, args.output_dir)
