#!/usr/bin/env bash
set -euo pipefail

# Usar este script solamente en un clon exclusivo del daemon.
REPO_DIR="/RUTA/ABSOLUTA/proyecto-sensores-datos"
PYTHON_BIN="/RUTA/ABSOLUTA/venv/bin/python"
BRANCH="main"

cd "$REPO_DIR"

# Un cambio inesperado indica intervención manual o una ejecución incompleta.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: el clon del daemon tiene cambios sin commit" >&2
  exit 1
fi

git pull --ff-only origin "$BRANCH"

"$PYTHON_BIN" scripts/export_monthly_csv.py
"$PYTHON_BIN" scripts/validate_export.py

if [[ -n "$(git status --porcelain -- data)" ]]; then
  git add -- data
  git commit -m "datos: actualización horaria"
fi

# También publica un commit conservado después de una falla de red anterior.
git push origin "$BRANCH"
