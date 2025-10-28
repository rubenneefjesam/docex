# tests/unit/test_index_builder.py
"""
Final standalone test for chatbot/index_builder.py

Werkt direct met de werkelijke mappenstructuur:
src/webapp/assistants/project_assistant/tools/chatbot/

De test:
- zet automatisch het juiste pad in sys.path
- maakt zelf dummy testbestanden aan (txt + csv)
- voert build_index() end-to-end uit
- controleert of embeddings en metadata correct zijn opgeslagen
"""

from pathlib import Path
import sys
import json
import numpy as np

# -----------------------------------------------------------------------------
# Zorg dat Python het juiste pad kent (root = /workspaces/docex/src)
# -----------------------------------------------------------------------------
SRC_ROOT = Path(__file__).resolve().parents[3] / "src"
if not SRC_ROOT.exists():
    raise FileNotFoundError(f"Kan src-map niet vinden op verwacht pad: {SRC_ROOT}")
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Import vanuit de echte pakketstructuur
from webapp.assistants.project_assistant.tools.chatbot.index_builder import build_index


# -----------------------------------------------------------------------------
# Hulpfunctie: maak tijdelijke testdata aan
# -----------------------------------------------------------------------------
def _seed_test_data(base_dir: Path) -> Path:
    """Maak een tijdelijke data-map met enkele testbestanden."""
    data_dir = base_dir / "data_for_test"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Kleine dummy documenten om indexering te testen
    (data_dir / "doc1.txt").write_text("Dit is een kleine test. " * 30, encoding="utf-8")
    (data_dir / "doc2.txt").write_text("Nog een document met voldoende tekst om te chunk-en. " * 25, encoding="utf-8")
    (data_dir / "tabel.csv").write_text("kolom1,kolom2\nA,1\nB,2\nC,3\n", encoding="utf-8")

    return data_dir


# -----------------------------------------------------------------------------
# Hoofdfunctie: end-to-end test voor index_builder
# -----------------------------------------------------------------------------
def test_index_builder(tmp_path):
    """Voer volledige indexeer-test uit met gegenereerde testdata."""
    data_dir = _seed_test_data(tmp_path)
    output_dir = tmp_path / "index_out"

    print(f"\n🚀 Start test-indexering vanuit {data_dir.resolve()}")
    build_index(data_dir, output_dir)

    npy_files = sorted(output_dir.glob("*.npy"))
    json_files = sorted(output_dir.glob("*.json"))

    # -------------------------------------------------
    # Controleer of outputbestanden bestaan
    # -------------------------------------------------
    assert npy_files, "❌ Geen .npy-bestanden aangemaakt!"
    assert json_files, "❌ Geen .json-bestanden aangemaakt!"

    # -------------------------------------------------
    # Controleer inhoud van bestanden
    # -------------------------------------------------
    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = json.load(f)
    arr = np.load(npy_files[0])

    print(f"✅ {len(meta)} chunks, embeddings shape = {arr.shape}")

    # Basisvalidaties
    assert len(meta) == arr.shape[0], "❌ Aantal metadata-items ≠ aantal embedding-rijen"
    assert arr.ndim == 2 and arr.shape[1] > 10, "❌ Embeddings hebben onverwachte vorm"
    assert all("source" in m and "chunk_id" in m for m in meta), "❌ Metadata mist verplichte sleutels"

    print("🎉 Test succesvol afgerond!\n")
