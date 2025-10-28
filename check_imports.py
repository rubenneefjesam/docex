"""
check_imports.py
----------------
Helpt bij het debuggen van ModuleNotFoundError voor 'chatbot.index_builder'.
"""

import os
import sys
from pathlib import Path
import importlib

print("=== PYTHON IMPORT CHECK ===\n")

# Toon huidige werkmap
cwd = Path.cwd()
print(f"📁 Current working directory: {cwd}")

# Zoek naar chatbot-map
root = cwd
chatbot_dir = root / "chatbot"
print(f"🔍 Verwachte chatbot-map: {chatbot_dir}")
print(f"   Bestaat? {'✅' if chatbot_dir.exists() else '❌'}")

# Kijk of __init__.py er is
init_file = chatbot_dir / "__init__.py"
print(f"📦 __init__.py aanwezig? {'✅' if init_file.exists() else '❌'}")

# Voeg root toe aan sys.path
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
print(f"\n🧩 Eerste 3 paden in sys.path:")
for p in sys.path[:3]:
    print("   ", p)

# Probeer de import
print("\n🚀 Probeer import van chatbot.index_builder...")
try:
    mod = importlib.import_module("chatbot.index_builder")
    print("✅ Import gelukt!")
    print("   Module-locatie:", Path(mod.__file__).resolve())
except Exception as e:
    print("❌ Import mislukt:", repr(e))

# Extra: toon aanwezige bestanden in chatbot/
if chatbot_dir.exists():
    print("\n📂 Inhoud van chatbot/:")
    for p in chatbot_dir.iterdir():
        print("   ", p.name)

print("\n=== EINDE CHECK ===")
