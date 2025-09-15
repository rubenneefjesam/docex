#!/usr/bin/env bash
set -euo pipefail

echo "1️⃣  Controleren dat de modules er echt zijn…"
if [[ ! -f src/webapp/assistants/general_support/document_generator.py ]]; then
  echo "❌ document_generator.py ontbreekt!"
  exit 1
fi
if [[ ! -f src/webapp/assistants/general_support/document_comparison.py ]]; then
  echo "❌ document_comparison.py ontbreekt!"
  exit 1
fi
echo "✅ Beide bestanden gevonden."

echo
echo "2️⃣  __pycache__ opruimen…"
find src -type d -name "__pycache__" -exec rm -rf {} +
echo "✅ Cache is schoon."

echo
echo "3️⃣  PYTHONPATH instellen op src/…"
export PYTHONPATH="$(pwd)/src"
echo "   PYTHONPATH=$PYTHONPATH"

echo
echo "4️⃣  Streamlit starten…"
exec streamlit run src/webapp/app.py
