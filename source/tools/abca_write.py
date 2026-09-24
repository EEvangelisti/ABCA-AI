import shutil
from source.config import PLUGIN_DIR, ABCA_DIR, REGISTRY_DIR, ANALYSIS_DIR
from source.tools.common import ensure_inside
from agents.decorators import tool


@tool
def write_discovered_plugin_file(
    relative_path: str,
    content: str
) -> str:
    """
    Create or overwrite a file inside
    plugins/discovered_swimming only.
    """
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    target = ensure_inside(
        PLUGIN_DIR / relative_path,
        PLUGIN_DIR
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    target.write_text(
        content,
        encoding="utf-8"
    )

    return (
        f"Wrote {len(content)} characters to "
        f"{target.relative_to(ABCA_DIR)}"
    )


@tool
def write_plugin_registry_file(
    relative_path: str,
    content: str
) -> str:
    """
    Create or overwrite a file inside plugin_registry only.
    """
    target = ensure_inside(
        REGISTRY_DIR / relative_path,
        REGISTRY_DIR
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    target.write_text(
        content,
        encoding="utf-8"
    )

    return (
        f"Wrote {len(content)} characters to "
        f"{target.relative_to(ABCA_DIR)}"
    )


@tool
def copy_abca_output_to_analysis(
    abca_relative_path: str,
    analysis_relative_path: str,
) -> str:
    """
    Copy an existing ABCA output file into analysis_workspace.

    Source must remain inside the ABCA repository.
    Destination must remain inside analysis_workspace.
    """
    source = ensure_inside(
        ABCA_DIR / abca_relative_path,
        ABCA_DIR,
    )

    destination = ensure_inside(
        ANALYSIS_DIR / analysis_relative_path,
        ANALYSIS_DIR,
    )

    if not source.exists():
        return f"Source does not exist: {abca_relative_path}"

    if not source.is_file():
        return f"Source is not a file: {abca_relative_path}"

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    return (
        f"Copied {source.relative_to(ABCA_DIR)} "
        f"to analysis_workspace/"
        f"{destination.relative_to(ANALYSIS_DIR)}"
    )

