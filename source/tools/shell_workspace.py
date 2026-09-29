"""Run workspace commands in the same isolated layout as analysis_python.py.

Copy input_data/analysis_toolsuite to /work/analysis_toolsuite before invoking
its Bash entry points. The original input package stays read-only at /data.
"""

import subprocess

from agents.decorators import tool

from source.config import (
    ANALYSIS_DIR,
    ANALYSIS_TIMEOUT,
    INPUT_DATA_DIR,
    OPAM_PREFIX,
)
from source.tools.analysis_python import sandbox_runtime_bindings
from source.tools.common import truncate


MAX_COMMAND_CHARS = 8_000


def _run_workspace_command_impl(command: str, timeout_seconds: int = 300) -> str:
    """Run a Bash command with /data read-only and /work read-write.

    The command starts in /work, has no network, and cannot see the host
    repository outside the explicit mounts. For the supplied toolsuite, first
    copy /data/analysis_toolsuite to /work/analysis_toolsuite, then run its
    `run` or `batch_run` entry point with configs and outputs under /work.
    This tool is intended for Scripter and LinuxOracle, not web searches.
    """
    if not isinstance(command, str) or not command.strip():
        return "Denied: command is empty."
    if len(command) > MAX_COMMAND_CHARS or "\x00" in command:
        return "Denied: command is too long or contains a NUL byte."

    timeout_seconds = min(max(int(timeout_seconds), 1), ANALYSIS_TIMEOUT)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    sandbox = [
        "bwrap", "--unshare-all", "--unshare-net", "--die-with-parent",
        "--new-session", "--proc", "/proc", "--dev", "/dev",
        "--tmpfs", "/tmp", "--ro-bind", str(INPUT_DATA_DIR), "/data",
        "--bind", str(ANALYSIS_DIR), "/work", "--chdir", "/work",
        *sandbox_runtime_bindings(),
        "/bin/bash", "--noprofile", "--norc", "-c", command,
    ]

    try:
        result = subprocess.run(
            sandbox, cwd=ANALYSIS_DIR, capture_output=True, text=True,
            timeout=timeout_seconds,
            env={
                "PATH": f"{OPAM_PREFIX / 'bin'}:/usr/bin:/bin",
                "HOME": "/work",
                "TMPDIR": "/tmp",
                "PYTHONNOUSERSITE": "1",
                "BASH_ENV": "",
                "OPAM_SWITCH_PREFIX": str(OPAM_PREFIX),
            },
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout_seconds} seconds."
    except OSError as exc:
        return f"Could not start isolated shell: {exc}"

    return truncate(
        f"COMMAND: {command}\nEXIT CODE: {result.returncode}\n\n"
        f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    )


@tool
def run_workspace_command(command: str, timeout_seconds: int = 300) -> str:
    """Run a Bash command with /data read-only and /work read-write.

    The command starts in /work, has no network, and cannot see the host
    repository outside the explicit mounts. For the supplied toolsuite, first
    copy /data/analysis_toolsuite to /work/analysis_toolsuite, then run its
    `run` or `batch_run` entry point with configs and outputs under /work.
    """
    return _run_workspace_command_impl(command, timeout_seconds)
