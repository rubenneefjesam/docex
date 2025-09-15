#!/usr/bin/env python3
from pathlib import Path
import sys, pkgutil, importlib, os

# zorg dat project root op sys.path staat (script bevindt zich in tools/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print("Project root:", ROOT)
tools_dir = ROOT / "tools"
mods = [m.name for m in pkgutil.iter_modules([str(tools_dir)])]
print("gevonden tool-modules:", mods)

errors = []
for m in mods:
    p = tools_dir / m
    if not p.is_dir():
        continue
    for fname in sorted(os.listdir(p)):
        if fname.endswith('.py') and fname != '__init__.py':
            modname = f"tools.{m}.{fname[:-3]}"
            try:
                importlib.import_module(modname)
            except Exception as e:
                errors.append((modname, type(e).__name__, str(e).splitlines()[0]))

if errors:
    print("\nIMPORT ERRORS (eerste 50):")
    for mod, etype, msg in errors[:50]:
        print(f"- {mod} -> {etype}: {msg}")
    print(f"\nTotaal errors: {len(errors)}")
    sys.exit(1)
else:
    print("\nSmoke-imports OK — geen import exceptions gedetecteerd")
    sys.exit(0)
