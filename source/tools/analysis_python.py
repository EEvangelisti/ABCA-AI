from pathlib import Path
import shlex
import subprocess

from agents.decorators import tool

from source.config import (
    INPUT_DATA_DIR,
    ANALYSIS_DIR,
    ANALYSIS_TIMEOUT,
    ANALYSIS_PYTHON,
    ANALYSIS_PYTHON_PREFIX,
)

from source.tools.common import (
    ensure_inside,
    truncate,
)


def python_runtime_bindings() -> list[str]:
    """
    Construct read-only filesystem bindings required by the
    dedicated scientific Python environment.
    """
    bindings = []

    # System libraries and executables required by Python.
    for path in (
        "/usr",
        "/bin",
        "/lib",
        "/lib64",
        "/etc/ld.so.cache",
    ):
        p = Path(path)

        if p.exists():
            bindings.extend(
                ["--ro-bind", path, path]
            )

    # Dedicated scientific Python environment.
    if ANALYSIS_PYTHON_PREFIX.exists():
        bindings.extend(
            [
                "--ro-bind",
                str(ANALYSIS_PYTHON_PREFIX),
                str(ANALYSIS_PYTHON_PREFIX),
            ]
        )

    return bindings


def _run_analysis_script_impl(
    relative_path: str,
    arguments: str = "",
) -> str:
    """
    Internal implementation used both by tests and by the agent tool.
    """

    script = ensure_inside(
        ANALYSIS_DIR / relative_path,
        ANALYSIS_DIR,
    )

    if not script.exists():
        return f"Script does not exist: {relative_path}"

    if not script.is_file():
        return f"Not a file: {relative_path}"

    if script.suffix.lower() != ".py":
        return "Denied: only .py analysis scripts may be executed."

    try:
        extra_args = shlex.split(arguments)
    except ValueError as exc:
        return f"Invalid arguments: {exc}"

    if len(extra_args) > 50:
        return "Denied: too many command-line arguments."

    sandbox_script = (
        "/work/"
        + str(script.relative_to(ANALYSIS_DIR))
    )

    command = [
        "bwrap",

        "--unshare-all",
        "--unshare-net",

        "--die-with-parent",
        "--new-session",

        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",

        "--ro-bind",
        str(INPUT_DATA_DIR),
        "/data",

        "--bind",
        str(ANALYSIS_DIR),
        "/work",

        "--chdir",
        "/work",
    ]

    command.extend(
        python_runtime_bindings()
    )

    command.extend(
        [
            str(ANALYSIS_PYTHON),
            "-I",
            sandbox_script,
            *extra_args,
        ]
    )

    try:
        result = subprocess.run(
            command,
            cwd=ANALYSIS_DIR,
            capture_output=True,
            text=True,
            timeout=ANALYSIS_TIMEOUT,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": "/work",
                "TMPDIR": "/tmp",
                "PYTHONNOUSERSITE": "1",
            },
        )

    except subprocess.TimeoutExpired:
        return (
            f"Analysis timed out after "
            f"{ANALYSIS_TIMEOUT} seconds."
        )

    return truncate(
        f"COMMAND: python {relative_path} {arguments}\n"
        f"EXIT CODE: {result.returncode}\n\n"
        f"STDOUT:\n{result.stdout}\n\n"
        f"STDERR:\n{result.stderr}"
    )


@tool
def run_analysis_script(
    relative_path: str,
    arguments: str = "",
) -> str:
    """
    Run a Python script from analysis_workspace inside the isolated
    analysis sandbox.

    Inside the sandbox:
      - /data is the complete experimental input dataset (read-only).
      - /work is analysis_workspace (read/write).
      - large input files should be parsed or streamed directly from /data
        rather than transferred through read_input_file().

    Analysis scripts should be resource-aware. For large datasets, avoid
    repeated full-data parsing, repeated equivalent model fits, and Python
    row-wise loops. Cache compact derived representations and use vectorized
    or streaming computations where practical.
    """
    return _run_analysis_script_impl(
        relative_path,
        arguments,
    )
