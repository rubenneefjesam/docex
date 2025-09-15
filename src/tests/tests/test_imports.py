import importlib
import pytest
from webapp.registry import ASSISTANTS

BASE = "webapp.assistants"
PAGES = ["home", "info", "contact"]
ASSISTANT_MODULES = list(ASSISTANTS.keys())

def try_import(module_name):
    try:
        importlib.import_module(f"{BASE}.{module_name}")
    except Exception as e:
        pytest.fail(f"Kon module {BASE}.{module_name} niet importeren: {e}")

@pytest.mark.parametrize("page", PAGES)
def test_global_pages(page):
    """Check of globale pagina-modules importeren zonder errors."""
    try_import(page)

@pytest.mark.parametrize("assistant", ASSISTANT_MODULES)
def test_assistant_info_pages(assistant):
    """Check of voor elke assistant de info-module importeert."""
    try_import(assistant)
