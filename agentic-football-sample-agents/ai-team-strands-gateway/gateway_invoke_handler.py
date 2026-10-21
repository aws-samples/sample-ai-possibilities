"""Invoke handler for Gateway-enabled agents.

Similar to the shared lib's agent_base.create_invoke_handler, but wraps
the agent call inside the MCPClient context manager so Gateway tools
are available during invocation.
"""

import json
from typing import Callable
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

from agent_base import parse_prompt, team_id_from
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
        # Parsed once, outside the try, so the error handler can reuse it
        # rather than re-parsing and raising a second exception.
        prompt_data = parse_prompt(payload)
        team_id = team_id_from(prompt_data, log, position_label)
        try:
            game_state = prompt_data.get("gameState", {})

            # Honor myPlayers from payload if present, otherwise use configured player ID
            my_players = prompt_data.get("myPlayers", [my_player_id])
            effective_pid = my_players[0] if my_players else my_player_id

            state_summary = summarize_state(
                game_state, team_id, effective_pid, position_label
            )
            log.info(f"{position_label} gateway agent invoked for team {team_id}, controlling player {effective_pid}")

            # Use MCP client context so Gateway tools are available
            with mcp_client:
                response = agent(state_summary)
            response_text = str(response)

            commands = parse_commands(response_text, team_id, effective_pid)

            if commands:
                log.info(f"LLM+tools returned {len(commands)} commands: "
                         f"{[c.get('commandType') for c in commands]}")
                yield json.dumps(commands)
            else:
                log.warn(f"LLM parse failed, using fallback. Response: {response_text[:200]}")
                commands = fallback_fn(game_state, team_id, effective_pid)
                yield json.dumps(commands)

        except Exception as e:
            log.error(f"{position_label} gateway agent error: {e}")
            try:
                # Reuse the payload parsed at entry — re-parsing an
                # already-decoded dict raised TypeError here, which the bare
                # except swallowed, skipping the rule-based fallback.
                my_players = prompt_data.get("myPlayers", [my_player_id])
                effective_pid = my_players[0] if my_players else my_player_id
                commands = fallback_fn(
                    prompt_data.get("gameState", {}), team_id, effective_pid,
                )
                yield json.dumps(commands)
            except Exception as fallback_error:
                log.error(f"{position_label} gateway fallback also failed: {fallback_error}")
                cmd = dict(last_resort)
                cmd["teamId"] = team_id
                yield json.dumps([cmd])

    return invoke
