#!/usr/bin/env bash
set -euo pipefail

# Zet src/ op de module-zoekweg voor Python
export PYTHONPATH="$(pwd)/src"

# Laad optioneel je .env
set -a
[ -f .env ] && source .env
set +a

# Start Streamlit vanuit de juiste locatie
streamlit run src/webapp/app.py "$@"
