# test_index_builder.py
"""
Testscript voor index_builder.py
Controleert of indexeren werkt en of indexbestanden bestaan.
"""

from pathlib import Path
import json
import numpy as np
from index_builder import build_index

DATA_DIR = Path("./chatbot/data")
OUTPUT_DIR = Path("./chatbot/index/test_run")

def test_index_builder():
    print("🚀 Test indexeren gestart...")
    build_index(DATA_DIR, OUTPUT_DIR)

    npy_files = list(OUTPUT_DIR.glob("*.npy"))
    json_files = list(OUTPUT_DIR.glob("*.json"))

    assert npy_files, "Geen .npy-bestand gevonden!"
    assert json_files, "Geen .json-bestand gevonden!"

    print(f"✅ Gevonden indexbestanden: {len(npy_files)} NPY, {len(json_files)} JSON")

    meta = json.load(open(json_files[0], "r", encoding="utf-8"))
    embeddings = np.load(npy_files[0])

    print(f"📊 Aantal chunks: {len(meta)}")
    print(f"📏 Embedding shape: {embeddings.shape}")
    print("🎉 Test succesvol afgerond!")


if __name__ == "__main__":
    test_index_builder()
