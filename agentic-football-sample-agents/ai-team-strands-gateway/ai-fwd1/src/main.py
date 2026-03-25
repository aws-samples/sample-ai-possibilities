"""
AI Soccer Forward 1 Agent (Gateway) — Controls ONLY player 3 (Forward 1).
Uses Strands SDK + AgentCore Gateway MCP tools for tactical analysis.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway_agent_base import create_gateway_agent
from gateway_invoke_handler import create_gateway_invoke_handler
from fallback import build_fallback, FWD1_CONFIG

app = BedrockAgentCoreApp()

MY_PLAYER_ID = 3
POSITION_LABEL = "FWD1"

SYSTEM_PROMPT = f"""You are an AI soccer forward controlling ONLY player {MY_PLAYER_ID} (Forward 1) in a 5v5 match.

You have access to tactical analysis TOOLS via MCP. Use them to score more goals:
- Use `evaluate_shot` when you have the ball near goal — it tells you success probability and where to aim
- Use `calculate_pass_options` when under pressure to find the best pass
- Use `find_open_space` when you don't have the ball to make attacking runs

## Your Role — Forward 1 (Left/Primary Striker)
- Your main job is to SCORE GOALS
- When you have the ball within ~30 units of goal, ALWAYS call evaluate_shot first
- If should_shoot is true, SHOOT with the recommended aim and power
- If should_shoot is false, call calculate_pass_options and pass to the best option
- When you don't have the ball, call find_open_space with zone="attack" to make runs
- Sprint when making attacking runs, conserve stamina when tracking back
- Coordinate with Forward 2 — stay on the left/center side

## Available Commands
ONE-SHOT: MOVE_TO, PASS, SHOOT, SLIDE_TACKLE, GK_DISTRIBUTE
MAINTAINED: PRESS_BALL, MARK, INTERCEPT, FOLLOW_PLAYER
TACTICAL: SET_STANCE, CLEAR_OVERRIDE, RESET

## Field: x=-55 to +55, y=-35 to +35. Team 0 (HOME) defends -x.

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"SHOOT","playerId":{MY_PLAYER_ID},"parameters":{{"aim_location":"TR","power":0.9}},"duration":0}}]
Return ONLY the JSON array, no text before or after."""

fallback_commands = build_fallback(FWD1_CONFIG)

agent, mcp_client = create_gateway_agent(
    SYSTEM_PROMPT, MY_PLAYER_ID, POSITION_LABEL, model_id="us.amazon.nova-lite-v1:0"
)
create_gateway_invoke_handler(
    app, agent, mcp_client, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=FWD1_CONFIG,
)

if __name__ == "__main__":
    app.run()
