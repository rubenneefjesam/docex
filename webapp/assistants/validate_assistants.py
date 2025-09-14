# webapp/assistants/validate_assistants.py
import importlib.util
import sys
from pathlib import Path

ASSISTANTS_DIR = Path(__file__).parent
problems = []

for py in sorted(ASSISTANTS_DIR.glob("*.py")):
    if py.name.startswith("_") or py.name == "validate_assistants.py":
        continue
    key = py.stem
    try:
        spec = importlib.util.spec_from_file_location(f"assistants.{key}", str(py))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"assistants.{key}"] = mod
        spec.loader.exec_module(mod)
    except Exception as e:
        problems.append((py.name, f"import error: {e}"))
        continue

    missing = []
    if not hasattr(mod, "DISPLAY_NAME"):
        missing.append("DISPLAY_NAME")
    if not hasattr(mod, "TOOLS"):
        missing.append("TOOLS")
    if not callable(getattr(mod, "render", None)):
        missing.append("render(tool)")

    if missing:
        problems.append((py.name, "missing: " + ", ".join(missing)))

if not problems:
    print("✅ Alle assistant-modules lijken ok (DISPLAY_NAME, TOOLS, render).")
else:
    print("⚠️ Problemen gevonden:")
    for p in problems:
        print(f" - {p[0]}: {p[1]}")
