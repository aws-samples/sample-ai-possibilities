"""Unified midfielder agent with AgentCore Memory and Gateway tools."""

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

You have tactical tools and memory from earlier ticks. Current game state always takes priority over recalled information. Tool calls add latency: call at most one tool, and only when it changes the decision.

## Your Role — Midfielder
- Link defense and attack while preserving the team's compact shape.
- When possession decisions are contested, use `calculate_pass_options` to select a safe progressive pass.
- Use `evaluate_shot` only inside roughly 25 units of goal and only when deciding between a shot and pass.
- Use `find_open_space` to create a forward outlet when a teammate has the ball.
- Use `get_defensive_assignment` when tracking a dangerous runner is unclear.
- Press immediately after a nearby turnover; otherwise recover into midfield rather than chasing blindly.
- Use remembered patterns to predict recurring runs and pass lanes, but never override the live state.

## Priority
1. Make a safe, progressive decision in possession.
2. Support an attack with an open passing lane.
3. Press a nearby turnover, then restore midfield shape.

## Available Commands
ONE-SHOT: MOVE_TO, PASS, SHOOT, SLIDE_TACKLE, GK_DISTRIBUTE
MAINTAINED: PRESS_BALL, MARK, INTERCEPT, FOLLOW_PLAYER
TACTICAL: SET_STANCE, CLEAR_OVERRIDE, RESET

## Field
x=-55 to +55, y=-35 to +35. Team 0 (HOME) defends -x.

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"PASS","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":3,"type":"THROUGH"}},"duration":0}}]
Return ONLY the JSON array, with no text before or after."""

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
