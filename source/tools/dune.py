import shlex
import subprocess

from agents.decorators import tool

from source.config import ABCA_DIR, COMMAND_TIMEOUT
from source.tools.common import truncate

@tool
def run_dune_build() -> str:
    """
    Run dune build from the ABCA repository root.
    """
    try:
        result = subprocess.run(
            ["dune", "build"],
            cwd=ABCA_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return (
            f"dune build timed out "
            f"after {COMMAND_TIMEOUT}s"
        )

    return truncate(
        f"EXIT CODE: {result.returncode}\n\n"
        f"STDOUT:\n{result.stdout}\n\n"
        f"STDERR:\n{result.stderr}"
    )


@tool
def run_dune_command(arguments: str) -> str:
    """
    Run a restricted dune command.

    Allowed:
      dune build
      dune exec ...
      dune runtest ...
    """
    try:
        args = shlex.split(arguments)
    except ValueError as exc:
        return f"Invalid arguments: {exc}"

    if not args:
        return "No arguments supplied."

    if args[0] not in {
        "build",
        "exec",
        "runtest",
    }:
        return (
            "Denied. Allowed dune operations: "
            "build, exec, runtest."
        )

    command = ["dune"] + args

    try:
        result = subprocess.run(
            command,
            cwd=ABCA_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return (
            f"Command timed out "
            f"after {COMMAND_TIMEOUT}s"
        )

    return truncate(
        f"COMMAND: {' '.join(command)}\n"
        f"EXIT CODE: {result.returncode}\n\n"
        f"STDOUT:\n{result.stdout}\n\n"
        f"STDERR:\n{result.stderr}"
    )


