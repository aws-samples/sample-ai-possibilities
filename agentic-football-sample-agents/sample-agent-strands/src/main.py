"""
AI Soccer Coach Agent — Strands SDK + Amazon Nova Micro.

Receives game state from the agent-loop sidecar, uses LLM to reason about
tactics, and returns per-player commands using the vendor's 11 command types.

This agent serves as:
  1. Integration test for the full game pipeline
  2. Starting point for participants building their own agents

Command types: MOVE_TO, FOLLOW_PLAYER, PASS, SHOOT, MARK, PRESS_BALL,
               INTERCEPT, GK_DISTRIBUTE, SET_STANCE, CLEAR_OVERRIDE, RESET
"""

import json
import re
import math
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
log = app.logger

# --- LLM Setup ---

model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")

SYSTEM_PROMPT = """You are an AI soccer coach controlling a 5v5 team. You receive game state each tick and must return commands for your players as a JSON array.

## Available Commands (commandType → parameters)

ONE-SHOT (auto-clear after execution):
- MOVE_TO: target_x (float), target_y (float), sprint (bool)
- PASS: target_player_id (int), type ("GROUND"|"AERIAL"|"THROUGH") — only if player has ball
- SHOOT: aim_location ("TL"|"TR"|"BL"|"BR"|"CENTER"), power (0.0-1.0) — only if player has ball
- GK_DISTRIBUTE: target_player_id (int), method ("THROW"|"KICK") — goalkeeper only

MAINTAINED (active until cleared or duration expires):
- PRESS_BALL: intensity (0.0-1.0) — pressure ball carrier (>0.5 sprints, >0.3 tackles)
- MARK: target_player_id (int), tightness ("LOOSE"|"TIGHT") — man-mark opponent
- INTERCEPT: aggressive (bool) — predict and intercept the ball
- FOLLOW_PLAYER: target_player_id (int), target_team ("HOME"|"AWAY"), distance (float)

TACTICAL:
- SET_STANCE: stance (0=Balanced, 1=Attack, 2=Defend)
- CLEAR_OVERRIDE: {} — return player to default AI
- RESET: {} — clear all overrides for the team

## Field
- Coordinates: x roughly -55 to +55, y roughly -35 to +35
- Team 0 (HOME) defends -x, attacks toward +x
- Team 1 (AWAY) defends +x, attacks toward -x
- Player 0 is the goalkeeper

## Tactics
- Ball carrier: advance toward goal, PASS to better-positioned teammate, or SHOOT when close
- Without ball (your team has it): MOVE_TO open space to create passing options
- Opponent has ball: nearest player PRESS_BALL, others MARK opponents or INTERCEPT
- Goalkeeper: GK_DISTRIBUTE quickly after saves, otherwise stay back
- Manage stamina: avoid constant sprinting

## Response
Return ONLY a JSON array. One command per player you want to control. Players without commands keep their current behavior.
Example: [{"commandType":"SHOOT","playerId":3,"parameters":{"aim_location":"TR","power":0.85},"duration":0},{"commandType":"PRESS_BALL","playerId":1,"parameters":{"intensity":0.7},"duration":3}]
Return ONLY the JSON array, no text before or after."""

agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)


# --- Game State Summary ---

def summarize_state(game_state: dict, team_id: int) -> str:
    """Build a concise text summary of the game state for the LLM."""
    ball = game_state.get("ball", {})
    ball_pos = ball.get("position", {"x": 0, "y": 0})
    score = game_state.get("score", {})
    game_time = game_state.get("gameTime", 0)
    play_mode = game_state.get("playMode", 0)
    players = game_state.get("players", [])

    my_players = sorted(
        [p for p in players if p.get("teamId") == team_id],
        key=lambda p: p.get("playerId", 0),
    )
    opponents = sorted(
        [p for p in players if p.get("teamId") != team_id],
        key=lambda p: p.get("playerId", 0),
    )

    # Who has the ball?
    possession_id = ball.get("possessionPlayerId")
    if possession_id is not None:
        holder = next((p for p in players if p.get("playerId") == possession_id), None)
        if holder:
            side = "MY" if holder.get("teamId") == team_id else "OPP"
            ball_status = f"{side} player {possession_id}"
        else:
            ball_status = "unknown"
    else:
        ball_status = "free"

    # Opponent goal position
    goal_x = 55 if team_id == 0 else -55

    lines = [
        f"Time: {game_time:.0f}s | Score: {score.get('home',0)}-{score.get('away',0)} | "
        + f"Team: {team_id} ({'HOME' if team_id == 0 else 'AWAY'}) | PlayMode: {play_mode}",
        f"Ball: ({ball_pos.get('x',0):.1f}, {ball_pos.get('y',0):.1f}) held by {ball_status}",
        f"Attack direction: {'→ +x' if team_id == 0 else '← -x'} (goal at x={goal_x})",
        "",
        "Your players:",
    ]

    for p in my_players:
        pos = p.get("position", {})
        pid = p.get("playerId", 0)
        role = "GK" if pid == 0 else f"P{pid}"
        stam = p.get("stamina", 100)
        action = p.get("lastAction", "")
        dist_ball = math.sqrt(
            (pos.get("x", 0) - ball_pos.get("x", 0)) ** 2
            + (pos.get("y", 0) - ball_pos.get("y", 0)) ** 2
        )
        dist_goal = abs(pos.get("x", 0) - goal_x)
        lines.append(
            f"  {role}(id={pid}): pos=({pos.get('x',0):.1f},{pos.get('y',0):.1f}) "
            f"stam={stam:.0f} distBall={dist_ball:.1f} distGoal={dist_goal:.1f} action={action}"
        )

    lines.append("")
    lines.append("Opponents:")
    for p in opponents:
        pos = p.get("position", {})
        pid = p.get("playerId", 0)
        lines.append(f"  P{pid}: ({pos.get('x',0):.1f},{pos.get('y',0):.1f})")

    return "\n".join(lines)


# --- Response Parsing ---

def parse_commands(text: str, team_id: int) -> list[dict]:
    """Extract command array from LLM response. Adds teamId to each command."""
    # Find JSON array in response
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            commands = json.loads(match.group())
            if isinstance(commands, list):
                for cmd in commands:
                    cmd["teamId"] = team_id
                return [c for c in commands if "commandType" in c]
        except json.JSONDecodeError:
            pass

    # Try parsing entire response
    try:
        result = json.loads(text)
        if isinstance(result, list):
            for cmd in result:
                cmd["teamId"] = team_id
            return [c for c in result if "commandType" in c]
        if isinstance(result, dict) and "commandType" in result:
            result["teamId"] = team_id
            return [result]
    except json.JSONDecodeError:
        pass

    return []


# --- Rule-Based Fallback ---

def fallback_commands(game_state: dict, team_id: int) -> list[dict]:
    """Simple rule-based fallback if LLM fails. Returns per-player commands."""
    ball = game_state.get("ball", {})
    ball_pos = ball.get("position", {"x": 0, "y": 0})
    players = game_state.get("players", [])
    my_players = [p for p in players if p.get("teamId") == team_id]
    possession_id = ball.get("possessionPlayerId")

    goal_x = 55 if team_id == 0 else -55
    commands = []

    # Find who has the ball
    we_have_ball = False
    if possession_id is not None:
        holder = next((p for p in players if p.get("playerId") == possession_id), None)
        if holder and holder.get("teamId") == team_id:
            we_have_ball = True

    for p in my_players:
        pid = p.get("playerId", 0)
        pos = p.get("position", {"x": 0, "y": 0})
        dist_ball = math.sqrt(
            (pos.get("x", 0) - ball_pos.get("x", 0)) ** 2
            + (pos.get("y", 0) - ball_pos.get("y", 0)) ** 2
        )

        if pid == 0:
            # Goalkeeper: stay back
            commands.append({
                "commandType": "SET_STANCE", "playerId": pid, "teamId": team_id,
                "parameters": {"stance": 2}, "duration": 0,
            })
        elif possession_id == pid:
            # We have the ball with this player
            dist_goal = abs(pos.get("x", 0) - goal_x)
            if dist_goal < 25:
                commands.append({
                    "commandType": "SHOOT", "playerId": pid, "teamId": team_id,
                    "parameters": {"aim_location": "TR", "power": 0.85}, "duration": 0,
                })
            else:
                commands.append({
                    "commandType": "MOVE_TO", "playerId": pid, "teamId": team_id,
                    "parameters": {"target_x": goal_x * 0.7, "target_y": 0, "sprint": True},
                    "duration": 0,
                })
        elif not we_have_ball and dist_ball < 15:
            # Opponent has ball, we're close — press
            commands.append({
                "commandType": "PRESS_BALL", "playerId": pid, "teamId": team_id,
                "parameters": {"intensity": 0.7}, "duration": 3,
            })
        elif we_have_ball:
            # Teammate has ball — move to create space
            offset_y = 10 if pid % 2 == 0 else -10
            commands.append({
                "commandType": "MOVE_TO", "playerId": pid, "teamId": team_id,
                "parameters": {"target_x": ball_pos.get("x", 0) + (10 if team_id == 0 else -10),
                               "target_y": offset_y, "sprint": False},
                "duration": 0,
            })
        else:
            # Default: move toward ball
            commands.append({
                "commandType": "MOVE_TO", "playerId": pid, "teamId": team_id,
                "parameters": {"target_x": ball_pos.get("x", 0), "target_y": ball_pos.get("y", 0),
                               "sprint": dist_ball > 20},
                "duration": 0,
            })

    return commands


# --- Entrypoint ---

@app.entrypoint
async def invoke(payload, context):
    """Receive game state, use LLM to decide commands, return JSON array."""
    try:
        prompt = payload.get("prompt", "{}")
        prompt_data = json.loads(prompt) if isinstance(prompt, str) else prompt

        game_state = prompt_data.get("gameState", {})
        team_id = prompt_data.get("teamId", 0)

        state_summary = summarize_state(game_state, team_id)
        log.info(f"Agent invoked for team {team_id}")

        # Ask the LLM for commands
        response = agent(state_summary)
        response_text = str(response)

        commands = parse_commands(response_text, team_id)

        if commands:
            log.info(f"LLM returned {len(commands)} commands: "
                     f"{[c.get('commandType') for c in commands]}")
            yield json.dumps(commands)
        else:
            # LLM response couldn't be parsed — use rule-based fallback
            log.warn(f"LLM parse failed, using fallback. Response: {response_text[:200]}")
            commands = fallback_commands(game_state, team_id)
            log.info(f"Fallback returned {len(commands)} commands")
            yield json.dumps(commands)

    except Exception as e:
        log.error(f"Agent error: {e}")
        # Last resort fallback
        try:
            commands = fallback_commands(
                json.loads(payload.get("prompt", "{}")).get("gameState", {}),
                json.loads(payload.get("prompt", "{}")).get("teamId", 0),
            )
            yield json.dumps(commands)
        except Exception:
            yield json.dumps([{
                "commandType": "PRESS_BALL", "playerId": 1, "teamId": 0,
                "parameters": {"intensity": 0.5}, "duration": 3,
            }])


if __name__ == "__main__":
    app.run()
