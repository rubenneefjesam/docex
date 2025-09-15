#!/usr/bin/env bash
set -euo pipefail

# Ga naar de general_support directory
cd src/webapp/assistants/general_support

echo "🗂 Inhoud van general_support voor verhuizing:"
ls -1

# Maak de tools-map aan als die nog niet bestaat
mkdir -p tools

# Verhuis álle directory­submappen behalve tools/ en __pycache__/
for d in */; do
  if [[ "$d" != "tools/" && "$d" != "__pycache__/" ]]; then
    echo "🔀 Verplaats $d → tools/"
    mv "$d" tools/
  fi
done

echo
echo "✅ Na verhuizing:"
ls -R