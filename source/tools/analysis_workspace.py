from source.config import ANALYSIS_DIR, MAX_ANALYSIS_READ, MAX_ANALYSIS_SCRIPT_SIZE
from source.tools.common import ensure_inside
from agents.decorators import tool

@tool
def list_analysis_files(relative_path: str = ".") -> str:
    """
    List files inside the isolated analysis workspace.
    """
    target = ensure_inside(
        ANALYSIS_DIR / relative_path,
        ANALYSIS_DIR,
    )

    if not target.exists():
        return f"Path does not exist: {relative_path}"

    if target.is_file():
        return str(target.relative_to(ANALYSIS_DIR))

    entries = []

    for p in sorted(target.iterdir()):
        suffix = "/" if p.is_dir() else ""
        entries.append(
            str(p.relative_to(ANALYSIS_DIR)) + suffix
        )

    return "\n".join(entries)


@tool
def read_analysis_file(
    relative_path: str,
    max_chars: int = MAX_ANALYSIS_READ,
) -> str:
    """
    Read a text file produced inside the analysis workspace.
    """
    target = ensure_inside(
        ANALYSIS_DIR / relative_path,
        ANALYSIS_DIR,
    )

    if not target.exists():
        return f"File does not exist: {relative_path}"

    if not target.is_file():
        return f"Not a file: {relative_path}"

    try:
        text = target.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        return f"Could not read {relative_path}: {exc}"

    max_chars = min(
        max(1000, max_chars),
        MAX_ANALYSIS_READ,
    )

    if len(text) > max_chars:
        return (
            text[:max_chars]
            + f"\n\n[FILE TRUNCATED at {max_chars} characters]"
        )

    return text


@tool
def write_analysis_file(
    relative_path: str,
    content: str,
) -> str:
    """
    Create or overwrite a file inside analysis_workspace only.

    Intended for Python analysis scripts, CSV summaries,
    JSON outputs, Markdown notes, etc.
    """
    if len(content) > MAX_ANALYSIS_SCRIPT_SIZE:
        return (
            f"Denied: file content exceeds "
            f"{MAX_ANALYSIS_SCRIPT_SIZE} characters."
        )

    target = ensure_inside(
        ANALYSIS_DIR / relative_path,
        ANALYSIS_DIR,
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        content,
        encoding="utf-8",
    )

    return (
        f"Wrote {len(content)} characters to "
        f"analysis_workspace/{target.relative_to(ANALYSIS_DIR)}"
    )

