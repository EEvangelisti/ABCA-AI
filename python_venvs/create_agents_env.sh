#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/python_venvs/agents"

echo "Creating agents environment:"
echo "  ${VENV_DIR}"

python3 -m venv "${VENV_DIR}"

"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

"${VENV_DIR}/bin/pip" install \
    openai \
    openai-agents

echo
echo "Agents environment ready."
echo
echo "Activate with:"
echo "  source ${VENV_DIR}/bin/activate"
