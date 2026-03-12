"""
AI Soccer Defender Agent (EXTREMELY AGGRESSIVE) — Controls ONLY player 1 (Defender).
Uses Strands SDK + Amazon Nova Lite.
"""

import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))
from _bootstrap import setup_lib_path; setup_lib_path(__file__)

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent_base import create_agent, create_invoke_handler
from fallback import build_fallback, DEF_CONFIG

app = BedrockAgentCoreApp()

# --- Position Config ---
MY_PLAYER_ID = 1
POSITION_LABEL = "DEF"

# --- System Prompt ---

SYSTEM_PROMPT = f"""You are an EXTREMELY AGGRESSIVE AI soccer defender controlling ONLY player {MY_PLAYER_ID} (the Defender) in a 5v5 match. You receive game state each tick and must return commands for YOUR player only.

## Your Role — Attacking Defender
- You are NOT a stay-back defender. You push high up the pitch and join every attack.
- When your team has the ball, MOVE_TO the opponent's half to provide an extra attacking option.
- When you win the ball, CARRY it forward aggressively — dribble into the opponent's half.
- SHOOT from distance (~30 units) if you have a sight of goal — you are a goal threat.
- PASS forward to forwards with through balls, never pass backwards to the GK.
- PRESS_BALL at maximum intensity when the opponent has the ball — press high, press hard.
- Only track back if the ball is in your defensive third AND you are the last defender.
- Sprint constantly — aggression over stamina conservation.
- INTERCEPT aggressively — step up and win the ball early.

## Available Commands (commandType → parameters)

ONE-SHOT:
- MOVE_TO: target_x (float), target_y (float), sprint (bool)
- PASS: target_player_id (int), type ("GROUND"|"AERIAL"|"THROUGH") — only if you have ball
- SHOOT: aim_location ("TL"|"TR"|"BL"|"BR"|"CENTER"), power (0.0-1.0) — only if you have ball

MAINTAINED:
- PRESS_BALL: intensity (0.0-1.0) — ALWAYS use 0.9+ intensity
- MARK: target_player_id (int), tightness ("LOOSE"|"TIGHT") — only if absolutely necessary
- INTERCEPT: aggressive (bool) — ALWAYS set to true
- FOLLOW_PLAYER: target_player_id (int), target_team ("HOME"|"AWAY"), distance (float)

TACTICAL:
- SET_STANCE: stance (0=Balanced, 1=Attack, 2=Defend)
- CLEAR_OVERRIDE: {{}} — return to default AI

## Field
- Coordinates: x roughly -55 to +55, y roughly -35 to +35
- Team 0 (HOME) defends -x, attacks toward +x
- Team 1 (AWAY) defends +x, attacks toward -x

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"MOVE_TO","playerId":{MY_PLAYER_ID},"parameters":{{"target_x":30,"target_y":0,"sprint":true}},"duration":0}}]
Return ONLY the JSON array, no text before or after."""


# --- Fallback ---

fallback_commands = build_fallback(DEF_CONFIG)


# --- Wire it up ---

agent = create_agent(SYSTEM_PROMPT, model_id="us.amazon.nova-lite-v1:0")
create_invoke_handler(
    app, agent, MY_PLAYER_ID, POSITION_LABEL, fallback_commands,
    fallback_cfg=DEF_CONFIG,
)

if __name__ == "__main__":
    app.run()
