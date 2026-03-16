"""Invoke handler for Gateway-enabled agents.

Similar to the shared lib's agent_base.create_invoke_handler, but wraps
the agent call inside the MCPClient context manager so Gateway tools
are available during invocation.
"""

import json
from typing import Callable
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

from parsing import parse_commands
from state import summarize_state
from fallback import FallbackConfig, build_last_resort


def create_gateway_invoke_handler(
    app,
    agent: Agent,
    mcp_client: MCPClient,
    my_player_id: int,
    position_label: str,
    fallback_fn: Callable[[dict, int, int], list[dict]],
    fallback_cfg: FallbackConfig,
):
    """Register the @app.entrypoint handler with Gateway MCP context."""
    log = app.logger
    last_resort = build_last_resort(fallback_cfg, my_player_id)

    @app.entrypoint
    async def invoke(payload, context):
        try:
            prompt = payload.get("prompt", "{}")
            prompt_data = json.loads(prompt) if isinstance(prompt, str) else prompt

            game_state = prompt_data.get("gameState", {})
            team_id = prompt_data.get("teamId", 0)

            state_summary = summarize_state(
                game_state, team_id, my_player_id, position_label
            )
            log.info(f"{position_label} gateway agent invoked for team {team_id}")

            # Use MCP client context so Gateway tools are available
            with mcp_client:
                response = agent(state_summary)
            response_text = str(response)

            commands = parse_commands(response_text, team_id, my_player_id)

            if commands:
                log.info(f"LLM+tools returned {len(commands)} commands: "
                         f"{[c.get('commandType') for c in commands]}")
                yield json.dumps(commands)
            else:
                log.warn(f"LLM parse failed, using fallback. Response: {response_text[:200]}")
                commands = fallback_fn(game_state, team_id, my_player_id)
                yield json.dumps(commands)

        except Exception as e:
            log.error(f"{position_label} gateway agent error: {e}")
            try:
                prompt_data = json.loads(payload.get("prompt", "{}"))
                team_id = prompt_data.get("teamId", 0)
                commands = fallback_fn(
                    prompt_data.get("gameState", {}), team_id, my_player_id,
                )
                yield json.dumps(commands)
            except Exception:
                cmd = dict(last_resort)
                cmd["teamId"] = 0
                yield json.dumps([cmd])

    return invoke
