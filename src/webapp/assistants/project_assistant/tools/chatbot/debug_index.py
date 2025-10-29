from pathlib import Path
from embed_utils import INDEX_DIR, load_index

print(f"📦 INDEX_DIR = {INDEX_DIR.resolve()}")

client_id = "C001"
project_id = "P1001"

rows, _ = load_index(client_id, project_id)
print(f"🔍 {client_id}/{project_id} → {len(rows)} chunks gevonden")

# Toon even de eerste paar records
for i, r in enumerate(rows[:3]):
    print(f"{i+1}. {r.get('source_path','?')} | {r.get('text','')[:80]!r}")