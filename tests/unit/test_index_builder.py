# tests/unit/test_index_builder.py
"""
Final standalone test for chatbot/index_builder.py
Werkt direct, ongeacht of chatbot/__init__.py bestaat.
Maakt zelf testbestanden aan, zodat de test hermetisch is.
"""

from pathlib import Path
import sys, json, numpy as np

# Repo-root: /workspaces/docex (2 niveaus omhoog vanaf ./tests/unit)
ROOT = Path(__file__).resolve().parents[2]
CHATBOT_DIR = ROOT / "chatbot"
CHATBOT_DIR.mkdir(exist_ok=True)
(CHATBOT_DIR / "__init__.py").touch(exist_ok=True)

# Zorg dat de repo-root op sys.path staat (zodat 'chatbot.*' importeerbaar is)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chatbot.index_builder import build_index


def _seed_test_data(base_dir: Path) -> Path:
    """Maak een tijdelijke data-map met een paar kleine tekstbestanden."""
    data_dir = base_dir / "data_for_test"
    data_dir.mkdir(parents=True, exist_ok=True)

    # drie kleine bestanden (txt/csv) om de pipeline te testen
    (data_dir / "doc1.txt").write_text("Dit is een kleine test. " * 50, encoding="utf-8")
    (data_dir / "doc2.txt").write_text("Nog een document met voldoende tekst om te chunk-en. " * 40, encoding="utf-8")
    (data_dir / "tabel.csv").write_text("kolom1,kolom2\nA,1\nB,2\nC,3\n", encoding="utf-8")

    return data_dir


def test_index_builder(tmp_path):
    """End-to-end test voor index_builder met eigen testdata."""
    # Seed testdata in een tijdelijke map, zodat test altijd werkt
    data_dir = _seed_test_data(tmp_path)
    output_dir = tmp_path / "index_out"

    print(f"\n🚀 Start test-indexering vanuit {data_dir.resolve()}")
    build_index(data_dir, output_dir)

    npy_files = sorted(output_dir.glob("*.npy"))
    json_files = sorted(output_dir.glob("*.json"))

    assert npy_files, "Geen .npy-bestanden aangemaakt!"
    assert json_files, "Geen .json-bestanden aangemaakt!"

    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = json.load(f)

    arr = np.load(npy_files[0])
    print(f"✅ {len(meta)} chunks, embeddings shape = {arr.shape}")

    # Basischecks
    assert len(meta) == arr.shape[0], "Aantal metadata-items ≠ aantal embedding-rijen"
    assert arr.ndim == 2 and arr.shape[1] > 10, "Embeddings hebben onverwachte vorm"
    assert all("source" in m and "chunk_id" in m for m in meta), "Metadata mist verplichte sleutels"

    print("🎉 Test succesvol afgerond!\n")
