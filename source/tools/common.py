from pathlib import Path
from source.config import MAX_OUTPUT

def ensure_inside(path: Path, root: Path) -> Path:
    path = path.resolve()
    root = root.resolve()

    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Access denied: {path} is outside allowed root {root}"
        )

    return path


def truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text

    return (
        "[OUTPUT TRUNCATED — showing final part]\n\n"
        + text[-limit:]
    )
