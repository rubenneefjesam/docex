cat > setup_packages.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

WEBAPP_DIR="src/webapp"

echo "🔍 Controleren op directories en toevoegen __init__.py..."
find "$WEBAPP_DIR" -type d | while read -r dir; do
  init_file="$dir/__init__.py"
  if [ ! -f "$init_file" ]; then
    echo "  ➕ Aanmaken $init_file"
    touch "$init_file"
  fi
done
echo "✅ __init__.py bestanden bijgewerkt."

APP_FILE="$WEBAPP_DIR/app.py"
TMP_FILE="$(mktemp)"

echo "🔧 Bewerken van safe_import in $APP_FILE..."
awk '
  BEGIN {in_safe=0}
  /^def safe_import\\(module_path_or_basename\\):/ {
    print; in_safe=1; next
  }
  in_safe && /^    return import_page_module/ {
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
    in_safe=0; next
  }
  { print }
' "$APP_FILE" > "$TMP_FILE"
mv "$TMP_FILE" "$APP_FILE"
echo "✅ safe_import is gepatcht."

echo "🎉 Klaar! Probeer nu opnieuw te starten."
EOF
