"""Gateway-aware agent factory for AI soccer position agents (CDK/npm-CLI flow).

Sibling of gateway_agent_base.py with the same public API, for deployments
made with the npm AgentCore CLI (`python deploy_all.py`). There the gateway
and its Lambda tools are declared in agentcore/agentcore.json
("tactical-tools") and created by the CDK app, which injects the gateway
endpoint into every runtime as AGENTCORE_GATEWAY_TACTICAL_TOOLS_URL — no
GATEWAY_URL env var is passed at deploy time.

deploy_all.py stages this file into each agent directory AS
gateway_agent_base.py, so src/main.py imports it unchanged. The original
gateway_agent_base.py remains the module staged by the legacy deploy-all.sh
flow. gateway_invoke_handler.py is flow-agnostic (it reads no environment
variables) and is shared by both flows.
"""

import os
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from strands.tools.mcp.mcp_agent_tool import MCPAgentTool
from mcp.client.streamable_http import streamablehttp_client


def _create_gateway_transport():
    """Build a Streamable HTTP transport pointing at the AgentCore Gateway.

    Supports both NONE auth (no token) and token-based auth.
    """
    gateway_url = os.environ.get("AGENTCORE_GATEWAY_TACTICAL_TOOLS_URL")
    if not gateway_url:
        raise RuntimeError(
            "AGENTCORE_GATEWAY_TACTICAL_TOOLS_URL environment variable is "
            "required. It is injected automatically when the agent is deployed "
            "via `python deploy_all.py` with the tactical-tools gateway "
            "declared in agentcore/agentcore.json."
        )

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
      AGENTCORE_GATEWAY_TACTICAL_TOOLS_URL — injected by the CDK stack for
                                             the "tactical-tools" gateway
      GATEWAY_ACCESS_TOKEN                 — Bearer token (optional, NONE auth)

    Returns:
      (agent, mcp_client) — caller must use `with mcp_client:` context manager
      when invoking the agent so tools remain available.
    """
    mcp_client = MCPClient(_create_gateway_transport)
    model = BedrockModel(model_id=model_id)

    # Fetch tool definitions inside the context so the connection is active.
    with mcp_client:
        # Nova rejects hyphens in tool names; rename for the model only.
        tools = [MCPAgentTool(t.mcp_tool, t.mcp_client, name_override=t.tool_name.replace("-", "_"))
                 for t in mcp_client.list_tools_sync()]

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
    )

    return agent, mcp_client
