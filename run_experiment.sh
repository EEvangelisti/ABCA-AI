#!/bin/bash
set -euo pipefail

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

team="unknown"
args=("$@")

for ((i=0; i<${#args[@]}; i++)); do
    if [[ "${args[i]}" == "--team" && $((i+1)) -lt ${#args[@]} ]]; then
        team="${args[i+1]}"
        break
    fi
done

python_venvs/agents/bin/python -u -m source.run_experiment "$@" 2>&1 \
  | tee "run_${team}_${timestamp}.log"
