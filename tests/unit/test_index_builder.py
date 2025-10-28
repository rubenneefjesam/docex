# tests/unit/test_index_builder.py
"""
Final standalone test for chatbot/index_builder.py
Werkt direct, ongeacht of chatbot/__init__.py bestaat.
"""

from pathlib import Path
import sys, json, numpy as np

# Voeg automatisch het juiste pad toe
ROOT = Path(__file__).resolve().parents[2]   # → /workspaces/docex
CHATBOT_DIR = ROOT / "chatbot"
CHATBOT_DIR.mkdir(exist_ok=True)  # maakt map als die nog niet bestaat
init_file = CHATBOT_DIR / "__init__.py"
init_file.touch(exist_ok=True)    # maakt __init__.py als die ontbreekt

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chatbot.index_builder import build_index


def test_index_builder(tmp_path):
    """End-to-end test voor index_builder."""
    data_dir = CHATBOT_DIR / "data"
    output_dir = tmp_path / "index_out"

    print(f"\n🚀 Start test-indexering vanuit {data_dir.resolve()}")

    build_index(data_dir, output_dir)

    npy_files = list(output_dir.glob("*.npy"))
    json_files = list(output_dir.glob("*.json"))

    assert npy_files, "Geen .npy-bestanden aangemaakt!"
    assert json_files, "Geen .json-bestanden aangemaakt!"

    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = json.load(f)
    arr = np.load(npy_files[0])

    print(f"✅ {len(meta)} chunks, embeddings shape = {arr.shape}")
    assert len(meta) == arr.shape[0]
    assert arr.shape[1] > 10
    assert all("source" in m for m in meta)

    print("🎉 Test succesvol afgerond!\n")
