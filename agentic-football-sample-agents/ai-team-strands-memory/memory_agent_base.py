"""Memory-aware agent factory for AI soccer position agents.

Extends the shared lib's agent_base with AgentCoreMemorySessionManager
so each agent persists conversation history across game ticks.
"""

import os
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig


def create_memory_agent(
    system_prompt: str,
    player_id: int,
    position_label: str,
    model_id: str = "us.amazon.nova-micro-v1:0",
) -> Agent:
    """Create a Strands Agent backed by AgentCore Memory (STM).

    Required env vars:
      MEMORY_ID  — AgentCore Memory resource ID
      TEAM_ID    — used as actor_id and session_id prefix
    """
    memory_id = os.environ.get("MEMORY_ID")
    team_id = os.environ.get("TEAM_ID", "default-team")

    if not memory_id:
        raise RuntimeError("MEMORY_ID environment variable is required")

    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=f"match-{team_id}-{position_label}",
            actor_id=f"{team_id}-{position_label}",
        ),
        region_name=os.environ.get("AWS_DEFAULT_REGION"),
    )

    model = BedrockModel(model_id=model_id)
    return Agent(
        model=model,
        system_prompt=system_prompt,
        session_manager=session_manager,
    )
