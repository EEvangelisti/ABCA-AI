import json
import argparse
import re
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from pathlib import Path


# ------------------------------------------------------------------
# Base paths
# ------------------------------------------------------------------

SOURCE_DIR = Path(__file__).resolve().parent
BASE_DIR = SOURCE_DIR.parent

def _arguments():
    parser = argparse.ArgumentParser(description="Run an ABCA agent team")
    parser.add_argument("--team", required=True, help="Load teams/NAME.json")
    parser.add_argument("--teams-dir", type=Path, default=SOURCE_DIR / "teams")
    parser.add_argument("--profile", help="Select a profile when the team JSON defines several")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=JSON",
                        help="Override a JSON value by dotted key, e.g. runtime.max_turns=20; repeatable")
    for name in ("max_turns", "command_timeout", "analysis_timeout", "max_output",
                 "max_file_size", "max_analysis_script_size", "max_analysis_read"):
        parser.add_argument("--" + name.replace("_", "-"), type=int)
    for name in ("abca_dir", "input_data_dir", "analysis_dir", "plugin_dir",
                 "registry_dir", "agents_python", "analysis_python_prefix", 
                 "analysis_python", "opam_prefix"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path)
    parser.add_argument("--plugin-name")
    return parser.parse_args()


ARGS = _arguments()
if ARGS.team and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", ARGS.team):
    raise SystemExit("--team must be a simple name (letters, digits, _ or -)")
TEAMS_DIR = ARGS.teams_dir.expanduser().resolve()
CONFIG_FILE = (TEAMS_DIR / f"{ARGS.team}.json").expanduser().resolve()


# ------------------------------------------------------------------
# Load experiment configuration
# ------------------------------------------------------------------

with CONFIG_FILE.open("r", encoding="utf-8") as f:
    EXPERIMENT_CONFIG = json.load(f)

for assignment in ARGS.set:
    key, separator, raw = assignment.partition("=")
    if not separator or not key:
        raise SystemExit(f"Invalid --set {assignment!r}; expected KEY=JSON")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in --set {assignment!r}: {exc}") from exc
    target = EXPERIMENT_CONFIG
    parts = key.split(".")
    try:
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        last = parts[-1]
        index = int(last) if isinstance(target, list) else last
        if (index not in range(len(target)) if isinstance(target, list)
                else index not in target):
            raise KeyError(last)
        target[index] = value
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise SystemExit(f"Unknown --set key: {key}") from exc

for _name in ("max_turns", "command_timeout", "analysis_timeout", "max_output",
              "max_file_size", "max_analysis_script_size", "max_analysis_read"):
    if getattr(ARGS, _name) is not None:
        EXPERIMENT_CONFIG["runtime"][_name] = getattr(ARGS, _name)


# ------------------------------------------------------------------
# Active profile
# ------------------------------------------------------------------

try:
    PROFILES = EXPERIMENT_CONFIG["profiles"]
except KeyError as exc:
    raise RuntimeError(f"Team configuration {CONFIG_FILE} does not define 'profiles'.") from exc

if not isinstance(PROFILES, dict) or not PROFILES:
    raise RuntimeError(f"Team configuration {CONFIG_FILE} must define at least one profile.")

if ARGS.profile is not None:
    ACTIVE_PROFILE_NAME = ARGS.profile
elif len(PROFILES) == 1:
    ACTIVE_PROFILE_NAME = next(iter(PROFILES))
else:
    raise RuntimeError(
        f"Team {ARGS.team!r} defines several profiles "
        f"({', '.join(PROFILES)}); select one with --profile NAME."
    )

try:
    ACTIVE_PROFILE = PROFILES[ACTIVE_PROFILE_NAME]
except KeyError as exc:
    raise RuntimeError(
        f"Unknown profile {ACTIVE_PROFILE_NAME!r} for team {ARGS.team!r}. "
        f"Available profiles: {', '.join(PROFILES)}"
    ) from exc

# Optional descriptive workflow name; default to the selected profile.
WORKFLOW = ACTIVE_PROFILE.get("workflow", ACTIVE_PROFILE_NAME)
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
    PROMPT_FILE_RELATIVE = ACTIVE_PROFILE["instructions"]
except KeyError as exc:
    raise RuntimeError(
        f"Profile {ACTIVE_PROFILE_NAME!r} does not define 'instructions'."
    ) from exc

PROMPT_FILE = (TEAMS_DIR / PROMPT_FILE_RELATIVE).expanduser().resolve()
ACTIVE_PROMPTS = str(PROMPT_FILE)

if PROMPT_FILE.suffix.lower() != ".toml":
    raise RuntimeError(
        f"Instructions file for profile {ACTIVE_PROFILE_NAME!r} must be TOML, "
        f"got: {PROMPT_FILE_RELATIVE!r}"
    )

if not PROMPT_FILE.exists():
    raise RuntimeError(
        f"Instructions file does not exist for profile {ACTIVE_PROFILE_NAME!r}: "
        f"{PROMPT_FILE}"
    )

with PROMPT_FILE.open("rb") as f:
    PROMPTS = tomllib.load(f)

def get_prompt(prompt_name):
    """
    Load one prompt string from the active TOML instructions file.
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

ABCA_DIR = (ARGS.abca_dir or BASE_DIR / "runs" / "input_data" / "ABCA").expanduser().resolve()
INPUT_DATA_DIR = (ARGS.input_data_dir or BASE_DIR / "runs" / "input_data").expanduser().resolve()
ANALYSIS_DIR = (ARGS.analysis_dir or BASE_DIR / "runs" / "analysis_workspace").expanduser().resolve()

PLUGIN_NAME = ARGS.plugin_name or "refined_zoospore_model"
PLUGIN_DIR = (ARGS.plugin_dir or ABCA_DIR / "plugins" / PLUGIN_NAME).expanduser().resolve()
REGISTRY_DIR = (ARGS.registry_dir or ABCA_DIR / "plugin_registry").expanduser().resolve()


# ------------------------------------------------------------------
# Python environments
# ------------------------------------------------------------------

AGENTS_PYTHON = (ARGS.agents_python or (
    BASE_DIR
    / "python_venvs"
    / "agents"
    / "bin"
    / "python"
)).expanduser().resolve()

ANALYSIS_PYTHON_PREFIX = (ARGS.analysis_python_prefix or (
    BASE_DIR
    / "python_venvs"
    / "analysis"
)).expanduser().resolve()

# CAUTION: do not call .resolve() here.
# bin/python is a symlink; resolving it would replace the virtualenv
# interpreter path with the underlying system Python path and break
# virtualenv detection inside the Bubblewrap sandbox.
ANALYSIS_PYTHON = ARGS.analysis_python or (
    ANALYSIS_PYTHON_PREFIX
    / "bin"
    / "python"
)
ANALYSIS_PYTHON = ANALYSIS_PYTHON.expanduser().absolute()

# ------------------------------------------------------------------
# OCaml / OPAM environment
# ------------------------------------------------------------------

if ARGS.opam_prefix is not None:
    OPAM_PREFIX = ARGS.opam_prefix.expanduser().resolve()
else:
    _default_opam_prefix = (Path.home() / ".opam" / "default").resolve()
    OPAM_PREFIX = _default_opam_prefix if _default_opam_prefix.exists() else None
