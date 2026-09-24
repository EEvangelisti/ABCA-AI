import json
import tomllib
from pathlib import Path


# ------------------------------------------------------------------
# Base paths
# ------------------------------------------------------------------

SOURCE_DIR = Path(__file__).resolve().parent
BASE_DIR = SOURCE_DIR.parent
CONFIG_FILE = SOURCE_DIR / "experiment_config.json"


# ------------------------------------------------------------------
# Load experiment configuration
# ------------------------------------------------------------------

with CONFIG_FILE.open("r", encoding="utf-8") as f:
    EXPERIMENT_CONFIG = json.load(f)


# ------------------------------------------------------------------
# Active profile
# ------------------------------------------------------------------

ACTIVE_PROFILE_NAME = EXPERIMENT_CONFIG["active_profile"]

try:
    ACTIVE_PROFILE = EXPERIMENT_CONFIG["profiles"][ACTIVE_PROFILE_NAME]
except KeyError as exc:
    raise RuntimeError(
        f"Unknown active profile {ACTIVE_PROFILE_NAME!r}. "
        f"Available profiles: {', '.join(EXPERIMENT_CONFIG['profiles'])}"
    ) from exc

WORKFLOW = ACTIVE_PROFILE["workflow"]
ACTIVE_AGENTS = ACTIVE_PROFILE["agents"]

AGENT_SPECS = {
    agent["id"]: agent
    for agent in ACTIVE_AGENTS
}

if len(AGENT_SPECS) != len(ACTIVE_AGENTS):
    raise RuntimeError(
        f"Duplicate agent ids detected in profile {ACTIVE_PROFILE_NAME!r}"
    )

ACTIVE_ROLES = [agent["role"] for agent in ACTIVE_AGENTS]


# ------------------------------------------------------------------
# Runtime
# ------------------------------------------------------------------

RUNTIME = EXPERIMENT_CONFIG["runtime"]

MAX_TURNS = RUNTIME["max_turns"]
COMMAND_TIMEOUT = RUNTIME["command_timeout"]
ANALYSIS_TIMEOUT = RUNTIME["analysis_timeout"]
MAX_OUTPUT = RUNTIME["max_output"]
MAX_FILE_SIZE = RUNTIME["max_file_size"]
MAX_ANALYSIS_SCRIPT_SIZE = RUNTIME["max_analysis_script_size"]
MAX_ANALYSIS_READ = RUNTIME["max_analysis_read"]


# ------------------------------------------------------------------
# Toolsets
# ------------------------------------------------------------------

TOOLSETS = EXPERIMENT_CONFIG["toolsets"]

def get_toolset_names(agent_id):
    """
    Return the symbolic tool names configured for one active agent.

    Resolution of these symbolic names to actual @tool objects remains
    in source.agents.team, not in config.py.
    """
    try:
        spec = AGENT_SPECS[agent_id]
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown active agent {agent_id!r}. "
            f"Available agents: {', '.join(AGENT_SPECS)}"
        ) from exc

    toolset_name = spec["toolset"]

    try:
        return list(TOOLSETS[toolset_name])
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown toolset {toolset_name!r} for agent {agent_id!r}. "
            f"Available toolsets: {', '.join(TOOLSETS)}"
        ) from exc


for _agent_id in AGENT_SPECS:
    get_toolset_names(_agent_id)


ROLE_DESCRIPTIONS = EXPERIMENT_CONFIG["role_descriptions"]

def agent_tool_description(agent_spec):
    agent_id = agent_spec["id"]
    role = agent_spec["role"]

    base = ROLE_DESCRIPTIONS.get(
        role,
        f"Specialist agent with role {role!r}."
    )

    if agent_id != role:
        return f"{base} Specialist id: {agent_id}."

    return base


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

def get_agent_model(agent_id):
    """
    Return the model configured for one active specialist agent.
    """
    try:
        spec = AGENT_SPECS[agent_id]
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown active agent {agent_id!r}. "
            f"Available agents: {', '.join(AGENT_SPECS)}"
        ) from exc

    try:
        model = spec["model"]
    except KeyError as exc:
        raise RuntimeError(
            f"Agent {agent_id!r} in profile {ACTIVE_PROFILE_NAME!r} "
            f"does not define a model."
        ) from exc

    if not isinstance(model, str) or not model.strip():
        raise RuntimeError(
            f"Invalid model for agent {agent_id!r}: {model!r}"
        )

    return model


AGENT_MODELS = {
    agent_id: get_agent_model(agent_id)
    for agent_id in AGENT_SPECS
}


try:
    ORCHESTRATOR_MODEL = ACTIVE_PROFILE["orchestrator"]["model"]
except KeyError as exc:
    raise RuntimeError(
        f"Profile {ACTIVE_PROFILE_NAME!r} does not define an "
        f"orchestrator model."
    ) from exc

if not isinstance(ORCHESTRATOR_MODEL, str) or not ORCHESTRATOR_MODEL.strip():
    raise RuntimeError(
        f"Invalid orchestrator model: {ORCHESTRATOR_MODEL!r}"
    )


def get_agent_max_turns(agent_id):
    """
    Return the maximum number of turns allowed for one specialist call.
    """
    try:
        spec = AGENT_SPECS[agent_id]
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown active agent {agent_id!r}. "
            f"Available agents: {', '.join(AGENT_SPECS)}"
        ) from exc

    try:
        max_turns = spec["max_turns"]
    except KeyError as exc:
        raise RuntimeError(
            f"Agent {agent_id!r} in profile {ACTIVE_PROFILE_NAME!r} "
            f"does not define max_turns."
        ) from exc

    if not isinstance(max_turns, int) or max_turns <= 0:
        raise RuntimeError(
            f"Invalid max_turns for agent {agent_id!r}: {max_turns!r}"
        )

    return max_turns


AGENT_MAX_TURNS = {
    agent_id: get_agent_max_turns(agent_id)
    for agent_id in AGENT_SPECS
}

# ------------------------------------------------------------------
# Prompts (TOML)
# ------------------------------------------------------------------

try:
    PROMPT_FILE_RELATIVE = ACTIVE_PROFILE["prompt_file"]
except KeyError as exc:
    raise RuntimeError(
        f"Profile {ACTIVE_PROFILE_NAME!r} does not define 'prompt_file'."
    ) from exc

PROMPT_FILE = (SOURCE_DIR / PROMPT_FILE_RELATIVE).resolve()
ACTIVE_PROMPTS = PROMPT_FILE_RELATIVE

if PROMPT_FILE.suffix.lower() != ".toml":
    raise RuntimeError(
        f"Prompt file for profile {ACTIVE_PROFILE_NAME!r} must be TOML, "
        f"got: {PROMPT_FILE_RELATIVE!r}"
    )

if not PROMPT_FILE.exists():
    raise RuntimeError(
        f"Prompt file does not exist for profile {ACTIVE_PROFILE_NAME!r}: "
        f"{PROMPT_FILE}"
    )

with PROMPT_FILE.open("rb") as f:
    PROMPTS = tomllib.load(f)


def get_prompt(prompt_name):
    """
    Load one prompt string from the active TOML prompt file.
    """
    try:
        prompt = PROMPTS[prompt_name]
    except KeyError as exc:
        raise RuntimeError(
            f"Prompt {prompt_name!r} was requested by profile "
            f"{ACTIVE_PROFILE_NAME!r}, but it does not exist in "
            f"{PROMPT_FILE_RELATIVE!r}"
        ) from exc

    if not isinstance(prompt, str):
        raise RuntimeError(
            f"Prompt {prompt_name!r} in {PROMPT_FILE_RELATIVE!r} "
            f"must be a string, got {type(prompt).__name__}"
        )

    return prompt


def get_agent_prompt(agent_id):
    """
    Return the prompt configured for one active agent.
    """
    try:
        spec = AGENT_SPECS[agent_id]
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown active agent {agent_id!r}. "
            f"Available agents: {', '.join(AGENT_SPECS)}"
        ) from exc

    return get_prompt(spec["prompt"])


AGENT_PROMPTS = {
    agent_id: get_agent_prompt(agent_id)
    for agent_id in AGENT_SPECS
}

try:
    ORCHESTRATOR_PROMPT_NAME = ACTIVE_PROFILE["orchestrator"]["prompt"]
    INITIAL_PROMPT_NAME = ACTIVE_PROFILE["initial_prompt"]
except KeyError as exc:
    raise RuntimeError(
        f"Profile {ACTIVE_PROFILE_NAME!r} is missing an orchestrator "
        f"or initial prompt configuration."
    ) from exc

ORCHESTRATOR_INSTRUCTIONS = get_prompt(ORCHESTRATOR_PROMPT_NAME)
INITIAL_EXPERIMENT_PROMPT = get_prompt(INITIAL_PROMPT_NAME)


# ------------------------------------------------------------------
# Backward-compatible convenience aliases
# ------------------------------------------------------------------

BUILDER_INSTRUCTIONS = AGENT_PROMPTS.get("builder")
IMPLEMENTER_INSTRUCTIONS = AGENT_PROMPTS.get("implementer")
CRITIC_INSTRUCTIONS = AGENT_PROMPTS.get("critic")


# ------------------------------------------------------------------
# Agent/profile helpers
# ------------------------------------------------------------------

def get_agents_by_role(role):
    """
    Return active agent specifications matching a role.
    """
    return [
        spec
        for spec in ACTIVE_AGENTS
        if spec["role"] == role
    ]


def get_agent_spec(agent_id):
    """
    Return the complete configuration entry for one active agent.
    """
    try:
        return AGENT_SPECS[agent_id]
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown active agent {agent_id!r}. "
            f"Available agents: {', '.join(AGENT_SPECS)}"
        ) from exc


# ------------------------------------------------------------------
# Existing ABCA paths
# ------------------------------------------------------------------

ABCA_DIR = (BASE_DIR / "abca").resolve()
INPUT_DATA_DIR = (BASE_DIR / "input_data").resolve()
ANALYSIS_DIR = (BASE_DIR / "analysis_workspace").resolve()

PLUGIN_NAME = "discovered_swimming"
PLUGIN_DIR = (ABCA_DIR / "plugins" / PLUGIN_NAME).resolve()
REGISTRY_DIR = (ABCA_DIR / "plugin_registry").resolve()


# ------------------------------------------------------------------
# Python environments
# ------------------------------------------------------------------

AGENTS_PYTHON = (
    BASE_DIR
    / "python_venvs"
    / "agents"
    / "bin"
    / "python"
).resolve()

ANALYSIS_PYTHON_PREFIX = (
    BASE_DIR
    / "python_venvs"
    / "analysis"
).resolve()

# CAUTION: do not call .resolve() here.
# bin/python is a symlink; resolving it would replace the virtualenv
# interpreter path with the underlying system Python path and break
# virtualenv detection inside the Bubblewrap sandbox.
ANALYSIS_PYTHON = (
    ANALYSIS_PYTHON_PREFIX
    / "bin"
    / "python"
)
