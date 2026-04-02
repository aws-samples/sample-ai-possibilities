"""
AI Soccer Midfielder Agent (Gateway) — Controls ONLY player 2 (Midfielder).
Uses Strands SDK + AgentCore Gateway MCP tools for tactical analysis.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway_agent_base import create_gateway_agent
from gateway_invoke_handler import create_gateway_invoke_handler
from fallback import build_fallback, MID_CONFIG

app = BedrockAgentCoreApp()

MY_PLAYER_ID = 2
POSITION_LABEL = "MID"

SYSTEM_PROMPT = f"""You are an AI soccer midfielder controlling ONLY player {MY_PLAYER_ID} in a 5v5 match.

You have access to tactical analysis TOOLS via MCP. Use them to make better decisions:
- Use `calculate_pass_options` when you have the ball to find the best pass target
- Use `find_open_space` when you don't have the ball to position yourself for a pass
- Use `evaluate_shot` when within shooting range to decide shoot vs pass
- Use `get_defensive_assignment` when tracking back to know who to pressure

## Your Role — Midfielder
- You are the link between defense and attack — distribute the ball wisely
- When you have the ball, ALWAYS call calculate_pass_options first
- If within ~25 units of goal, call evaluate_shot to decide shoot vs pass
- When a teammate has the ball, call find_open_space to get into position
- When tracking back, call get_defensive_assignment to know who to pressure
- Balance attack and defense — manage stamina carefully

## Available Commands
ONE-SHOT: MOVE_TO, PASS, SHOOT, SLIDE_TACKLE, GK_DISTRIBUTE
MAINTAINED: PRESS_BALL, MARK, INTERCEPT, FOLLOW_PLAYER
TACTICAL: SET_STANCE, CLEAR_OVERRIDE, RESET

## Field: x=-55 to +55, y=-35 to +35. Team 0 (HOME) defends -x.

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"PASS","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":3,"type":"THROUGH"}},"duration":0}}]
Return ONLY the JSON array, no text before or after."""

fallback_commands = build_fallback(MID_CONFIG)

agent, mcp_client = create_gateway_agent(
    SYSTEM_PROMPT, MY_PLAYER_ID, POSITION_LABEL, model_id="us.amazon.nova-pro-v1:0"
)
create_gateway_invoke_handler(
    app, agent, mcp_client, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=MID_CONFIG,
)

if __name__ == "__main__":
    app.run()
