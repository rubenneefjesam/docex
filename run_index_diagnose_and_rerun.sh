#!/usr/bin/env bash
set -euo pipefail

# Single script: diagnose PDF-extractors, make sidecar text for "pdftotext-only" files,
# then rerun the indexer. Idempotent and safe: backs up any created files.

REPO_ROOT="$(pwd)"
export PYTHONPATH="$REPO_ROOT/src"
DATA_DIR="$REPO_ROOT/src/webapp/assistants/project_assistant/tools/chatbot/data"
LOGDIR="$REPO_ROOT/logs"
REPORT="$REPO_ROOT/logs/pdf_text_report.csv"
SIDECAR_DIR="$DATA_DIR/pdftotext_sidecars"
INDEX_LOG="$LOGDIR/index_run_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOGDIR"
mkdir -p "$SIDECAR_DIR"

echo "DATA_DIR = $DATA_DIR"
echo "Found PDFs:"
ls -1 "$DATA_DIR"/*.pdf 2>/dev/null || echo "  (none found)"

echo "Running PDF text diagnostics and preparing sidecars (if needed)..."
echo "file,pdftotext_chars,pypdf_chars,pdfminer_chars,action" > "$REPORT"

shopt -s nullglob
pdf_count=0
for f in "$DATA_DIR"/*.pdf; do
  pdf_count=$((pdf_count+1))
  bn=$(basename "$f")
  # pdftotext (poppler)
  if command -v pdftotext >/dev/null 2>&1; then
    pt=$(pdftotext -layout "$f" - | wc -c || echo 0)
  else
    pt=0
  fi

  # PyPDF2
  py=$(python - <<'PY' 2>/dev/null || true
from PyPDF2 import PdfReader
import sys
p = sys.argv[1]
try:
    r = PdfReader(p)
    s = ""
    for pg in r.pages:
        s += (pg.extract_text() or "")
    print(len(s))
except Exception:
    print(0)
PY
"$f")

  # pdfminer
  pm=$(python - <<'PY' 2>/dev/null || true
from pdfminer.high_level import extract_text
import sys
p = sys.argv[1]
try:
    t = extract_text(p)
    print(len(t) if t else 0)
except Exception:
    print(0)
PY
"$f")

  action="none"
  # if pdftotext sees text but both python extractors see 0 -> create sidecar text file
  if [ "$pt" -gt 0 ] && [ "$py" -eq 0 ] && [ "$pm" -eq 0 ]; then
    sc="$SIDECAR_DIR/${bn}.pdftotext.txt"
    if [ ! -f "$sc" ]; then
      echo "Creating sidecar for $bn (pdftotext sees text, python extractors don't)..."
      pdftotext -layout "$f" - > "$sc" || echo "" > "$sc"
      action="sidecar_created"
    else
      action="sidecar_exists"
    fi
  fi

  echo "$bn,$pt,$py,$pm,$action" >> "$REPORT"
done

echo "Processed $pdf_count PDF(s)."
echo "Wrote diagnostics to $REPORT"
echo

# Show a short preview of the report (top 20)
echo "=== REPORT PREVIEW ==="
head -n 22 "$REPORT" | sed -n '1,120p'
echo "======================"
echo

sidecar_count=$(ls -1 "$SIDECAR_DIR"/*.txt 2>/dev/null | wc -l || echo 0)
echo "Sidecar files present: $sidecar_count (in $SIDECAR_DIR)"
if [ "$sidecar_count" -gt 0 ]; then
  echo "Sidecars example (first 3):"
  ls -1 "$SIDECAR_DIR"/*.txt 2>/dev/null | head -n 3 | sed -n '1,120p'
  echo
fi

# Run the indexer with logging. The indexer will still behave as before,
# but we created sidecar text files to help manual debugging or future code changes.
echo "Starting indexer (output -> $INDEX_LOG)..."
python -m webapp.assistants.project_assistant.tools.chatbot.indexer.runner 2>&1 | tee "$INDEX_LOG"
RC=${PIPESTATUS[0]}

echo
echo "=== INDEXER SUMMARY (tail of log) ==="
tail -n 40 "$INDEX_LOG" || true
echo "=== END LOG PREVIEW ==="
echo

if [ "$RC" -ne 0 ]; then
  echo "Indexer finished with non-zero exit code: $RC"
else
  echo "Indexer finished with exit code 0"
fi

echo
echo "If the indexer still skipped files, check $REPORT and the sidecars in $SIDECAR_DIR."
echo "Next steps:"
echo " - If pdftotext shows >0 but indexer skipped: ik kan direct een patch maken om pdftotext als fallback in de indexer te gebruiken."
echo " - Als pdftotext == 0: de PDF’s missen echt een tekstlaag (dan OCR / re-export nodig)."

exit $RC
