"""
Integratietest: QueryRouter + index_utils + io_utils.
Simuleert volledige flow: tekst lezen → indexeren → vraag stellen → antwoord ontvangen.
"""

import sys
from pathlib import Path
import pytest

# Voeg 'src' toe aan path zodat imports werken
ROOT = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(ROOT))

from webapp.assistants.project_assistant.tools.chatbot.query_router import QueryRouter
from webapp.assistants.project_assistant.tools.chatbot import io_utils, index_utils


class DummyEmbedder:
    def embed(self, texts):
        # Simuleer eenvoudige vector
        return [[float(len(t)) / 100.0, 0.2, 0.3] for t in texts]


@pytest.fixture
def setup_router(tmp_path, monkeypatch):
    """Maak QueryRouter met dummy index en mock LLM."""
    index_utils.INDEX_DIR = tmp_path

    # 1️⃣ Documentinhoud simuleren
    text = "De woning van klant C001 heeft zonnepanelen en een dakkapel volgens de technische omschrijving."
    chunks = [{"text": text, "doc_type": "technische omschrijving", "source_path": "test.pdf"}]
    emb = [[0.1, 0.2, 0.3]]
    index_utils.save_index("C001", "P1001", chunks, emb)

    # 2️⃣ Mock LLM
    monkeypatch.setattr(
        "webapp.assistants.project_assistant.tools.chatbot.llm_utils.call_llm_system_prompt",
        lambda prompt, system, groq_client=None: "[MOCK ANSWER] " + prompt.splitlines()[0],
    )

    return QueryRouter(DummyEmbedder(), llm_client=None)


def test_end_to_end_query(setup_router):
    """Test volledige flow: intent + retrieval + samenvatting."""
    router = setup_router
    question = "Wat staat er in de technische omschrijving van klant C001?"
    answer = router.route_query(question)
    assert "[MOCK ANSWER]" in answer
    assert "Wat staat er" in answer


def test_io_utils_chunking_and_metadata(tmp_path):
    """Controleer chunking en metadata van io_utils."""
    test_txt = tmp_path / "Technische_omschrijving_C001_P1001.txt"
    test_txt.write_text("Dit is een korte tekst over zonnepanelen bij klant C001.")

    # lees & chunk
    text = io_utils.read_text_from_file(test_txt)
    chunks = io_utils.chunk_to_records(text, test_txt)

    assert len(chunks) > 0
    first = chunks[0]
    assert "text" in first
    assert "doc_type" in first
    assert "source_path" in first
