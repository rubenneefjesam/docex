import importlib
import pytest
from webapp.registry import ASSISTANTS

BASE = "webapp.assistants"

@pytest.mark.parametrize("assistant", list(ASSISTANTS.keys()))
def test_assistant_info_import(assistant):
    \"\"\"Check of voor iedere assistant de info-module aanwezig en importeerbaar is.\"\"\"
    module_name = f"{BASE}.{assistant}.info"
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        pytest.fail(f"Module {module_name} niet gevonden")
    except Exception as e:
        pytest.fail(f"Fout bij importeren van {module_name}: {e}")
