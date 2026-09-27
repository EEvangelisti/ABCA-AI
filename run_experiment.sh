#!/bin/bash
set -euo pipefail

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

python_venvs/agents/bin/python -u -m source.run_experiment 2>&1 \
  | tee "run_refinement_${timestamp}.log"
