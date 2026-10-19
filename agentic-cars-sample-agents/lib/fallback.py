"""Rule-based fallback for Cars Edition agents.

When the model gives nothing usable the car must still play. The first cycles set the team's
posture for the squad variant (the vendor's recommended levers), then each cycle issues one
role-appropriate moment command read from the game state.
"""

from dataclasses import dataclass

import arena


@dataclass(frozen=True)
class Posture:
    stance: str
    pressing: str
    tempo: str
    width: str
    shot_selection: str
    shape: str


POSTURES = {
    "balanced":   Posture("BALANCED", "NORMAL", "NORMAL", "NORMAL", "NORMAL", "1-1-2"),
    "aggressive": Posture("ATTACK", "HIGH", "FULL", "WIDE", "EAGER", "1-0-3"),
    "defensive":  Posture("DEFEND", "LOW", "MEASURED", "NARROW", "PATIENT", "2-1-1"),
}

OPENING = ("SET_TEAM_STANCE", "SET_SHAPE", "SET_PRESSING", "SET_SHOT_SELECTION", "SET_TEMPO", "SET_WIDTH")


def opening_command(agent_id: str, team_code: str, variant: str, cycle: int):
    """One posture lever per opening cycle, or None once the sequence is complete."""
    posture = POSTURES.get(variant, POSTURES["balanced"])
    if cycle >= len(OPENING):
        return None
    ct = OPENING[cycle]
    params = {
        "SET_TEAM_STANCE": {"stance": posture.stance},
        "SET_SHAPE": {"shape": posture.shape},
        "SET_PRESSING": {"level": posture.pressing},
        "SET_SHOT_SELECTION": {"level": posture.shot_selection},
        "SET_TEMPO": {"level": posture.tempo},
        "SET_WIDTH": {"level": posture.width},
    }[ct]
    return _cmd(agent_id, team_code, ct, params)


def moment_command(status: dict, agent_id: str, team_code: str, role: str, attacking_z: int):
    """A sensible single action for this car from the live state; None when holding shape is best."""
    ball = (status or {}).get("ball") or {}
    pos = ball.get("position") or {}
    bz = float(pos.get("z", 0.0))
    ball_third = arena.third(bz, attacking_z)
    controller = ball.get("controllerCarId")
    mine = _my_car(status, agent_id)
    i_have_it = mine is not None and controller is not None and str(controller) == str(mine.get("carId", controller))

    if role == "GOALKEEPER":
        return _cmd(agent_id, team_code, "DEFENSIVE_CLEAR", {"power": 1.0})
    if role == "DEFENDER":
        if ball_third == "defensive third":
            return _cmd(agent_id, team_code, "INTERCEPT", {"aggressive": False})
        return None
    if role == "SUPPORT":
        if ball_third == "attacking third":
            return _cmd(agent_id, team_code, "PRESS_BALL", {"intensity": 0.5})
        return _cmd(agent_id, team_code, "INTERCEPT", {"aggressive": False})
    # STRIKER
    if ball_third == "attacking third" or i_have_it:
        return _cmd(agent_id, team_code, "SHOOT", {"aim_location": "CENTER", "power": 0.9})
    return _cmd(agent_id, team_code, "PRESS_BALL", {"intensity": 0.7})


def last_resort(agent_id: str, team_code: str) -> dict:
    """Harmless when even the state is unreadable: hand the car back to its autonomous AI."""
    return _cmd(agent_id, team_code, "CLEAR_OVERRIDE", {})


def _my_car(status: dict, agent_id: str):
    for car in (status or {}).get("cars") or []:
        if car.get("agentId") == agent_id:
            return car
    return None


def _cmd(agent_id: str, team_code: str, command_type: str, parameters: dict) -> dict:
    return {"agentId": agent_id, "teamCode": team_code, "commandType": command_type, "parameters": parameters}
