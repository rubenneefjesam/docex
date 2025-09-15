#!/usr/bin/env bash
set -euo pipefail

echo "Huidige PYTHONPATH:"
echo "  $PYTHONPATH"
echo

echo "1) Proberen te importeren vanuit de huidige omgeving…"
python3 - <<'EOF'
import importlib, sys
try:
    mod = importlib.import_module("tools.doc_generator.doc_generator")
    print("✅ tools.doc_generator.doc_generator import OK")
except Exception as e:
    print("❌ import failed:", e)
    sys.exit(1)
EOF

echo
echo "2) Proberen met project-root in PYTHONPATH…"
export PYTHONPATH="$(pwd):$(pwd)/src"
echo "  nieuwe PYTHONPATH: $PYTHONPATH"
python3 - <<'EOF'
import importlib, sys
try:
    mod = importlib.import_module("tools.doc_generator.doc_generator")
    print("✅ import OK met project-root in PYTHONPATH")
except Exception as e:
    print("❌ import nog steeds failed:", e)
    sys.exit(1)
EOF

echo
echo "Klaar – als tweede stap kun je je run.sh aanpassen om ook de project-root in PYTHONPATH te zetten:"
echo "  export PYTHONPATH=\"\$(pwd):\$(pwd)/src\""
