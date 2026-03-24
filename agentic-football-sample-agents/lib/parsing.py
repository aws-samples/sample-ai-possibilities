"""Response parsing utilities for AI soccer agents."""

import json
import re

VALID_COMMANDS = {
    "MOVE_TO", "PASS", "SHOOT", "SLIDE_TACKLE", "PRESS_BALL", "INTERCEPT", "MARK",
    "FOLLOW_PLAYER", "GK_DISTRIBUTE", "SET_STANCE", "CLEAR_OVERRIDE", "RESET",
}


def parse_commands(text: str, team_id: int, my_player_id: int) -> list[dict]:
    """Extract commands from LLM response, forcing the given player ID on all commands."""
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            commands = json.loads(match.group())
            if isinstance(commands, list):
                return _tag_commands(commands, team_id, my_player_id)
        except json.JSONDecodeError:
            pass

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return _tag_commands(parsed, team_id, my_player_id)
        if isinstance(parsed, dict) and "commandType" in parsed:
            parsed["teamId"] = team_id
            parsed["playerId"] = my_player_id
            return [parsed]
    except json.JSONDecodeError:
        pass

    return []


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _tag_commands(commands: list, team_id: int, my_player_id: int) -> list[dict]:
    """Add teamId and playerId to each command, filtering to valid ones."""
    result = []
    for cmd in commands:
        cmd["teamId"] = team_id
        cmd["playerId"] = my_player_id
        if "commandType" in cmd:
            # Skip unrecognized command types
            if cmd["commandType"] not in VALID_COMMANDS:
                continue
            # Clamp MOVE_TO coordinates to field bounds
            if cmd["commandType"] == "MOVE_TO":
                params = cmd.get("parameters", {})
                if isinstance(params.get("target_x"), (int, float)):
                    params["target_x"] = _clamp(params["target_x"], -55, 55)
                if isinstance(params.get("target_y"), (int, float)):
                    params["target_y"] = _clamp(params["target_y"], -35, 35)
            # Ensure PASS/MARK/FOLLOW_PLAYER/GK_DISTRIBUTE/SLIDE_TACKLE have target_player_id
            if cmd["commandType"] in ("PASS", "MARK", "FOLLOW_PLAYER", "GK_DISTRIBUTE", "SLIDE_TACKLE"):
                params = cmd.get("parameters", {})
                if params.get("target_player_id") is None:
                    # Default: pass to a forward, mark nearest opponent, tackle ball carrier
                    if cmd["commandType"] in ("PASS", "GK_DISTRIBUTE"):
                        params["target_player_id"] = 3 if my_player_id != 3 else 4
                    elif cmd["commandType"] == "SLIDE_TACKLE":
                        params["target_player_id"] = -1  # target ball carrier
                    else:
                        params["target_player_id"] = 0  # mark/follow opponent 0
                    cmd["parameters"] = params
            result.append(cmd)
    return result
