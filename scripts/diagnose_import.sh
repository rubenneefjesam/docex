#!/usr/bin/env bash
set -euo pipefail

echo "— Directory tree onder src/webapp —"
find src/webapp -type f | sed 's/^/   /'

echo
echo "— Controleren op __init__.py —"
for d in src/webapp src/webapp/assistants src/webapp/assistants/general_support; do
  if [ -f "$d/__init__.py" ]; then
    echo "  [OK] $d/__init__.py bestaat"
  else
    echo "  [MISSING] $d/__init__.py ontbreekt"
  fi
done

echo
echo "— Test import vanuit een tijdelijke Python-sessie —"
python3 - << 'PYCODE'
import sys, pathlib, traceback
# Simuleer dezelfde sys.path als streamlit/app.py doet
root = pathlib.Path("src/webapp").resolve().parents[1]
sys.path.insert(0, str(root))
print("sys.path[0]:", sys.path[0])
try:
    import webapp.assistants.general_support.document_generator
    print("✅ Import lukte!")
except Exception as e:
    print("❌ Import faalde:", e)
    traceback.print_exc()
PYCODE
