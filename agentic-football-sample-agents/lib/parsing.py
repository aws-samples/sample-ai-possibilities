"""Response parsing utilities for AI soccer agents."""

import re

from json_tolerant import parse_json_tolerant

VALID_COMMANDS = {
    "MOVE_TO", "PASS", "SHOOT", "SLIDE_TACKLE", "PRESS_BALL", "INTERCEPT", "MARK",
    "FOLLOW_PLAYER", "GK_DISTRIBUTE", "SET_STANCE", "CLEAR_OVERRIDE", "RESET",
}


def parse_commands(text: str, team_id: int, my_player_id: int, on_recovered=None) -> list[dict]:
    """Extract commands from LLM response, forcing the given player ID on all commands.

    A model that writes Python-flavoured JSON (``True`` instead of ``true``, a trailing
    comma, a markdown fence) still has its commands used — see lib/json_tolerant.py for
    what is recovered and what is deliberately left alone. Pass ``on_recovered(raw)`` if
    you want to log how often that happens; the commands themselves are used exactly as
    if the model had emitted valid JSON.
    """
    for candidate in _iter_array_candidates(text):
        parsed = _loads(candidate, on_recovered)
        if not isinstance(parsed, list):
            continue
        commands = _tag_commands(parsed, team_id, my_player_id)
        if commands:
            return commands

    parsed = _loads(text, on_recovered)
    if isinstance(parsed, list):
        return _tag_commands(parsed, team_id, my_player_id)
    if isinstance(parsed, dict) and "commandType" in parsed:
        parsed["teamId"] = team_id
        parsed["playerId"] = my_player_id
        return [parsed]

    return []


def _iter_array_candidates(text: str):
    """Yield each balanced ``[...]`` span in ``text``, left to right.

    Previously the array was located with ``re.search(r"\\[[\\s\\S]*\\]")``,
    which is greedy on both ends: the span ran from the *first* ``[`` in the
    response to the *last* ``]``. Any bracket in the model's prose therefore
    swallowed the command array, the combined span failed to parse, and the
    agent silently dropped to rule-based play for that tick — which reads as
    a sluggish or badly prompted agent rather than a parse failure.

    Bracket depth is tracked so nested arrays inside a command survive, and
    string literals are skipped so a ``[`` or ``]`` inside a JSON string does
    not unbalance the scan.
    """
    for start, ch in enumerate(text):
        if ch != "[":
            continue
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            c = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
                continue
            if c == '"':
                in_string = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    yield text[start : i + 1]
                    break


def _loads(candidate: str, on_recovered):
    """Parse one candidate payload; None when it does not parse even after normalisation."""
    result = parse_json_tolerant(candidate)
    if result is None:
        return None
    value, recovered = result
    if recovered and on_recovered is not None:
        on_recovered(candidate)
    return value


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _tag_commands(commands: list, team_id: int, my_player_id: int) -> list[dict]:
    """Add teamId and playerId to each command, filtering to valid ones."""
    result = []
    for cmd in commands:
        # A bracketed aside in the prose can parse as a list of non-objects,
        # e.g. "[1, 2]". Skip those rather than raising, so the scan can move
        # on to the real command array.
        if not isinstance(cmd, dict):
            continue
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
            # NOTE: the SLIDE_TACKLE default of -1 is not a valid per-team
            # index, and the MARK/FOLLOW_PLAYER default of 0 is the opposing
            # goalkeeper, so an untargeted MARK marks the one opponent least
            # worth marking. Left as-is deliberately: this function has no
            # game state and so cannot choose a better opponent, and dropping
            # the command instead would change behaviour in a way that needs
            # the server's view on what an absent target does. Raised as an
            # open question rather than guessed at here.
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
