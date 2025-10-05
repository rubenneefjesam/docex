#!/usr/bin/env bash
set -e

# run from repo root
ROOT="$(pwd)"
SRC="src/webapp/assistants/project_assistant/tools/chatbot"
IDX="$SRC/indexer"
BACKUP_DIR="/tmp/chatbot_indexer_backup_$(date +%s)"

echo "1) Backup .py files from indexer to $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp "$IDX"/*.py "$BACKUP_DIR"/ 2>/dev/null || true

echo "2) Show current files in indexer:"
ls -la "$IDX" || true

echo "3) Preview imports to be patched (lines that match):"
grep -n -E "from (io_utils_extended|chunker|embedder_modular|pdf_io|index_utils) import" "$IDX"/*.py || true

echo "4) Applying sed patches to make imports relative..."
sed -i 's/from io_utils_extended import /from .io_utils_extended import /g' "$IDX"/*.py || true
sed -i 's/from chunker import /from .chunker import /g' "$IDX"/*.py || true
sed -i 's/from embedder_modular import /from .embedder_modular import /g' "$IDX"/*.py || true
sed -i 's/from pdf_io import /from .pdf_io import /g' "$IDX"/*.py || true
sed -i 's/from index_utils import /from ..index_utils import /g' "$IDX"/index_csvs_modular.py || true

echo "5) Show top of index_csvs_modular.py for verification:"
sed -n '1,40p' "$IDX"/index_csvs_modular.py || true

echo "6) Set PYTHONPATH and try running the indexer module (this may print progress or errors)."
export PYTHONPATH="$ROOT/src"
python -m webapp.assistants.project_assistant.tools.chatbot.indexer.index_csvs_modular || {
  echo "=== INDEXER RUN FAILED ==="
  echo "If it failed, the backup of indexer .py files is at: $BACKUP_DIR"
  exit 2
}

echo "=== DONE: Indexer ran without crashing (or exited clean)."
echo "Backups of original files are in: $BACKUP_DIR"
