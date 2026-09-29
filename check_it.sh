#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 TEAM [PROFILE]" >&2
    echo "Example: $0 discovery" >&2
    echo "         $0 refinement model_b" >&2
    exit 2
fi

TEAM="$1"
PROFILE="${2:-}"

CONFIG_ARGS=(--team "$TEAM")
if [[ -n "$PROFILE" ]]; then
    CONFIG_ARGS+=(--profile "$PROFILE")
fi

AGENT_PY="python_venvs/agents/bin/python"
ANALYSIS_PY="python_venvs/analysis/bin/python"

echo "========================================================================"
echo "1. Python syntax / imports"
echo "========================================================================"

"$AGENT_PY" -m compileall -q source
echo "source compileall OK"

"$AGENT_PY" - "${CONFIG_ARGS[@]}" <<'PY'
import source.config as config

print("config import OK")
print("team           :", config.ARGS.team)
print("active profile :", config.ACTIVE_PROFILE_NAME)
print("workflow       :", config.WORKFLOW)
print("prompt module  :", config.ACTIVE_PROMPTS)
print(
    "active agents  :",
    ", ".join(
        f"{spec['id']}[{spec['role']}]"
        for spec in config.ACTIVE_AGENTS
    ),
)
PY


echo
echo "========================================================================"
echo "2. Tool registry and JSON toolsets"
echo "========================================================================"

"$AGENT_PY" - "${CONFIG_ARGS[@]}" <<'PY'
import source.config as config
from source.agents.team import resolve_tool

errors = []

for spec in config.ACTIVE_AGENTS:
    agent_id = spec["id"]
    toolset_name = spec["toolset"]

    print(f"{agent_id} -> {toolset_name}")

    for tool_name in config.get_toolset_names(agent_id):
        try:
            tool = resolve_tool(tool_name)
        except Exception as exc:
            errors.append((agent_id, tool_name, str(exc)))
            print(f"  FAIL  {tool_name}: {exc}")
        else:
            print(f"  OK    {tool_name} -> {tool!r}")

if errors:
    print("\nTool resolution errors:")
    for agent_id, tool_name, message in errors:
        print(f"  {agent_id}: {tool_name}: {message}")

    raise SystemExit(
        "\nOne or more symbolic tool names from experiment_config.json "
        "could not be resolved through source.tools."
    )

print("\nAll configured tools resolved successfully.")
PY


echo
echo "========================================================================"
echo "3. Team and orchestrator construction"
echo "========================================================================"

"$AGENT_PY" - "${CONFIG_ARGS[@]}" <<'PY'
import source.config as config
from source.agents.team import create_team
from source.agents.orchestrator import make_orchestrator

team = create_team()

expected = [spec["id"] for spec in config.ACTIVE_AGENTS]
actual = list(team)

if set(expected) != set(actual):
    raise RuntimeError(
        f"Team mismatch: expected={expected}, actual={actual}"
    )

print("team creation OK")
print("team:", ", ".join(actual))

orchestrator = make_orchestrator(team)

print("orchestrator creation OK")
print("orchestrator:", orchestrator.name)
PY


echo
echo "========================================================================"
echo "4. Scientific analysis environment"
echo "========================================================================"

"$ANALYSIS_PY" - <<'PY'
import numpy
import pandas
import scipy
import sklearn
import statsmodels

print("analysis env OK")
print("numpy      :", numpy.__version__)
print("pandas     :", pandas.__version__)
print("scipy      :", scipy.__version__)
print("sklearn    :", sklearn.__version__)
print("statsmodels:", statsmodels.__version__)
PY


echo
echo "========================================================================"
echo "5. Bubblewrap / analysis sandbox smoke test"
echo "========================================================================"

ANALYSIS_WORKSPACE="$("$AGENT_PY" - "${CONFIG_ARGS[@]}" <<'PY'
from source.config import ANALYSIS_DIR
print(ANALYSIS_DIR)
PY
)"
mkdir -p "$ANALYSIS_WORKSPACE"
SMOKE_SCRIPT="$ANALYSIS_WORKSPACE/_sandbox_smoke_test.py"
SMOKE_OUTPUT="$ANALYSIS_WORKSPACE/_sandbox_smoke_test_output.txt"
SHELL_OUTPUT="$ANALYSIS_WORKSPACE/_shell_tool_smoke_output.txt"

cleanup() {
    rm -f "$SMOKE_SCRIPT" "$SMOKE_OUTPUT" "$SHELL_OUTPUT"
}
trap cleanup EXIT

cat > "$SMOKE_SCRIPT" <<'PY'
import sys
import numpy as np
from pathlib import Path

print("python:", sys.executable)
print("numpy:", np.__version__)

data = Path("/data")
work = Path("/work")

print("data exists:", data.exists())
print("work exists:", work.exists())

files = list(data.rglob("*"))
print("input files visible:", len(files))

out = work / "_sandbox_smoke_test_output.txt"
out.write_text("sandbox write OK\n")

print("write OK:", out.exists())
print("SANDBOX TEST PASSED")
PY

"$AGENT_PY" -m source.test_analysis_tool "${CONFIG_ARGS[@]}"

echo
echo "========================================================================"
echo "6. Shell tool functional test"
echo "========================================================================"

"$AGENT_PY" - "${CONFIG_ARGS[@]}" <<'PY'
from source.tools.shell_workspace import _run_workspace_command_impl

result = _run_workspace_command_impl(
    "printf 'SHELL_TOOL_OK\\n' | tee /work/_shell_tool_smoke_output.txt",
    timeout_seconds=30,
)
print(result)
if "EXIT CODE: 0" not in result or "SHELL_TOOL_OK" not in result:
    raise SystemExit("Shell tool did not complete successfully")
PY

test "$(cat "$SHELL_OUTPUT")" = "SHELL_TOOL_OK"
echo "shell tool write verified in analysis workspace"

echo
echo "========================================================================"
echo "7. ABCA build inside the actual agent shell (modelling team)"
echo "========================================================================"

if [[ "$TEAM" == "modelling" ]]; then
"$AGENT_PY" - "${CONFIG_ARGS[@]}" <<'PY'
from source.config import ANALYSIS_TIMEOUT
from source.tools.shell_workspace import _run_workspace_command_impl

command = r'''set -euo pipefail
printf 'ABCA toolchain inside isolated shell:\n'
for executable in dune ocamlc; do
    if ! command -v "$executable"; then
        printf 'MISSING: %s is not on the isolated shell PATH\n' "$executable" >&2
        exit 20
    fi
    printf '%s: %s\n' "$executable" "$(command -v "$executable")"
done

printf 'dune version: '
dune --version
printf 'ocamlc version: '
ocamlc -version
printf 'ocamlfind: '
command -v ocamlfind
printf 'cairo2 package: '
ocamlfind query cairo2

if [[ -f /data/ABCA/dune-project ]]; then
    source_dir=/data/ABCA
else
    printf 'ABCA repository not found at /data/ABCA (expected dune-project).\n' >&2
    printf 'Visible candidate dune-project files:\n' >&2
    find /data -maxdepth 4 -name dune-project -print 2>/dev/null | head -20 >&2
    exit 21
fi

build_dir=$(mktemp -d /work/abca-build-check.XXXXXXXX)
trap 'rm -rf "$build_dir"' EXIT
cp -a "$source_dir"/. "$build_dir"/
cd "$build_dir"
printf 'Building copied ABCA repository from %s\n' "$source_dir"
dune build --display short
printf 'ABCA_BUILD_OK\n'
'''

result = _run_workspace_command_impl(
    command, timeout_seconds=min(180, ANALYSIS_TIMEOUT)
)
print(result)
if "EXIT CODE: 0" not in result or "ABCA_BUILD_OK" not in result:
    raise SystemExit(
        "ABCA could not be built inside run_workspace_command. "
        "Inspect the toolchain, path, dependencies or timeout above."
    )
PY
else
    echo "Skipped: ABCA build check applies to TEAM=modelling."
fi


echo
echo "========================================================================"
echo "8. Europe PMC tool functional test"
echo "========================================================================"

"$AGENT_PY" - "${CONFIG_ARGS[@]}" <<'PY'
from source.tools.literature import _search, _record

payload = _search("Phytophthora zoospore", 2)
records = payload.get("resultList", {}).get("result", [])
if not records or not records[0].get("title"):
    raise SystemExit(f"Europe PMC returned no usable record: {payload}")
record = _record(records[0])
print("Europe PMC query OK; hits:", payload.get("hitCount"))
print("first title:", record["title"])
print("first identifier:", record.get("doi") or record.get("pmid"))
PY


echo
echo "========================================================================"
echo "ALL CHECKS PASSED"
echo "========================================================================"
