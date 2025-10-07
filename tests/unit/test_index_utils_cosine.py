import numpy as np
from webapp.assistants.project_assistant.tools.chatbot.index_utils import _cosine_sim

def test_cosine_sim_basic():
    a = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.float32)
    b = np.array([1.0, 0.0], dtype=np.float32)
    sims = _cosine_sim(a, b)
    assert sims.shape == (2,)
    assert sims[0] > 0.9  # first is ~1.0
    assert sims[1] == sims[1]  # not nan

def test_cosine_sim_empty_or_none():
    assert _cosine_sim(None, None).size == 0
    assert _cosine_sim([], [1,2,3]).size == 0
