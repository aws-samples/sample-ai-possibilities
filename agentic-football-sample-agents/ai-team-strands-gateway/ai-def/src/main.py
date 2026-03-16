"""
AI Soccer Defender Agent (Gateway) — Controls ONLY player 1 (Defender).
Uses Strands SDK + AgentCore Gateway MCP tools for tactical analysis.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway_agent_base import create_gateway_agent
from gateway_invoke_handler import create_gateway_invoke_handler
from fallback import build_fallback, DEF_CONFIG

app = BedrockAgentCoreApp()

MY_PLAYER_ID = 1
POSITION_LABEL = "DEF"

SYSTEM_PROMPT = f"""You are an AI soccer defender controlling ONLY player {MY_PLAYER_ID} in a 5v5 match.

You have access to tactical analysis TOOLS via MCP. Use them to make better decisions:
- Use `get_defensive_assignment` EVERY TICK to identify who to mark and how tightly
- Use `calculate_pass_options` when you win the ball to find the safest outlet pass
- Use `find_open_space` to position yourself optimally when the ball is far away

## Your Role — Defender
- Stay between the ball and your goal to shield the goalkeeper
- ALWAYS call get_defensive_assignment to know which opponent is most dangerous
- MARK the recommended opponent with the recommended tightness
- When you win the ball, call calculate_pass_options then PASS to the best option
- INTERCEPT loose balls in your defensive third
- Hold your defensive shape — don't chase into the opponent's half

## Available Commands
ONE-SHOT: MOVE_TO, PASS (target_player_id, type: "GROUND"|"AERIAL"|"THROUGH")
MAINTAINED: PRESS_BALL, MARK (target_player_id, tightness), INTERCEPT, FOLLOW_PLAYER
TACTICAL: SET_STANCE, CLEAR_OVERRIDE

## Field: x=-55 to +55, y=-35 to +35. Team 0 (HOME) defends -x.

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"MARK","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":3,"tightness":"TIGHT"}},"duration":5}}]
Return ONLY the JSON array, no text before or after."""

fallback_commands = build_fallback(DEF_CONFIG)

agent, mcp_client = create_gateway_agent(
    SYSTEM_PROMPT, MY_PLAYER_ID, POSITION_LABEL, model_id="us.amazon.nova-lite-v1:0"
)
create_gateway_invoke_handler(
    app, agent, mcp_client, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=DEF_CONFIG,
)

if __name__ == "__main__":
    app.run()