#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
PYTHON="${VENV}/bin/python"

if [[ ! -d "$VENV" ]]; then
  echo ">> Creating virtualenv at .venv"
  python3 -m venv "$VENV"
fi

INSTALL_CMD="$PYTHON -m pip install -r requirements.txt && $PYTHON -m pip install -e ."
VERIFY_CMD="PYTHONPATH=. $PYTHON -m unittest discover -s tests/unit -p 'test_*.py' -q"
START_CMD="python3 scripts/dev_up.py"

echo "== GTM Engine init =="
echo "Directory: $ROOT"
echo "Python: $PYTHON"
echo ""

echo ">> Installing dependencies..."
eval "$INSTALL_CMD"
echo ""

echo ">> Running verification..."
eval "$VERIFY_CMD"
echo "Verification: PASS"
echo ""

if [[ "${RUN_START_COMMAND:-0}" == "1" ]]; then
  echo ">> Starting dev stack..."
  eval "$START_CMD"
else
  echo ">> Start command (not run):"
  echo "   $START_CMD"
  echo ""
  echo "   To start automatically: RUN_START_COMMAND=1 ./init.sh"
  echo "   To activate venv: source .venv/bin/activate"
fi