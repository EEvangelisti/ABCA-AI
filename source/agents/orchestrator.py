from agents import Agent

import source.config as config


def make_orchestrator(team):
    """
    Create the Orchestrator from a dictionary of specialist Agents.

    Every active specialist is exposed to the Orchestrator as an agent-tool.
    Team topology, specialist descriptions, prompts and models are controlled
    by configuration rather than hard-coded here.
    """
    expected_ids = set(config.AGENT_SPECS)
    received_ids = set(team)

    missing = expected_ids - received_ids
    extra = received_ids - expected_ids

    if missing or extra:
        details = []

        if missing:
            details.append(f"missing={sorted(missing)}")

        if extra:
            details.append(f"extra={sorted(extra)}")

        raise RuntimeError(
            "Team does not match the active experiment profile: "
            + ", ".join(details)
        )

    specialist_tools = []

    for agent_spec in config.ACTIVE_AGENTS:
        agent_id = agent_spec["id"]
        specialist = team[agent_id]

        specialist_tools.append(
            specialist.as_tool(
                tool_name=agent_id,
                tool_description=config.agent_tool_description(agent_spec),
                max_turns=config.get_agent_max_turns(agent_id),
            )
        )

    return Agent(
        name=f"ABCA Orchestrator [{config.ACTIVE_PROFILE_NAME}]",
        model=config.ORCHESTRATOR_MODEL,
        instructions=config.ORCHESTRATOR_INSTRUCTIONS,
        tools=specialist_tools,
    )
