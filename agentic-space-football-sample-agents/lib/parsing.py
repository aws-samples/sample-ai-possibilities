"""Response parsing for Space Football policy agents.

Space Football agents are MANAGERS, not joysticks: they emit ONE standing-policy command per ~2s
cycle (a team-tactics vote, a per-ship role, a contingency, or a team message), not per-tick
moves. The relay validates parameters against contracts/command-schemas.json, so this parser
only needs to extract a single well-formed command and stamp the issuing agentId + teamCode.
"""

import json
import re

# The 9 frozen space football command types (contracts/command-schemas.json).
VALID_COMMANDS = {
    "SET_TEAM_TACTICS", "SET_BIKE_ROLE", "SET_MARKING", "SET_CONTINGENCY",
    "CLEAR_CONTINGENCY", "SEND_TEAM_MESSAGE", "CALL_TIMEOUT", "CLEAR_POLICY", "RESET_TEAM",
}

# Enum domains — used to normalise casing and drop out-of-range values before the relay sees them.
_DEF_LINE = {"DEEP", "MID", "HIGH"}
_SHOT_BIAS = {"FAR_POST", "NEAR_POST", "CENTRE"}
_DASH_USE = {"CONSERVE", "DEFEND", "BALANCED", "CHASE"}
_ROLE = {"KEEPER", "SWEEPER", "SUPPORT", "RUNNER", "STRIKER", "FREE"}
_TRIGGER = {"TRAILING", "LEADING", "LEVEL", "LAST_30S", "TRAILING_LATE", "LEADING_LATE"}


def _clamp01(v):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None


def parse_command(text: str, agent_id: str, team_code: str) -> dict | None:
    """Extract ONE command from an LLM response and stamp agentId + teamCode.

    Space Football is one-command-per-cycle, so we take the first valid command found (a single
    object, or the first element of a list). Returns None if nothing valid parses — the caller
    then falls back to a rule-based opening policy.
    """
    obj = _first_command_object(text)
    if obj is None:
        return None

    ct = obj.get("commandType")
    if ct not in VALID_COMMANDS:
        return None

    params = _sanitise_params(ct, obj.get("parameters", {}) or {})
    cmd = {
        "agentId": agent_id,
        "teamCode": team_code,
        "commandType": ct,
        "parameters": params,
    }
    # Rationale is mandatory (<=200); keep the model's if present, else a terse default.
    rationale = obj.get("rationale") or "policy update"
    cmd["rationale"] = str(rationale)[:200]
    if obj.get("message"):
        cmd["message"] = str(obj["message"])[:240]
    return cmd


def _first_command_object(text: str) -> dict | None:
    # Prefer a JSON object; also accept the first element of a JSON array.
    for candidate in _json_candidates(text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "commandType" in parsed:
            return parsed
        if isinstance(parsed, list):
            for el in parsed:
                if isinstance(el, dict) and "commandType" in el:
                    return el
    return None


def _json_candidates(text: str):
    # Whole string first, then the first {...} or [...] block embedded in prose.
    yield text
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        yield m.group()
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        yield m.group()


def _sanitise_params(command_type: str, params: dict) -> dict:
    """Normalise enum casing + clamp 0..1 levers; drop unknown/out-of-range values so the relay
    schema check passes (or the field is simply omitted = 'no opinion')."""
    out = {}
    if command_type in ("SET_TEAM_TACTICS", "SET_CONTINGENCY"):
        for k in ("aggression", "keeperAggression", "width"):
            v = _clamp01(params.get(k))
            if v is not None:
                out[k] = v
        _enum_into(out, "defensiveLine", params, _DEF_LINE)
        _enum_into(out, "shotBias", params, _SHOT_BIAS)
        _enum_into(out, "dashUse", params, _DASH_USE)
        if command_type == "SET_CONTINGENCY":
            trig = str(params.get("trigger", "")).upper()
            if trig in _TRIGGER:
                out["trigger"] = trig
    elif command_type == "SET_BIKE_ROLE":
        _enum_into(out, "role", params, _ROLE)
        if "agentId" in params:
            out["agentId"] = str(params["agentId"])
        v = _clamp01(params.get("aggression"))
        if v is not None:
            out["aggression"] = v
    elif command_type == "SET_MARKING":
        if params.get("agentId"):
            out["agentId"] = str(params["agentId"])
        if params.get("opponentAgentId"):
            out["opponentAgentId"] = str(params["opponentAgentId"])
    elif command_type == "SEND_TEAM_MESSAGE":
        if params.get("to"):
            out["to"] = str(params["to"])
        if params.get("text"):
            out["text"] = str(params["text"])[:240]
    # CALL_TIMEOUT / CLEAR_CONTINGENCY / CLEAR_POLICY / RESET_TEAM take no parameters.
    return out


def _enum_into(out: dict, key: str, params: dict, domain: set):
    raw = params.get(key)
    if raw is None:
        return
    val = str(raw).upper()
    if val in domain:
        out[key] = val
