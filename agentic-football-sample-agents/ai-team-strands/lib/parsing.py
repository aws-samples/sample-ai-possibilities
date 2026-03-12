"""Response parsing utilities for AI soccer agents."""

import json
import re


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


def _tag_commands(commands: list, team_id: int, my_player_id: int) -> list[dict]:
    """Add teamId and playerId to each command, filtering to valid ones."""
    result = []
    for cmd in commands:
        cmd["teamId"] = team_id
        cmd["playerId"] = my_player_id
        if "commandType" in cmd:
            result.append(cmd)
    return result
