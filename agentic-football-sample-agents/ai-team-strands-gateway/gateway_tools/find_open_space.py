"""Gateway Tool: find_open_space

Accepts game_state + team_id + zone from the MCP schema,
extracts opponent positions, and finds the best open space.
"""

import json
import math


def _distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _min_opp_dist(x, y, opponents):
    if not opponents:
        return 999.0
    return min(_distance(x, y, o["x"], o["y"]) for o in opponents)


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
    zone = body.get("zone", "attack")

    players = game_state.get("players", [])
    me = next((p for p in players if _player_idx(p) == player_id and _is_team(p, team_id)), None)
    my_position = me["position"] if me else {"x": 0, "y": 0}

    opp_positions = [p["position"] for p in players if not _is_team(p, team_id)]
    team_side = "HOME" if team_id == 0 else "AWAY"

    if team_side == "HOME":
        zones = {"defense": (-55, -15), "midfield": (-15, 15), "attack": (15, 52)}
    else:
        zones = {"defense": (15, 55), "midfield": (-15, 15), "attack": (-52, -15)}

    x_min, x_max = zones.get(zone, zones["midfield"])
    best_point = None
    best_score = -1
    step = 5
    x = x_min
    while x <= x_max:
        y = -30
        while y <= 30:
            min_d = _min_opp_dist(x, y, opp_positions)
            my_dist = _distance(x, y, my_position["x"], my_position["y"])
            score = min_d - (my_dist * 0.15)
            if score > best_score:
                best_score = score
                best_point = {"x": round(x, 1), "y": round(y, 1)}
            y += step
        x += step

    min_opp = round(_min_opp_dist(best_point["x"], best_point["y"], opp_positions), 1)
    my_dist = round(_distance(best_point["x"], best_point["y"], my_position["x"], my_position["y"]), 1)

    return {"statusCode": 200, "body": json.dumps({
        "recommended_position": best_point,
        "nearest_opponent_distance": min_opp,
        "distance_from_current": my_dist,
        "zone": zone,
    })}
