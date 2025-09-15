#!/usr/bin/env bash
set -euo pipefail

# 1. Zet path naar je src/webapp directory
WEBAPP_DIR="src/webapp"

echo "🔍 Controleren op directories en toevoegen __init__.py..."

# Vind alle directories onder WEBAPP_DIR en maak __init__.py aan als die nog niet bestaat
find "$WEBAPP_DIR" -type d | while read -r dir; do
  init_file="$dir/__init__.py"
  if [ ! -f "$init_file" ]; then
    echo "  ➕ Aanmaken $init_file"
    touch "$init_file"
  fi
done

echo "✅ __init__.py bestanden bijgewerkt."

# 2. Patch safe_import in app.py
APP_FILE="$WEBAPP_DIR/app.py"
TMP_FILE="$(mktemp)"

echo "🔧 Bewerken van safe_import in $APP_FILE..."

# We vervangen de huidige safe_import definitie door een versie die eerst de full module-path probeert.
# Let op: zorg dat je een backup hebt of commit voordat je dit script draait!

awk '
  BEGIN {in_safe=0}
  # begin van safe_import functie
  /^def safe_import\(module_path_or_basename\):/ {
    print
    in_safe=1
    next
  }
  # einde van functie
  in_safe && /^    return import_page_module/ {
    # Print nieuwe implementatie
    print "    # Eerst proberen import van volledige module-path"
    print "    try:"
    print "        return importlib.import_module(module_path_or_basename)"
    print "    except ModuleNotFoundError:"
    print "        pass"
    print "    except Exception as e:"
    print "        return e"
    print ""
    print "    # Fallback: importeren op basis van basename"
    print "    base = module_path_or_basename.split('.')[-1]"
    print "    return import_page_module(base)"
    in_safe=0
    next
  }
  # print alle andere regels gewoon door
  { print }
' "$APP_FILE" > "$TMP_FILE"

mv "$TMP_FILE" "$APP_FILE"
echo "✅ safe_import is gepatcht."

echo "🎉 Klaar! Probeer nu opnieuw te starten." 
