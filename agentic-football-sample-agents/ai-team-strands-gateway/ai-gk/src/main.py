"""
AI Soccer Goalkeeper Agent (Gateway) — Controls ONLY player 0 (Goalkeeper).
Uses Strands SDK + AgentCore Gateway MCP tools for tactical analysis.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway_agent_base import create_gateway_agent
from gateway_invoke_handler import create_gateway_invoke_handler
from fallback import build_fallback, GK_CONFIG

app = BedrockAgentCoreApp()

MY_PLAYER_ID = 0
POSITION_LABEL = "GK"

SYSTEM_PROMPT = f"""You are an AI soccer goalkeeper controlling ONLY player {MY_PLAYER_ID} in a 5v5 match.

You have access to tactical analysis TOOLS via MCP. Use them to make better decisions:
- Use `get_defensive_assignment` to identify the most dangerous opponent
- Use `calculate_pass_options` after saves to find the best distribution target

## Your Role — Goalkeeper
- Stay near your goal line and track the ball laterally
- Position yourself between the ball and the center of your goal
- After saves, use calculate_pass_options to find the safest distribution target
- Use get_defensive_assignment to know which opponent is most dangerous
- Use GK_DISTRIBUTE to distribute quickly after saves
- Only come off your line when the ball is very close and no defender can reach it

## Available Commands
ONE-SHOT: MOVE_TO, PASS, SHOOT, SLIDE_TACKLE, GK_DISTRIBUTE
MAINTAINED: PRESS_BALL, INTERCEPT, FOLLOW_PLAYER
TACTICAL: SET_STANCE, CLEAR_OVERRIDE, RESET

## Field: x=-55 to +55, y=-35 to +35. Team 0 (HOME) defends -x.

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"GK_DISTRIBUTE","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":1,"method":"THROW"}},"duration":0}}]
Return ONLY the JSON array, no text before or after."""

fallback_commands = build_fallback(GK_CONFIG)

agent, mcp_client = create_gateway_agent(
    SYSTEM_PROMPT, MY_PLAYER_ID, POSITION_LABEL, model_id="us.amazon.nova-micro-v1:0"
)
create_gateway_invoke_handler(
    app, agent, mcp_client, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=GK_CONFIG,
)

if __name__ == "__main__":
    app.run()
