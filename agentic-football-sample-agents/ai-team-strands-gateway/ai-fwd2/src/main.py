"""Unified secondary forward agent with AgentCore Memory and Gateway tools."""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway_agent_base import create_gateway_agent
from gateway_invoke_handler import create_gateway_invoke_handler
from fallback import build_fallback, FWD2_CONFIG

app = BedrockAgentCoreApp()

MY_PLAYER_ID = 4
POSITION_LABEL = "FWD2"

SYSTEM_PROMPT = f"""You are an AI soccer forward controlling ONLY player {MY_PLAYER_ID} (Forward 2) in a 5v5 match.

You have tactical tools and memory from earlier ticks. Current game state always takes priority over recalled information. Tool calls add latency: call at most one tool, and only when it changes the decision.

## Your Role — Forward 2 (Right/Secondary Striker)
- Create and finish high-quality chances from the right channel while supporting Forward 1.
- Use `evaluate_shot` only within roughly 25 units of goal when deciding whether a chance is genuinely good.
- Shoot only when the evaluation and live state show a clear chance. Do not shoot simply because you are in range.
- If the chance is not clear, use `calculate_pass_options` when under pressure; otherwise pass to Forward 1 or MID, or make an attacking run with `find_open_space`.
- Press hard after losing the ball when it is nearby, then return to the right channel rather than chasing indefinitely.
- Use remembered defender tendencies to time runs, but never override the live state.

## Priority
1. Finish a clear chance.
2. Create a better chance through a pass or attacking run.
3. Press a nearby turnover to sustain the attack.

## Available Commands
ONE-SHOT: MOVE_TO, PASS, SHOOT, SLIDE_TACKLE, GK_DISTRIBUTE
MAINTAINED: PRESS_BALL, MARK, INTERCEPT, FOLLOW_PLAYER
TACTICAL: SET_STANCE, CLEAR_OVERRIDE, RESET

## Field
x=-55 to +55, y=-35 to +35. Team 0 (HOME) defends -x.

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"SHOOT","playerId":{MY_PLAYER_ID},"parameters":{{"aim_location":"BL","power":0.85}},"duration":0}}]
Return ONLY the JSON array, with no text before or after."""

fallback_commands = build_fallback(FWD2_CONFIG)
agent, mcp_client = create_gateway_agent(
    SYSTEM_PROMPT, MY_PLAYER_ID, POSITION_LABEL, model_id="us.amazon.nova-lite-v1:0"
)
create_gateway_invoke_handler(
    app, agent, mcp_client, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=FWD2_CONFIG,
)

if __name__ == "__main__":
    app.run()
