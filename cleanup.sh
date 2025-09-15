#!/usr/bin/env bash
set -euo pipefail

echo "1) Verwijder oude assistant-home folder…"
if [ -d "webapp/assistants/home" ]; then
  rm -rf webapp/assistants/home
  echo "   -> webapp/assistants/home is weggehaald."
else
  echo "   -> Geen oude webapp/assistants/home gevonden, overslaan."
fi

echo ""
echo "2) Verwijder alle app.py-*.bak backups…"
# zoekt bestanden als app.py.bak, app.py.1.bak, app.py.backup etc.
find . -type f -regex '.*app\.py.*\.bak$' -print -delete || true

echo "   -> Backup-bestanden verwijderd."
echo ""
echo "3) Toon (nieuwe) mapstructuur onder webapp/…"
if command -v tree &> /dev/null; then
  tree webapp -I '__pycache__|*.pyc'
else
  # fallback als tree niet beschikbaar is
  find webapp -type d -print -o -type f -print \
    | sed 's|/|  |g;s|  \(.*\)|-- \1|' 
fi