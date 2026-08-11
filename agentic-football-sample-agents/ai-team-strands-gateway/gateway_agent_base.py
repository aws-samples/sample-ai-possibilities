"""Unified AgentCore Memory and Gateway agent factory for soccer roles."""

import os

from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient


def _create_gateway_transport():
    """Build a Streamable HTTP transport for the existing AgentCore Gateway."""
    gateway_url = os.environ.get("GATEWAY_URL")
    if not gateway_url:
        raise RuntimeError("GATEWAY_URL environment variable is required")

    headers = {}
    access_token = os.environ.get("GATEWAY_ACCESS_TOKEN")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return streamablehttp_client(gateway_url, headers=headers)


def create_gateway_agent(
    system_prompt: str,
    player_id: int,
    position_label: str,
    model_id: str = "us.amazon.nova-micro-v1:0",
) -> tuple[Agent, MCPClient]:
    """Create a role agent with the existing Gateway tools and Memory resource."""
    memory_id = os.environ.get("MEMORY_ID")
    if not memory_id:
        raise RuntimeError("MEMORY_ID environment variable is required")

    team_id = os.environ.get("TEAM_ID", "kasia-rook")
    # ponytail: The game payload has no match ID, so a role retains its own team-scoped
    # history. Add matchId to the payload and use it here to isolate memory per match.
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=f"team-{team_id}-{position_label.lower()}",
            actor_id=f"{team_id}-{position_label.lower()}",
        ),
        region_name=os.environ.get("AWS_DEFAULT_REGION"),
    )

    mcp_client = MCPClient(_create_gateway_transport)
    with mcp_client:
        tools = mcp_client.list_tools_sync()

    return (
        Agent(
            model=BedrockModel(model_id=model_id),
            system_prompt=system_prompt,
            tools=tools,
            session_manager=session_manager,
        ),
        mcp_client,
    )
