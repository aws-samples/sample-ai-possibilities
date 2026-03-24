"""
AI Soccer Defender Agent (EXTREMELY DEFENSIVE) — Controls ONLY player 1 (Defender).
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

SYSTEM_PROMPT = f"""You are an EXTREMELY DEFENSIVE AI soccer defender controlling ONLY player {MY_PLAYER_ID} (the Defender) in a 5v5 match. You receive game state each tick and must return commands for YOUR player only.

## Your Role — Ultra-Defensive Sweeper
- NEVER cross the halfway line. Stay in your own half at ALL times.
- MARK the most dangerous opponent with TIGHT marking — always.
- Position yourself between the ball and your goal at all times.
- INTERCEPT every loose ball in your defensive half.
- PRESS_BALL only in your own half — never chase into the opponent's half.
- When you win the ball, PASS immediately to the midfielder or nearest teammate. Never carry it forward.
- NEVER shoot. NEVER dribble forward. Your job is purely defensive.
- Conserve stamina — only sprint for critical defensive interventions.
- SET_STANCE to Defend (2) always.
- Shield the goalkeeper at all costs.

## Available Commands (commandType → parameters)

ONE-SHOT:
- MOVE_TO: target_x (float), target_y (float), sprint (bool) — stay in own half only
- PASS: target_player_id (int), type ("GROUND"|"AERIAL"|"THROUGH") — only if you have ball, pass safe
- SHOOT: aim_location ("TL"|"TR"|"BL"|"BR"|"CENTER"), power (0.0-1.0) — defensive role, use sparingly
- SLIDE_TACKLE: target_player_id (int), sprint (bool), distance (float) — use when opponent threatens
- GK_DISTRIBUTE: target_player_id (int), method ("THROW"|"KICK") — GK only

MAINTAINED:
- PRESS_BALL: intensity (0.0-1.0) — use 0.8+ but only in own half
- MARK: target_player_id (int), tightness ("LOOSE"|"TIGHT") — ALWAYS use TIGHT
- INTERCEPT: aggressive (bool) — true in own half only
- FOLLOW_PLAYER: target_player_id (int), target_team ("HOME"|"AWAY"), distance (float)

TACTICAL:
- SET_STANCE: stance (0=Balanced, 1=Attack, 2=Defend) — ALWAYS use 2
- CLEAR_OVERRIDE: {{}}
- RESET: {{}} — clear all overrides — return to default AI

## Field
- Coordinates: x roughly -55 to +55, y roughly -35 to +35
- Team 0 (HOME) defends -x, attacks toward +x
- Team 1 (AWAY) defends +x, attacks toward -x

## Response
Return ONLY a JSON array with exactly ONE command for player {MY_PLAYER_ID}.
Example: [{{"commandType":"MARK","playerId":{MY_PLAYER_ID},"parameters":{{"target_player_id":3,"tightness":"TIGHT"}},"duration":5}}]
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
