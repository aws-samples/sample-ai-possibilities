"""Agent factory for Cars Edition cars: Strands Agent + AgentCore entrypoint + three-layer fallback.

Payload (from the platform's cars-agent-loop): {"prompt": JSON of {gameState, teamCode, agentId, role,
attackingZ, durationSeconds, coachInstructions}}. Reply: a JSON array of 1-3 relay commands.
"""

import json

from strands import Agent
from strands.models import BedrockModel

import fallback as fb
from parsing import parse_commands
from state import summarize_state


def create_agent(system_prompt: str, model_id: str = "us.amazon.nova-micro-v1:0") -> Agent:
    return Agent(model=BedrockModel(model_id=model_id), system_prompt=system_prompt, callback_handler=None)


def create_invoke_handler(app, agent: Agent, default_agent_id: str, role: str, variant: str = "balanced"):
    log = app.logger
    cycle = {"n": 0}

    @app.entrypoint
    async def invoke(payload, context):
        n = cycle["n"]
        cycle["n"] += 1
        agent_id, team_code, status, attacking_z = default_agent_id, "?", {}, 1
        try:
            data = payload.get("prompt", "{}")
            data = json.loads(data) if isinstance(data, str) else data
            status = data.get("gameState") or {}
            agent_id = data.get("agentId") or default_agent_id
            team_code = data.get("teamCode") or "?"
            attacking_z = 1 if int(data.get("attackingZ", 1)) >= 0 else -1

            briefing = summarize_state(status, team_code, agent_id, role, attacking_z,
                                       data.get("coachInstructions"), data.get("durationSeconds"))
            response_text = str(agent(briefing))

            def on_recovered(raw: str) -> None:
                log.info(f"[{role}] recovered malformed JSON from the model: {raw[:200]}")

            commands = parse_commands(response_text, agent_id, team_code, on_recovered)
            if commands:
                log.info(f"[{role}] LLM commands: {[c['commandType'] for c in commands]}")
                yield json.dumps(commands)
                return
            log.warn(f"[{role}] LLM parse failed (cycle {n}); using fallback. resp={response_text[:160]}")
            yield json.dumps(_fallback(status, agent_id, team_code, role, variant, attacking_z, n))
        except Exception as e:
            log.error(f"[{role}] agent error: {e}")
            try:
                yield json.dumps(_fallback(status, agent_id, team_code, role, variant, attacking_z, n))
            except Exception:
                yield json.dumps([fb.last_resort(agent_id, team_code)])

    return invoke


def _fallback(status, agent_id, team_code, role, variant, attacking_z, cycle) -> list:
    opening = fb.opening_command(agent_id, team_code, variant, cycle)
    moment = fb.moment_command(status, agent_id, team_code, role, attacking_z)
    commands = [c for c in (opening, moment) if c is not None]
    return commands or [fb.last_resort(agent_id, team_code)]
