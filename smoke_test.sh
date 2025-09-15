#!/usr/bin/env bash
set -euo pipefail

# Zorg dat src/ op de module-zoekweg staat
export PYTHONPATH="$(pwd)/src"

# Lijst van modules om te testen (moet overeenkomen met je registry)
MODULES=(
  "tools.doc_comparison"
  "tools.doc_generator"
  "tools.doc_extractor"
  "tools.doc_riskanalyzer"
  "tools.plan_creator"
)

echo "🔎 Smoke‐test starten…"

for m in "${MODULES[@]}"; do
  python3 - << EOF
import importlib, sys
try:
    mod = importlib.import_module("$m")
    if not hasattr(mod, "render"):
        print("❌ $m: wél import maar géén render()")
        sys.exit(1)
    print("✅ $m: OK (render() gevonden)")
except Exception as e:
    print(f"❌ {m}: kon niet importeren: {e}")
    sys.exit(1)
EOF
  if [ $? -ne 0 ]; then
    exit 1
  fi
done

echo "🎉 Alle imports en render()-checks geslaagd!"