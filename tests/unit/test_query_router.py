"""
Unit tests voor QueryRouter (volledige reasoning-pipeline met mocks)
Compatibel met projectstructuur: src/webapp/assistants/project_assistant/tools/chatbot
"""

import sys
from pathlib import Path
import pytest

# Voeg 'src' toe aan sys.path zodat imports werken
ROOT = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(ROOT))

from webapp.assistants.project_assistant.tools.chatbot.query_router import QueryRouter
from webapp.assistants.project_assistant.tools.chatbot import index_utils


class DummyEmbedder:
    def embed(self, texts):
        return [[0.1, 0.2, 0.3]]


@pytest.fixture
def router(tmp_path, monkeypatch):
    """Maak QueryRouter met dummy index in tijdelijke map."""
    # overschrijf index directory
    index_utils.INDEX_DIR = tmp_path
    cid, pid = "C001", "P1001"
    rows = [{"text": "Zonnepanelen worden geïnstalleerd op dak.", "_score": 0.99}]
    embeddings = [[0.1, 0.2, 0.3]]
    index_utils.save_index(cid, pid, rows, embeddings)

    # monkeypatch LLM-call
    monkeypatch.setattr(
        "webapp.assistants.project_assistant.tools.chatbot.llm_utils.call_llm_system_prompt",
        lambda prompt, system, groq_client=None: "[MOCK LLM] " + prompt.splitlines()[0],
    )

    return QueryRouter(DummyEmbedder(), llm_client=None)


def test_intent_parsing(router):
    q = "Wat staat er in de technische omschrijving van klant C001 over zonnepanelen?"
    intent = router.parse_intent(q)
    assert intent["intent"] == "document"
    assert intent["client_id"] == "C001"


def test_retrieval_and_summary(router):
    q = "Wat staat er in de technische omschrijving van klant C001 over zonnepanelen?"
    answer = router.route_query(q)
    assert "[MOCK LLM]" in answer
    assert "Wat staat er" in answer
