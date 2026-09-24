"""
Public tool registry for ABCA AI agents.

All agent-accessible @tool objects are re-exported here so that
source.agents.team can resolve symbolic tool names from
experiment_config.json via getattr(source.tools, tool_name).
"""

from .abca_read import (
    list_abca_files,
    read_abca_file,
)

from .abca_write import (
    write_discovered_plugin_file,
    write_plugin_registry_file,
    copy_abca_output_to_analysis,
)

from .analysis_python import (
    run_analysis_script,
)

from .analysis_workspace import (
    list_analysis_files,
    read_analysis_file,
    write_analysis_file,
)

from .dune import (
    run_dune_build,
    run_dune_command,
)

from .input_data import (
    list_input_files,
    read_input_file,
    inspect_input_file,
    read_input_file_chunk,
    inspect_csv,
    csv_column_summary,
)


__all__ = [
    # ABCA read access
    "list_abca_files",
    "read_abca_file",

    # ABCA / plugin write access
    "write_discovered_plugin_file",
    "write_plugin_registry_file",
    "copy_abca_output_to_analysis",

    # Analysis sandbox
    "run_analysis_script",

    # Analysis workspace
    "list_analysis_files",
    "read_analysis_file",
    "write_analysis_file",

    # Dune / ABCA execution
    "run_dune_build",
    "run_dune_command",

    # Experimental input data
    "list_input_files",
    "read_input_file",
    "inspect_input_file",
    "read_input_file_chunk",
    "inspect_csv",
    "csv_column_summary",
]
