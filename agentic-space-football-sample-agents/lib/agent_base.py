"""Base agent factory for Space Football policy agents.

Mirrors the soccer factory's shape (Strands Agent + AgentCore @app.entrypoint + 3-layer
fallback) but for space football's MANAGER model: one standing-policy command per ~2s cycle, not
per-tick moves. Fallback layers, best → worst:
  1. LLM response → parse ONE valid command
  2. rule-based opening policy for this cycle (fallback.opening_commands)
  3. last-resort safe role affirmation
"""

import json
from strands import Agent
from strands.models import BedrockModel

from parsing import parse_command
from state import summarize_state
import fallback as fb


def create_agent(system_prompt: str, model_id: str = "us.amazon.nova-micro-v1:0") -> Agent:
    """A Strands Agent with the space football starter system prompt."""
    return Agent(model=BedrockModel(model_id=model_id), system_prompt=system_prompt)


def create_invoke_handler(app, agent: Agent, my_agent_id: str, role_label: str):
    """Register the AgentCore @app.entrypoint. Payload carries the /status game state + this
    agent's teamCode; the reply is exactly ONE space football command as JSON."""
    log = app.logger
    cycle = {"n": 0}   # per-agent decision-cycle counter drives the opening sequence

    @app.entrypoint
    async def invoke(payload, context):
        n = cycle["n"]
        cycle["n"] += 1
        team_code = "?"
        try:
            data = payload.get("prompt", "{}")
            data = json.loads(data) if isinstance(data, str) else data
            status = data.get("gameState", {}) or {}
            team_code = data.get("teamCode") or data.get("teamId") or "?"

            briefing = summarize_state(status, team_code, my_agent_id, role_label)
            response_text = str(agent(briefing))

            cmd = parse_command(response_text, my_agent_id, team_code)
            if cmd is not None:
                log.info(f"[{role_label}] LLM command: {cmd['commandType']}")
                yield json.dumps([cmd])
                return

            log.warn(f"[{role_label}] LLM parse failed (cycle {n}); using opening fallback. resp={response_text[:160]}")
            yield json.dumps([fb.opening_commands(my_agent_id, team_code, role_label, n)])

        except Exception as e:
            log.error(f"[{role_label}] agent error: {e}")
            try:
                yield json.dumps([fb.opening_commands(my_agent_id, team_code, role_label, n)])
            except Exception:
                yield json.dumps([fb.last_resort(my_agent_id, team_code)])

    return invoke
