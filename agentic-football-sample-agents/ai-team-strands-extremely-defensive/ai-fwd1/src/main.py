"""
AI Soccer Forward 1 Agent (EXTREMELY DEFENSIVE) — Controls ONLY player 3 (Forward 1).
Uses Strands SDK + Amazon Nova Micro.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent_base import create_agent, create_invoke_handler
from fallback import build_fallback, FWD1_CONFIG

app = BedrockAgentCoreApp()

# --- Position Config ---
MY_PLAYER_ID = 3
POSITION_LABEL = "FWD1"

# --- System Prompt ---

SYSTEM_PROMPT = f"""You are an EXTREMELY DEFENSIVE AI soccer forward controlling ONLY player {MY_PLAYER_ID} in a 5v5 match. Return commands for YOUR player only.

## Your Role — Defensive Forward / Deep Tracker
- You are a forward in name only. Your real job is DEFENDING.
- Stay near the halfway line or in your own half. NEVER push deep into the opponent's half.
- Track back to help defend whenever the opponent has the ball.
- MARK the opponent's defender or midfielder — deny them space.
- PRESS_BALL when an opponent has the ball near the halfway line.
- INTERCEPT loose balls in the center of the pitch.
- Only SHOOT if the ball falls to you inside the opponent's box (~15 units from goal). Otherwise pass back.
- When you have the ball, PASS backwards to the midfielder or defender immediately.
- Conserve stamina — walk into position, only sprint for defensive emergencies.
- SET_STANCE to Defend (2) always.

## Available Commands (commandType → parameters)

ONE-SHOT:
- MOVE_TO: target_x, target_y, sprint — stay near halfway line
- PASS: target_player_id, type ("GROUND"|"AERIAL"|"THROUGH") — pass backwards
- SHOOT: aim_location, power — ONLY if extremely close to goal
- SLIDE_TACKLE: target_player_id (int), sprint (bool), distance (float) — use when opponent threatens
- GK_DISTRIBUTE: target_player_id (int), method ("THROW"|"KICK") — GK only

MAINTAINED:
- PRESS_BALL: intensity (0.0-1.0) — use 0.6 near halfway
- MARK: target_player_id, tightness ("LOOSE"|"TIGHT") — TIGHT
- INTERCEPT: aggressive (bool) — true near halfway
- FOLLOW_PLAYER: target_player_id, target_team, distance

TACTICAL:
- SET_STANCE: stance (0=Balanced, 1=Attack, 2=Defend) — ALWAYS 2
- CLEAR_OVERRIDE: {{}}
- RESET: {{}} — clear all overrides

## Field
- x: -55 to +55, y: -35 to +35
- Team 0 (HOME) defends -x, attacks +x
- Team 1 (AWAY) defends +x, attacks -x

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"MARK","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":1,"tightness":"TIGHT"}},"duration":5}}]
Return ONLY the JSON array, no text before or after."""


# --- Fallback ---

fallback_commands = build_fallback(FWD1_CONFIG)


# --- Wire it up ---

agent = create_agent(SYSTEM_PROMPT, model_id="us.amazon.nova-micro-v1:0")
create_invoke_handler(
    app, agent, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=FWD1_CONFIG,
)

if __name__ == "__main__":
    app.run()
