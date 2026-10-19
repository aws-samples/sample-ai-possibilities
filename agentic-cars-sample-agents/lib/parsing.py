"""Response parsing for Cars Edition agents.

The model replies with a JSON array of one to three commands for its own car (posture levers are
team-wide; moment commands act on this car). The relay queues anything with a known commandType and a
valid agent, so the parameter checks here are what keeps a car from driving into a wall or sending an
out-of-domain enum the host will ignore.
"""

import re

import arena
from json_tolerant import parse_json_tolerant

VALID_COMMANDS = {
    "MOVE_TO", "FOLLOW_PLAYER", "MARK", "PRESS_BALL", "INTERCEPT", "DEFENSIVE_CLEAR", "BUMP", "SHOOT",
    "PASS", "CLEAR_OVERRIDE", "RESET", "SET_ROLE_PARAMS", "SET_TEAM_STANCE", "SET_SHOT_SELECTION",
    "SET_PRESSING", "SET_TEMPO", "SET_WIDTH", "SET_SHAPE", "SET_FORMATION",
}
MAX_COMMANDS = 3
MOMENT_COMMANDS = {"MOVE_TO", "FOLLOW_PLAYER", "MARK", "PRESS_BALL", "INTERCEPT", "DEFENSIVE_CLEAR", "BUMP", "SHOOT", "PASS"}

_LEVELS = {
    "SET_SHOT_SELECTION": {"EAGER", "NORMAL", "PATIENT"},
    "SET_PRESSING": {"HIGH", "NORMAL", "LOW"},
    "SET_TEMPO": {"FULL", "NORMAL", "MEASURED"},
    "SET_WIDTH": {"WIDE", "NORMAL", "NARROW"},
}
_STANCES = {"ATTACK", "BALANCED", "DEFEND"}
_AIM = {"TL", "TR", "BL", "BR", "CENTER"}
_TIGHTNESS = {"LOOSE", "TIGHT"}
_TEAMS = {"HOME", "AWAY"}
_ROLES = {"STRIKER", "SUPPORT", "DEFENDER"}
_SHAPE = re.compile(r"^(\d)-(\d)-(\d)$")
OUTFIELD_CARS = 4


def parse_commands(text: str, agent_id: str, team_code: str, on_recovered=None) -> list:
    """Extract up to MAX_COMMANDS valid commands and stamp agentId + teamCode on each.

    Returns an empty list when nothing valid parses; the caller then falls back to rule-based play.
    ``on_recovered(raw)`` fires when the text only parsed after tolerant normalisation.
    """
    objs = _command_objects(text, on_recovered)
    out, seen = [], set()
    wants_moment = any(str(o.get("commandType", "")).upper() in MOMENT_COMMANDS for o in objs)
    moment_taken = False
    for obj in objs:
        ct = str(obj.get("commandType", "")).upper()
        if ct not in VALID_COMMANDS or ct in seen:
            continue
        if ct in ("CLEAR_OVERRIDE", "RESET") and wants_moment:
            continue
        if ct in MOMENT_COMMANDS:
            if moment_taken:
                continue
            moment_taken = True
        params = _sanitise(ct, obj.get("parameters") or {})
        if params is None:
            continue
        cmd = {"agentId": agent_id, "teamCode": team_code, "commandType": ct, "parameters": params}
        duration = _number(obj.get("duration"))
        if duration is not None and duration > 0:
            cmd["duration"] = duration
        out.append(cmd)
        seen.add(ct)
        if len(out) == MAX_COMMANDS:
            break
    return out


def _command_objects(text: str, on_recovered=None) -> list:
    for candidate in _json_candidates(text):
        result = parse_json_tolerant(candidate)
        if result is None:
            continue
        parsed, recovered = result
        if recovered and on_recovered is not None:
            on_recovered(candidate)
        if isinstance(parsed, dict) and "commandType" in parsed:
            return [parsed]
        if isinstance(parsed, list):
            found = [el for el in parsed if isinstance(el, dict) and "commandType" in el]
            if found:
                return found
    # The array itself is broken (an extra brace, a missing comma): salvage each command object on its
    # own. Small models do this a few times per match and the valid commands should still land.
    found = []
    for m in _OBJECT.finditer(text):
        result = parse_json_tolerant(m.group())
        if result and isinstance(result[0], dict) and "commandType" in result[0]:
            found.append(result[0])
    if found and on_recovered is not None:
        on_recovered(text)
    return found


_OBJECT = re.compile(r"\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}")


def _json_candidates(text: str):
    yield text
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        yield m.group()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        yield m.group()


def _sanitise(command_type: str, params: dict):
    """Normalise enum casing, clamp numbers, drop unknown keys. None means the command is unusable."""
    out = {}
    if command_type in _LEVELS:
        level = str(params.get("level", "")).upper()
        if level not in _LEVELS[command_type]:
            return None
        out["level"] = level
    elif command_type == "SET_TEAM_STANCE":
        stance = str(params.get("stance", "")).upper()
        if stance not in _STANCES:
            return None
        out["stance"] = stance
    elif command_type == "SET_SHAPE":
        shape = str(params.get("shape", "")).strip()
        m = _SHAPE.match(shape)
        if not m or sum(int(g) for g in m.groups()) != OUTFIELD_CARS:
            return None
        out["shape"] = shape
    elif command_type == "SET_FORMATION":
        shape = str(params.get("formation", params.get("shape", ""))).strip()
        m = _SHAPE.match(shape)
        if not m or sum(int(g) for g in m.groups()) != OUTFIELD_CARS:
            return None
        out["formation"] = shape
    elif command_type == "MOVE_TO":
        x, z = _number(params.get("target_x")), _number(params.get("target_y"))
        if x is None or z is None:
            return None
        out["target_x"] = round(arena.clamp_x(x), 2)
        out["target_y"] = round(arena.clamp_z(z), 2)
        _bool_into(out, "sprint", params)
    elif command_type == "BUMP":
        target = _int(params.get("target_player_id"))
        out["target_player_id"] = -1 if target is None else target
        _bool_into(out, "sprint", params)
    elif command_type == "SHOOT":
        aim = str(params.get("aim_location", "CENTER")).upper()
        out["aim_location"] = aim if aim in _AIM else "CENTER"
        out["power"] = _clamp01(params.get("power"), default=0.8)
    elif command_type == "PASS":
        target = _int(params.get("target_player_id"))
        if target is None:
            return None
        out["target_player_id"] = target
        _bool_into(out, "lead", params)
    elif command_type == "FOLLOW_PLAYER":
        target = _int(params.get("target_player_id"))
        if target is None:
            return None
        out["target_player_id"] = target
        team = str(params.get("target_team", "")).upper()
        if team in _TEAMS:
            out["target_team"] = team
        distance = _number(params.get("distance"))
        if distance is not None and distance > 0:
            out["distance"] = distance
    elif command_type == "MARK":
        target = _int(params.get("target_player_id"))
        if target is None:
            return None
        out["target_player_id"] = target
        tightness = str(params.get("tightness", "TIGHT")).upper()
        out["tightness"] = tightness if tightness in _TIGHTNESS else "TIGHT"
    elif command_type == "PRESS_BALL":
        out["intensity"] = _clamp01(params.get("intensity"), default=0.6)
    elif command_type == "INTERCEPT":
        _bool_into(out, "aggressive", params)
    elif command_type == "DEFENSIVE_CLEAR":
        out["power"] = _clamp01(params.get("power"), default=1.0)
    elif command_type == "SET_ROLE_PARAMS":
        role = str(params.get("role", "")).upper()
        if role in _ROLES:
            out["role"] = role
        for key in ("forward_bias", "press_intensity", "speed_bias"):
            v = _number(params.get(key))
            if v is not None:
                out[key] = max(0.0, min(1.0, v))
        for key in ("shoot_distance", "defend_distance"):
            v = _number(params.get(key))
            if v is not None and v >= 0:
                out[key] = v
        if not out:
            return None
    # CLEAR_OVERRIDE / RESET take no parameters.
    return out


def _bool_into(out: dict, key: str, params: dict) -> None:
    v = params.get(key)
    if isinstance(v, bool):
        out[key] = v
    elif isinstance(v, str) and v.lower() in ("true", "false"):
        out[key] = v.lower() == "true"


def _number(v):
    if isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v):
    n = _number(v)
    return None if n is None else int(n)


def _clamp01(v, default: float) -> float:
    n = _number(v)
    return default if n is None else max(0.0, min(1.0, n))
