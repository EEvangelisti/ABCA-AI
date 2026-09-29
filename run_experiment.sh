#!/bin/bash
set -euo pipefail

# Relaunch once inside a memory-limited systemd scope.
if [[ "${ABCA_AI_SCOPED:-0}" != "1" ]]; then
    exec systemd-run --user --scope \
        -p MemoryHigh=20G \
        -p MemoryMax=24G \
        -p MemorySwapMax=4G \
        env ABCA_AI_SCOPED=1 "$0" "$@"
fi

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
