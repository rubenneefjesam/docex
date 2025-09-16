#!/usr/bin/env bash
set -euo pipefail

# Zet PYTHONPATH zodat Python je src/ map vindt
export PYTHONPATH="$(pwd)/src"

MODULE="webapp.assistants.general_support.tools.speech_2_document"

echo "=== Test 1: Direct import & callable('app') ==="
if python3 - <<PYCODE
import importlib, sys
try:
    mod = importlib.import_module("$MODULE")
    app_fn = getattr(mod, "app", None)
    if not callable(app_fn):
        sys.exit(1)
except Exception:
    sys.exit(1)
# succes
sys.exit(0)
PYCODE
then
    echo "PASS: module '$MODULE' geïmporteerd en 'app' is callable."
else
    echo "FAIL: module '$MODULE' niet importeerbaar of 'app' mist."
    exit 1
fi

echo

echo "=== Test 2: registry.resolve_tool_module ==="
if python3 - <<'PYCODE'
import sys
from webapp.registry import resolve_tool_module

try:
    entry = resolve_tool_module("general_support", "speech_2_document")
except Exception:
    sys.exit(1)
# succes als we hier zijn
sys.exit(0)
PYCODE
then
    echo "PASS: registry.resolve_tool_module laadt het correct."
else
    echo "FAIL: registry kon module speech_2_document niet laden."
    exit 1
fi

echo
echo "🎉 Alle tests geslaagd!"
