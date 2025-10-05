#!/usr/bin/env bash
set -euo pipefail

BASE="webapp/assistants"
[[ -d "$BASE" ]] || { echo "❌ Map $BASE niet gevonden"; exit 1; }

created=0; patched=0

# Loop over alle assistant-packages: directories met __init__.py én IS_ASSISTANT=True
while IFS= read -r -d '' pkg; do
  init="$pkg/__init__.py"
  [[ -f "$init" ]] || continue
  if ! grep -Eq 'IS_ASSISTANT[[:space:]]*=[[:space:]]*True' "$init"; then
    continue
  fi

  name="$(basename "$pkg")"
  overview="$pkg/overview.py"

  # 1) overview.py aanmaken indien ontbreekt
  if [[ ! -f "$overview" ]]; then
    cat > "$overview" <<'PY'
import streamlit as st
try:
    from . import DISPLAY_NAME as _DISPLAY_NAME
except Exception:
    _DISPLAY_NAME = None

def render():
    title = _DISPLAY_NAME or __name__.split('.')[-2].replace('_',' ').title()
    st.subheader(f"Welkom bij {title}")
    st.write("Dit is de startpagina voor deze assistent. Kies links een tool om te beginnen.")
PY
    echo "➕ aangemaakt: $overview"
    ((created++))
  else
    echo "✔︎ bestaat al: $overview"
  fi

  # 2) veilige import naar overview in __init__.py zetten (indien nog niet aanwezig)
  if ! grep -Eq 'from[[:space:]]+\.[[:space:]]+overview[[:space:]]+import[[:space:]]+render[[:space:]]+as[[:space:]]+_render_overview' "$init"; then
    cat >> "$init" <<'PY'

# --- auto-added by make_assistant_overviews.sh ---
try:
    from .overview import render as _render_overview
except Exception:
    _render_overview = None
PY
    echo "✳︎ import overview toegevoegd in $init"
    ((patched++))
  fi

  # 3) default render(tool) toevoegen als die nog niet bestaat
  if ! grep -Eq '^def[[:space:]]+render\(' "$init"; then
    cat >> "$init" <<'PY'

# --- auto-added render() by make_assistant_overviews.sh ---
import streamlit as st
def render(tool=None):
    title = globals().get("DISPLAY_NAME") or __name__.split('.')[-2].replace('_',' ').title()
    st.title(title)
    if not tool or tool == "— Kies tool —":
        if callable(_render_overview):
            _render_overview()
        else:
            st.info("Selecteer een tool in de sidebar.")
        return
    st.info(f"Tool '{tool}' is nog niet gekoppeld aan een pagina.")
PY
    echo "✳︎ default render() toegevoegd in $init"
    ((patched++))
  fi

done < <(find "$BASE" -maxdepth 1 -mindepth 1 -type d -print0)

echo "✅ Klaar. Overviews aangemaakt: $created, bestanden gepatcht: $patched"
