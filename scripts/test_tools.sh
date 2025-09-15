#!/usr/bin/env bash
set -euo pipefail

echo "Huidige PYTHONPATH:"
echo "  ${PYTHONPATH:-<niet-gezet>}"
echo

echo "1) Proberen te importeren vanuit de huidige omgeving…"
python3 - <<'EOF'
import importlib, sys
try:
    import tools.doc_generator.doc_generator
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
    import tools.doc_generator.doc_generator
    print("✅ import OK met project-root in PYTHONPATH")
except Exception as e:
    print("❌ import nog steeds failed:", e)
    sys.exit(1)
EOF

echo
echo ">>> Als stap 2 OK is, pas dan je run.sh aan:"
echo "export PYTHONPATH=\"\$(pwd):\$(pwd)/src\""
