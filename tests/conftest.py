# conftest.py (plaats in project root: /workspaces/docex)
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent  # project root
SRC = ROOT / "src"
src_str = str(SRC)
if src_str not in sys.path:
    sys.path.insert(0, src_str)

@pytest.fixture(scope="session")
def project_root():
    return ROOT
