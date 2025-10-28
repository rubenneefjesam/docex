# tests/unit/test_index_builder.py
"""
Volledige test voor chatbot/index_builder.py
-------------------------------------------
Deze test controleert of de indexbuilder zonder fouten draait en of
er embeddings (.npy) en metadata (.json) worden aangemaakt.

Gebruik:
    pytest -q
"""

from pathlib import Path
import sys
import json
import numpy as np

# ✅ Voeg chatbot-map toe aan het Python pad
ROOT = Path(__file__).resolve().parents[2]   # → /workspaces/docex
CHATBOT_DIR = ROOT / "chatbot"
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from index_builder import build_index


def test_index_builder_end_to_end(tmp_path):
    """End-to-end test voor index_builder."""
    data_dir = CHATBOT_DIR / "data"
    output_dir = tmp_path / "index_out"

    print(f"\n🚀 Start test-indexering vanuit: {data_dir.resolve()}")

    # Bouw de index
    build_index(data_dir, output_dir)

    # Controleer of output bestaat
    npy_files = list(output_dir.glob("*.npy"))
    json_files = list(output_dir.glob("*.json"))

    assert npy_files, "❌ Geen .npy-bestand gevonden in output-map!"
    assert json_files, "❌ Geen .json-bestand gevonden in output-map!"

    # Controleer inhoud
    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = json.load(f)
    arr = np.load(npy_files[0])

    print(f"✅ Test succesvol: {len(meta)} chunks, embedding shape = {arr.shape}")
    assert len(meta) == arr.shape[0], "Aantal embeddings komt niet overeen met metadata"

    # Baseline sanity-checks
    assert arr.shape[1] > 10, "Embeddings lijken te klein, controleer embed_utils!"
    assert all("source" in m for m in meta), "Metadata mist 'source'-velden!"

    print("🎉 Alles werkt zoals verwacht!\n")
