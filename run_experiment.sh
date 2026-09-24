#!/bin/bash

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

python_venvs/agents/bin/python -u -m source.run_experiment 2>&1 \
  | tee "run_full_discovery_${timestamp}.log"
