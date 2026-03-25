"""Gateway-aware agent factory for AI soccer position agents.

Creates a Strands Agent that connects to an AgentCore Gateway via MCP,
giving each player access to tactical analysis tools (pass options,
open space finder, shot evaluator, defensive assignments).
"""

import os
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client


def _create_gateway_transport():
    """Build a Streamable HTTP transport pointing at the AgentCore Gateway.

    Supports both NONE auth (no token) and token-based auth.
    """
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
    """Create a Strands Agent with MCP tools from AgentCore Gateway.

    Tools are fetched inside the MCPClient context so the connection is
    active when list_tools_sync() is called.

    Required env vars:
      GATEWAY_URL          — AgentCore Gateway MCP endpoint
      GATEWAY_ACCESS_TOKEN — Bearer token for Gateway auth (optional, NONE auth)

    Returns:
      (agent, mcp_client) — caller must use `with mcp_client:` context manager
      when invoking the agent so tools remain available.
    """
    mcp_client = MCPClient(_create_gateway_transport)
    model = BedrockModel(
        model_id=model_id,
        temperature=0,
        max_tokens=5000,
    )

    # Fetch tool definitions inside the context so the connection is active.
    with mcp_client:
        tools = mcp_client.list_tools_sync()

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
    )

    return agent, mcp_client
