mkdir -p scripts
cat > scripts/packagify_modules.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

# Vind de directory van dit script en bepaal assistants-map absoluut
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$SCRIPT_DIR/../webapp/assistants"

if [[ ! -d "$BASE" ]]; then
  echo "❌ Map $BASE niet gevonden. Check je repo-structuur."
  exit 1
fi

usage() {
  echo "Gebruik:"
  echo "  $0 [--assistant] naam [naam2 ...]"
  echo "     --assistant  maak een echte assistant (IS_ASSISTANT=True + overview)"
  echo "     zonder --assistant   maak een gewone pagina-package"
  exit 1
}

is_assistant=false
if [[ "${1:-}" == "--assistant" ]]; then
  is_assistant=true
  shift
fi

[[ $# -ge 1 ]] || usage

# Hulpfunctie: underscore -> Title Case
titlecase() {
  python - "$1" <<'PY'
import sys
s=sys.argv[1].replace('_',' ')
print(' '.join(w.capitalize() for w in s.split()))
PY
}

for name in "$@"; do
  dir="$BASE/$name"
  file="$BASE/$name.py"
  init="$dir/__init__.py"
  display="$(titlecase "$name")"

  mkdir -p "$dir"

  # Verplaats vlakke module naar package als die bestaat
  if [[ -f "$file" ]]; then
    mv "$file" "$init"
    echo "➜ Verplaatst $file → $init"
  fi

  # Maak skeleton __init__.py aan als dat nog niet bestaat
  if [[ ! -f "$init" ]]; then
    if $is_assistant; then
      cat > "$init" <<PY
DISPLAY_NAME = "$display"
IS_ASSISTANT = True
TOOLS = ["— Kies tool —"]

import streamlit as st
try:
    from .overview import render as _render_overview
except Exception:
    _render_overview = None

def render(tool=None):
    st.title(DISPLAY_NAME)
    if not tool or tool == "— Kies tool —":
        if callable(_render_overview):
            _render_overview()
        else:
            st.info("Selecteer links een tool om te starten.")
        return
    st.info(f"Tool '{tool}' is nog niet gekoppeld.")
PY
      # overzichtspagina
      cat > "$dir/overview.py" <<PY
import streamlit as st
try:
    from . import DISPLAY_NAME as _DISPLAY_NAME
except Exception:
    _DISPLAY_NAME = None

def render():
    title = _DISPLAY_NAME or "Assistent"
    st.subheader(f"Welkom bij {title}")
    st.write("Dit is de startpagina voor deze assistent. Kies links een tool om te beginnen.")
PY
      echo "➕ Assistant-package aangemaakt: $dir/"
    else
      # gewone pagina-package
      cat > "$init" <<PY
DISPLAY_NAME = "$display"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —"]

import streamlit as st
def render(tool=None):
    st.title(DISPLAY_NAME)
    st.write("Pagina-inhoud volgt.")
PY
      echo "➕ Pagina-package aangemaakt: $dir/"
    fi
  else
    echo "✔︎ Bestaat al: $dir/"
  fi
done

echo "✅ Klaar."
BASH

chmod +x scripts/packagify_modules.sh
