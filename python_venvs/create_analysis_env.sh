#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/python_venvs/analysis"

echo "Creating analysis environment:"
echo "  ${VENV_DIR}"

python3 -m venv "${VENV_DIR}"

"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

"${VENV_DIR}/bin/pip" install \
    numpy \
    pandas \
    scipy \
    matplotlib \
    scikit-learn \
    statsmodels

echo
echo "Analysis environment ready."
echo
echo "Python:"
echo "  ${VENV_DIR}/bin/python"
