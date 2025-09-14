#!/usr/bin/env bash
set -euo pipefail

timestamp() { date +"%Y%m%d-%H%M%S"; }

# 1) Backup branch maken
BACKUP_BRANCH="pre-refactor-$(timestamp)"
echo "==> Maak backup branch: $BACKUP_BRANCH"
git checkout -b "$BACKUP_BRANCH"

# commit alles indien er ongestage wijzigingen zijn (veiligheidsbackup)
git add -A
if git diff --cached --quiet; then
  echo "  - Geen staged changes om te committen (working tree clean)"
else
  git commit -m "wip: backup before cleanup ($BACKUP_BRANCH)" || true
fi

# 2) .gitignore updaten (idempotent)
echo "==> .gitignore updaten (voegt alleen toe wat nog niet bestaat)"
GITIGNORE_ENTRIES=$'__pycache__/\n*.pyc\n.vscode/\nsecrets.toml\n.env\n.env.*\n'
touch .gitignore
echo "$GITIGNORE_ENTRIES" | while IFS= read -r line; do
  # skip lege regels
  [[ -z "$line" ]] && continue
  if ! grep -Fxq "$line" .gitignore 2>/dev/null; then
    echo "$line" >> .gitignore
    echo "  - toegevoegd aan .gitignore: $line"
  fi
done

git add .gitignore
git commit -m "chore: update .gitignore (ignore pyc, __pycache__, secrets, env files)" || true

# 3) Verwijder __pycache__ mappen en .pyc uit git (cached)
echo "==> Verwijder __pycache__ mappen en .pyc bestanden uit git (git rm --cached)"
# verwijder directories uit git index
find . -type d -name '__pycache__' -print0 | xargs -0 -r git rm -r --cached || true
# verwijder losse .pyc bestanden
find . -type f -name '*.pyc' -print0 | xargs -0 -r git rm --cached || true

# 4) Commit veranderingen
git add -A
if git diff --cached --quiet; then
  echo "  - Geen verdere wijzigingen om te committen"
else
  git commit -m "chore: remove compiled python files (pyc, __pycache__) from git" || true
fi

echo "==> Klaar. Controleer status met: git status"
echo "Backup branch: $BACKUP_BRANCH"
echo "Als alles ok is, push de backup branch (optioneel):"
echo "  git push origin $BACKUP_BRANCH"

exit 0
