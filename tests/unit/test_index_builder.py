# /workspaces/docex/tests/unit/test_index_builder.py
"""
Definitieve test voor chatbot.index_builder
-------------------------------------------
End-to-end test die controleert of de indexbuilder draait en output oplevert.
Gebruik:
    pytest tests/unit/test_index_builder.py -s
"""

from pathlib import Path
import json
import numpy as np
from chatbot.index_builder import build_index  # ✅ vaste pakketimport


def test_index_builder(tmp_path):
    """End-to-end test voor index_builder."""
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "chatbot" / "data"
    output_dir = tmp_path / "index_out"

    print(f"\n🚀 Test start: indexeren vanuit {data_dir.resolve()}")

    # Bouw de index
    build_index(data_dir, output_dir)

    # Controleer of output bestaat
    npy_files = list(output_dir.glob("*.npy"))
    json_files = list(output_dir.glob("*.json"))

    assert npy_files, "❌ Geen .npy-bestanden aangemaakt!"
    assert json_files, "❌ Geen .json-bestanden aangemaakt!"

    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = json.load(f)
    arr = np.load(npy_files[0])

    print(f"✅ Index succesvol: {len(meta)} chunks, embeddings shape = {arr.shape}")

    assert len(meta) == arr.shape[0], "Mismatch tussen aantal metadata-records en embeddings"
    assert arr.shape[1] > 10, "Embedding vector lijkt te klein"
    assert all("source" in m for m in meta), "Metadata mist 'source'-velden"

    print("🎉 Alles werkt zoals verwacht!\n")
