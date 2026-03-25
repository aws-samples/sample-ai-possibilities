"""Gateway Tool: evaluate_shot

Accepts game_state + team_id + player_id from the MCP schema,
extracts shooter/GK positions, and evaluates shot success probability.
"""

import json
import math

GOAL_HOME = {"x": -55, "y": 0}
GOAL_AWAY = {"x": 55, "y": 0}
GOAL_HALF_WIDTH = 5.0


def _distance(p1, p2):
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def _player_idx(p):
    if "agentId" in p:
        try:
            return int(p["agentId"].rsplit("_", 1)[-1])
        except (ValueError, IndexError):
            return 0
    return p.get("playerId", 0)


def _is_team(p, team_id):
    if "teamCode" in p:
        return p["teamCode"] == ("home" if team_id == 0 else "away")
    return p.get("teamId") == team_id


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    game_state = body.get("game_state", body)
    team_id = body.get("team_id", 0)
    player_id = body.get("player_id", 0)

    players = game_state.get("players", [])
    me = next((p for p in players if _player_idx(p) == player_id and _is_team(p, team_id)), None)
    shooter = me["position"] if me else {"x": 0, "y": 0}

    # Opponent GK is player index 0 on the other team
    opp_gk = next((p for p in players if _player_idx(p) == 0 and not _is_team(p, team_id)), None)
    gk_pos = opp_gk["position"] if opp_gk else {"x": 50, "y": 0}

    team_side = "HOME" if team_id == 0 else "AWAY"
    goal = GOAL_AWAY if team_side == "HOME" else GOAL_HOME

    # Blockers: opponents near the shooting lane (excluding GK)
    blockers = [p["position"] for p in players if not _is_team(p, team_id) and _player_idx(p) != 0]

    dist_to_goal = _distance(shooter, goal)
    dist_gk_to_goal = _distance(gk_pos, goal)

    angle_to_goal = math.atan2(GOAL_HALF_WIDTH, dist_to_goal)
    angle_factor = min(1.0, angle_to_goal / 0.15)
    distance_factor = max(0.0, 1.0 - (dist_to_goal / 55.0))
    gk_offset = abs(gk_pos["y"])
    gk_factor = min(1.0, gk_offset / 8.0) * 0.3
    gk_dist_factor = min(1.0, dist_gk_to_goal / 15.0) * 0.2

    blocker_penalty = 0.0
    for b in blockers:
        b_dist = _distance(shooter, b)
        if b_dist < 10:
            blocker_penalty += (10 - b_dist) / 10.0 * 0.15
    blocker_penalty = min(blocker_penalty, 0.4)

    probability = round(max(0.02, min(0.95,
        (distance_factor * 0.45) + (angle_factor * 0.25) + gk_factor + gk_dist_factor - blocker_penalty
    )), 2)

    if gk_pos["y"] > 1:
        aim = "BL" if shooter["y"] > 0 else "BR"
    elif gk_pos["y"] < -1:
        aim = "TL" if shooter["y"] > 0 else "TR"
    else:
        aim = "TR" if shooter["y"] <= 0 else "TL"

    return {"statusCode": 200, "body": json.dumps({
        "success_probability": probability,
        "distance_to_goal": round(dist_to_goal, 1),
        "recommended_aim": aim,
        "recommended_power": round(min(1.0, 0.6 + (dist_to_goal / 80.0)), 2),
        "should_shoot": probability > 0.25,
    })}
