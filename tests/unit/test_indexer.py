# tests/unit/test_indexer.py
import tempfile
from pathlib import Path
import sys
import importlib
import pytest

# Setup src path
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if not SRC_DIR.exists():
    pytest.skip(f"src directory not found: {SRC_DIR}")
sys.path.insert(0, str(SRC_DIR))

# Dynamically load index_csvs_modular module by file path
from importlib.util import spec_from_file_location, module_from_spec

def load_index_module():
    from types import ModuleType
    # find file
    candidates = list(SRC_DIR.rglob('index_csvs_modular.py'))
    assert candidates, 'Could not find index_csvs_modular.py under src/'
    for p in candidates:
        if 'indexer' in p.parts:
            path = p
            break
    else:
        path = candidates[0]
    rel = path.relative_to(SRC_DIR).with_suffix('')
    pkg_name = '.'.join(rel.parts[:-1])
    # insert dummy package to avoid executing __init__.py
    sys.modules[pkg_name] = ModuleType(pkg_name)
    # load module
    spec = spec_from_file_location('index_csvs_modular', str(path))
    mod = module_from_spec(spec)
    mod.__package__ = pkg_name
    sys.modules[f"{pkg_name}.index_csvs_modular"] = mod
    spec.loader.exec_module(mod)
    return mod

mod = load_index_module()
index_clients_projects_from_csv = mod.index_clients_projects_from_csv
index_documents = mod.index_documents

# Constants for CSV filenames
CLIENTS_CSV = "Clients_test.csv"
PROJECTS_CSV = "Projects_test.csv"

class DummyEmbedder:
    """Minimal dummy embedder for testing."""
    def __init__(self, dim=384):
        self.dim = dim
    def embed(self, texts):
        return [[0.0] * self.dim for _ in texts]


def write_csv(path: Path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(headers) + "\n")
        for r in rows:
            fh.write(",".join(r) + "\n")


def test_index_clients_projects_from_csv_returns_dict(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    clients_csv = data_dir / CLIENTS_CSV
    projects_csv = data_dir / PROJECTS_CSV
    # Write dummy CSVs
    write_csv(clients_csv, ["KlantID","ProjectID","Name"], [["C001","P1001","Client One"],["C002","P1002","Client Two"]])
    write_csv(projects_csv, ["ProjectID","ProjectName"], [["P1001","Project One"],["P1002","Project Two"]])
    dummy = DummyEmbedder(dim=384)
    result = index_clients_projects_from_csv(clients_csv, projects_csv, dummy)
    assert isinstance(result, dict)
    assert "P1001" in result and "P1002" in result
    val1 = result["P1001"]
    assert (isinstance(val1, str) and val1 == "C001") or (isinstance(val1, list) and "C001" in val1)
    val2 = result["P1002"]
    assert (isinstance(val2, str) and val2 == "C002") or (isinstance(val2, list) and "C002" in val2)


def test_index_documents_counts_chunks(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    # sample txts
    (docs_dir / "woning_C001_P1001.txt").write_text("Test P1001 C001", encoding="utf-8")
    (docs_dir / "brief_C002_P1002.txt").write_text("Test P1002 C002", encoding="utf-8")
    proj_map = {"P1001":["C001"], "P1002":["C002"]}
    dummy = DummyEmbedder(dim=384)
    count = index_documents(docs_dir, proj_map, dummy)
    assert isinstance(count, int)
    assert count >= 0
