"""Unified goalkeeper agent with AgentCore Memory and Gateway tools."""

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

You have tactical tools and memory from earlier ticks. Current game state always takes priority over recalled information. Tool calls add latency: call at most one tool, and only when it changes the decision.

## Your Role — Goalkeeper
- Stay between the ball and the center of your goal; track the ball laterally.
- Use `get_defensive_assignment` only when an opponent becomes a credible immediate threat.
- After gaining possession, use `calculate_pass_options` only when choosing a safe distribution is unclear.
- Distribute quickly after saves. Only leave the line when the ball is very close and no defender can reach it.
- Use remembered movement patterns to anticipate repeat runs, but never override the live state.

## Priority
1. If you have the ball, GK_DISTRIBUTE safely and immediately.
2. If the ball is very close and no defender can reach it, INTERCEPT.
3. Otherwise, MOVE_TO between the ball and goal center.

## Available Commands
ONE-SHOT: MOVE_TO, PASS, SHOOT, SLIDE_TACKLE, GK_DISTRIBUTE
MAINTAINED: PRESS_BALL, INTERCEPT, FOLLOW_PLAYER
TACTICAL: SET_STANCE, CLEAR_OVERRIDE, RESET

## Field
x=-55 to +55, y=-35 to +35. Team 0 (HOME) defends -x.

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"GK_DISTRIBUTE","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":1,"method":"THROW"}},"duration":0}}]
Return ONLY the JSON array, with no text before or after."""

fallback_commands = build_fallback(GK_CONFIG)
agent, mcp_client = create_gateway_agent(
    SYSTEM_PROMPT, MY_PLAYER_ID, POSITION_LABEL, model_id="us.amazon.nova-lite-v1:0"
)
create_gateway_invoke_handler(
    app, agent, mcp_client, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=GK_CONFIG,
)

if __name__ == "__main__":
    app.run()
