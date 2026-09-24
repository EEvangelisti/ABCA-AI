from source.config import ABCA_DIR, MAX_FILE_SIZE
from source.tools.common import ensure_inside
from agents.decorators import tool

@tool
def list_abca_files(relative_path: str = ".") -> str:
    """
    List files or directories inside the ABCA repository.
    """
    target = ensure_inside(ABCA_DIR / relative_path, ABCA_DIR)

    if not target.exists():
        return f"Path does not exist: {relative_path}"

    if target.is_file():
        return str(target.relative_to(ABCA_DIR))

    entries = []
    for p in sorted(target.iterdir()):
        suffix = "/" if p.is_dir() else ""
        entries.append(str(p.relative_to(ABCA_DIR)) + suffix)

    return "\n".join(entries)
    

@tool
def read_abca_file(relative_path: str) -> str:
    """
    Read a UTF-8 text file inside the ABCA repository.
    """
    target = ensure_inside(ABCA_DIR / relative_path, ABCA_DIR)

    if not target.exists():
        return f"File does not exist: {relative_path}"

    if not target.is_file():
        return f"Not a file: {relative_path}"

    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Cannot read binary/non-UTF8 file: {relative_path}"

    if len(text) > MAX_FILE_SIZE:
        return text[:MAX_FILE_SIZE] + "\n\n[FILE TRUNCATED]"

    return text
