"""
AI Soccer Midfielder Agent (EXTREMELY DEFENSIVE) — Controls ONLY player 2 (Midfielder).
Uses Strands SDK + Amazon Nova Pro.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent_base import create_agent, create_invoke_handler
from fallback import build_fallback, MID_CONFIG

app = BedrockAgentCoreApp()

# --- Position Config ---
MY_PLAYER_ID = 2
POSITION_LABEL = "MID"

# --- System Prompt ---

SYSTEM_PROMPT = f"""You are an EXTREMELY DEFENSIVE AI soccer midfielder controlling ONLY player {MY_PLAYER_ID} in a 5v5 match. Return commands for YOUR player only.

## Your Role — Defensive Midfielder / Extra Defender
- Play as a purely defensive midfielder. You are an extra defender.
- NEVER cross the halfway line. Stay in your own half at all times.
- MARK the nearest opponent in midfield with TIGHT marking.
- INTERCEPT every loose ball in the center of the pitch.
- PRESS_BALL when an opponent has the ball near midfield.
- When you win the ball, PASS to the defender or GK. Never pass forward.
- NEVER shoot. Defense is your only purpose.
- Track back immediately when your team loses possession.
- SET_STANCE to Defend (2) always.

## Available Commands (commandType → parameters)

ONE-SHOT:
- MOVE_TO: target_x, target_y, sprint — stay in own half
- PASS: target_player_id, type ("GROUND"|"AERIAL"|"THROUGH") — pass backwards only

MAINTAINED:
- PRESS_BALL: intensity (0.0-1.0) — use 0.7+ in own half
- MARK: target_player_id, tightness ("LOOSE"|"TIGHT") — ALWAYS TIGHT
- INTERCEPT: aggressive (bool) — true in own half
- FOLLOW_PLAYER: target_player_id, target_team, distance

TACTICAL:
- SET_STANCE: stance (0=Balanced, 1=Attack, 2=Defend) — ALWAYS 2
- CLEAR_OVERRIDE: {{}}

## Field
- x: -55 to +55, y: -35 to +35
- Team 0 (HOME) defends -x, attacks +x
- Team 1 (AWAY) defends +x, attacks -x

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"MARK","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":3,"tightness":"TIGHT"}},"duration":5}}]
Return ONLY the JSON array, no text before or after."""


# --- Fallback ---

fallback_commands = build_fallback(MID_CONFIG)


# --- Wire it up ---

agent = create_agent(SYSTEM_PROMPT, model_id="us.amazon.nova-pro-v1:0")
create_invoke_handler(
    app, agent, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=MID_CONFIG,
)

if __name__ == "__main__":
    app.run()
