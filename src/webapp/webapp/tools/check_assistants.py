# webapp/assistants/check_assistants.py
import importlib.util, sys
from pathlib import Path

ASS_DIR = Path(__file__).parent
if str(ASS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(ASS_DIR.parent))

problems = []
print("Scanning assistants/ ...\n")

for py in sorted(ASS_DIR.glob("*.py")):
    if py.name.startswith("_") or py.name == "check_assistants.py":
        continue
    key = py.stem
    try:
        spec = importlib.util.spec_from_file_location(f"assistants.{key}", str(py))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"- {py.name}: import error: {e}")
        continue
    print(f"- {py.name}: IS_ASSISTANT={getattr(mod,'IS_ASSISTANT',None)}, DISPLAY_NAME={getattr(mod,'DISPLAY_NAME',None)}, has_render={callable(getattr(mod,'render',None))}")

# packages: directories with __init__.py
for d in sorted([p for p in ASS_DIR.iterdir() if p.is_dir()]):
    init_py = d / "__init__.py"
    if not init_py.exists():
        continue
    key = d.name
    try:
        spec = importlib.util.spec_from_file_location(f"assistants.{key}", str(init_py))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"- {d.name}/__init__.py: import error: {e}")
        continue
    print(f"- {d.name}/ (package): IS_ASSISTANT={getattr(mod,'IS_ASSISTANT',None)}, DISPLAY_NAME={getattr(mod,'DISPLAY_NAME',None)}, has_render={callable(getattr(mod,'render',None))}")
