from importlib import import_module

from agents import Agent

import source.config as config


# By default, symbolic tool names from experiment_config.json are looked up
# in source.tools. Additional public tool modules may be declared in JSON via:
#
#   "tool_modules": ["source.tools", "source.analysis_tools"]
#
_TOOL_MODULE_NAMES = config.EXPERIMENT_CONFIG.get(
    "tool_modules",
    ["source.tools"],
)

_TOOL_MODULES = [
    import_module(module_name)
    for module_name in _TOOL_MODULE_NAMES
]


def resolve_tool(tool_name):
    """
    Resolve a symbolic tool name from experiment_config.json to the actual
    Python object decorated with @tool / @function_tool.

    The configured string is the Python attribute name exported by one of the
    configured public tool modules.
    """
    matches = []

    for module in _TOOL_MODULES:
        if hasattr(module, tool_name):
            matches.append(
                (module.__name__, getattr(module, tool_name))
            )

    if not matches:
        searched = ", ".join(_TOOL_MODULE_NAMES)
        raise RuntimeError(
            f"Configured tool {tool_name!r} was not found in: {searched}"
        )

    if len(matches) > 1:
        modules = ", ".join(
            module_name
            for module_name, _ in matches
        )
        raise RuntimeError(
            f"Configured tool {tool_name!r} is ambiguous; "
            f"it exists in multiple tool modules: {modules}"
        )

    return matches[0][1]


def resolve_agent_tools(agent_id):
    """
    Resolve every symbolic tool configured for one active agent.
    """
    return [
        resolve_tool(tool_name)
        for tool_name in config.get_toolset_names(agent_id)
    ]


def create_agent(agent_spec):
    """
    Create one specialist Agent from the active JSON profile.

    Agent identity, role, model, prompt and toolset are all supplied by
    experiment_config.json and resolved through source.config.
    """
    agent_id = agent_spec["id"]

    return Agent(
        name=agent_id,
        model=config.get_agent_model(agent_id),
        instructions=config.get_agent_prompt(agent_id),
        tools=resolve_agent_tools(agent_id),
    )


def create_team():
    """
    Instantiate every specialist declared in the active profile.

    The exact composition of the team is therefore controlled entirely by
    experiment_config.json.
    """
    return {
        spec["id"]: create_agent(spec)
        for spec in config.ACTIVE_AGENTS
    }
