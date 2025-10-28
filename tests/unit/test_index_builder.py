# tests/unit/test_index_builder.py
"""
End-to-end test voor index_builder.py

Deze versie werkt direct met de feitelijke mappenstructuur:
src/webapp/assistants/project_assistant/tools/chatbot/

De test:
- zet automatisch het juiste pad in sys.path
- maakt tijdelijke testbestanden aan (txt + csv)
- voert build_index() volledig uit
- controleert of embeddings en metadata zijn opgeslagen
"""

import sys
import json
import numpy as np
from pathlib import Path

# ----------------------------------------------------------------------
# Padconfiguratie — zorgt dat Python de juiste chatbot-module ziet
# ----------------------------------------------------------------------
SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Importeer de juiste index_builder
from webapp.assistants.project_assistant.tools.chatbot.index_builder import build_index


# ----------------------------------------------------------------------
# Hulpfunctie — maak tijdelijke testdata aan
# ----------------------------------------------------------------------
def _seed_test_data(base_dir: Path) -> Path:
    """Maakt kleine tekst- en csv-bestanden aan om te indexeren."""
    data_dir = base_dir / "data_for_test"
    data_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "doc1.txt").write_text("Dit is een kleine test. " * 30, encoding="utf-8")
    (data_dir / "doc2.txt").write_text("Nog een document met tekst om te chunk-en. " * 25, encoding="utf-8")
    (data_dir / "tabel.csv").write_text("kolom1,kolom2\nA,1\nB,2\nC,3\n", encoding="utf-8")

    return data_dir


# ----------------------------------------------------------------------
# Test — volledige indexeer-flow
# ----------------------------------------------------------------------
def test_index_builder(tmp_path):
    """Test de volledige indexeerflow van index_builder."""
    data_dir = _seed_test_data(tmp_path)
    output_dir = tmp_path / "index_out"

    print(f"\n🚀 Start test-indexering vanuit {data_dir.resolve()}")
    build_index(data_dir, output_dir)

    npy_files = sorted(output_dir.glob("*.npy"))
    json_files = sorted(output_dir.glob("*.json"))

    # Basischecks
    assert npy_files, "❌ Geen .npy-bestanden aangemaakt!"
    assert json_files, "❌ Geen .json-bestanden aangemaakt!"

    # Metadata en embeddings valideren
    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = json.load(f)
    arr = np.load(npy_files[0])

    print(f"✅ {len(meta)} chunks, embeddings shape = {arr.shape}")

    assert len(meta) == arr.shape[0], "❌ Aantal metadata-items ≠ aantal embedding-rijen"
    assert arr.ndim == 2 and arr.shape[1] > 10, "❌ Embeddings hebben onverwachte vorm"
    assert all("source" in m and "chunk_id" in m for m in meta), "❌ Metadata mist verplichte sleutels"

    print("🎉 Test succesvol afgerond!\n")
