# tests/unit/test_index_utils_metadata.py
"""
Test metadata-uitbreiding in index_utils.
"""

import numpy as np
from webapp.assistants.project_assistant.tools.chatbot import index_utils


def test_save_and_load_index_with_metadata(tmp_path):
    index_utils.INDEX_DIR = tmp_path
    cid, pid = "C001", "P1001"
    chunks = [
        {
            "text": "Dakkapel aanwezig bij deze woning.",
            "doc_type": "technische omschrijving",
            "source_path": "data/overige_documenten/1_Technische_omschrijving_C001.pdf",
        },
        {
            "text": "Zonnepanelen worden optioneel geleverd.",
            "doc_type": "technische omschrijving",
            "source_path": "data/overige_documenten/1_Technische_omschrijving_C001.pdf",
        },
    ]
    embeddings = np.random.rand(len(chunks), 3).tolist()
    index_utils.save_index(cid, pid, chunks, embeddings)

    rows, emb = index_utils.load_index(cid, pid)
    assert len(rows) == 2
    assert "doc_type" in rows[0]
    assert "source_path" in rows[0]
    assert emb.shape[0] == 2

    # retrieval werkt
    q_emb = np.random.rand(3)
    results = index_utils.retrieve(cid, pid, q_emb, top_k=1)
    assert isinstance(results, list)
    assert "_score" in results[0]
