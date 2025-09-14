# tests/test_registry_content.py
import sys
from pathlib import Path
import importlib
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webapp import registry

def test_expected_assistants_present():
    expected = {
        "general_support",
        "tender_assistant",
        "risk_assistant",
        "calculator_assistant",
        "legal_assistant",
        "project_assistant",
        "sustainability_advisor",
    }
    found = set(registry.ASSISTANTS.keys())
    missing = expected - found
    assert not missing, f"Missing expected assistants in registry: {missing}"
