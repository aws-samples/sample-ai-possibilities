"""Base agent factory for AI soccer position agents."""

import json
from typing import Callable
from strands import Agent
from strands.models import BedrockModel

from parsing import parse_commands
from state import summarize_state
from fallback import FallbackConfig, build_last_resort


def create_agent(system_prompt: str, model_id: str = "us.amazon.nova-micro-v1:0") -> Agent:
    """Create a Strands Agent with the given system prompt."""
    model = BedrockModel(model_id=model_id)
    return Agent(model=model, system_prompt=system_prompt)


def create_invoke_handler(
    app,
    agent: Agent,
    my_player_id: int,
    position_label: str,
    fallback_fn: Callable[[dict, int, int], list[dict]],
    fallback_cfg: FallbackConfig,
):
    """Create and register the @app.entrypoint invoke handler.

    Three layers of error handling, from best to worst:
      1. LLM response → parse into commands
      2. fallback_fn(game_state, team_id, my_player_id) → rule-based commands
      3. last-resort command from fallback_cfg → single safe command
    """
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
            log.info(f"{position_label} agent invoked for team {team_id}, controlling player {my_player_id}")

            response = agent(state_summary)
            response_text = str(response)

            commands = parse_commands(response_text, team_id, my_player_id)

            if commands:
                log.info(f"LLM returned {len(commands)} commands: "
                         f"{[c.get('commandType') for c in commands]}")
                yield json.dumps(commands)
            else:
                log.warn(f"LLM parse failed, using fallback. Response: {response_text[:200]}")
                commands = fallback_fn(game_state, team_id, my_player_id)
                log.info(f"Fallback returned {len(commands)} commands")
                yield json.dumps(commands)

        except Exception as e:
            log.error(f"{position_label} agent error: {e}")
            try:
                prompt_data = json.loads(payload.get("prompt", "{}"))
                team_id = prompt_data.get("teamId", 0)
                commands = fallback_fn(
                    prompt_data.get("gameState", {}),
                    team_id,
                    my_player_id,
                )
                yield json.dumps(commands)
            except Exception:
                cmd = dict(last_resort)
                cmd["teamId"] = 0  # best guess when payload parsing also failed
                yield json.dumps([cmd])

    return invoke
