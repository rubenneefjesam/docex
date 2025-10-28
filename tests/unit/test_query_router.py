# tests/unit/test_query_router.py
"""
Unit tests voor QueryRouter (chatbot/query_router.py)

Test de volledige flow:
- intent parsing
- retrieval via dummy-index
- samenvatting via mocked LLM
"""
import sys
from pathlib import Path

# Voeg 'src' toe aan Python path zodat imports werken
ROOT = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(ROOT))

import pytest
from webapp.assistants.project_assistant.tools.chatbot import index_utils


class DummyEmbedder:
    """Mock embedder die een vaste vector teruggeeft."""
    def embed(self, texts):
        return [[0.1, 0.2, 0.3]]  # fake embedding


class DummyLLM:
    """Mock LLM die de prompt gewoon samenvat in korte tekst."""
    def __init__(self):
        self.called = False

    def chat(self, question, context):
        self.called = True
        return f"[LLM MOCK] Answer to: {question[:40]}"

    # compatibel met llm_utils.call_llm_system_prompt
    def completions(self, *args, **kwargs):
        self.called = True
        return "[LLM MOCK response]"


@pytest.fixture
def router(tmp_path, monkeypatch):
    """Maak QueryRouter met dummy index in tijdelijke map."""
    # monkeypatch index_utils paths
    from chatbot import index_utils

    # maak tijdelijk index
    index_utils.INDEX_DIR = tmp_path
    cid, pid = "C001", "P1001"
    rows = [{"text": "Zonnepanelen worden geïnstalleerd op dak.", "_score": 0.99}]
    embeddings = [[0.1, 0.2, 0.3]]
    index_utils.save_index(cid, pid, rows, embeddings)

    # patch llm_utils.call_llm_system_prompt om geen API te gebruiken
    monkeypatch.setattr(
        "chatbot.llm_utils.call_llm_system_prompt",
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
