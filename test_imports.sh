#!/usr/bin/env bash
set -euo pipefail

ROOT=$(pwd)

echo "1) Controleren op __init__.py in packages…"
for DIR in \
  "$ROOT/src/webapp" \
  "$ROOT/src/webapp/assistants" \
  "$ROOT/src/webapp/assistants/general_support"; do
  if [ -f "$DIR/__init__.py" ]; then
    echo "✅ $DIR/__init__.py gevonden"
  else
    echo "❌ $DIR/__init__.py mist"
  fi
done

echo
echo "2) Controleren of pagina-modules importeren en render() hebben…"
MODULES=(
  "webapp.assistants.general_support.document_generator"
  "webapp.assistants.general_support.document_comparison"
)
for M in "${MODULES[@]}"; do
  echo -n "– $M: "
  python3 - <<EOF
import importlib, sys
try:
    mod = importlib.import_module("$M")
except Exception as e:
    print("import FOUT:", e)
    sys.exit(1)

r = getattr(mod, "render", None)
if not callable(r):
    print("geen callable render() gevonden")
    sys.exit(1)

print("✅ OK")
EOF
done

echo
echo "Alle checks voltooid."
