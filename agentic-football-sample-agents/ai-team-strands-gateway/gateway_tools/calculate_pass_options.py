"""Gateway Tool: calculate_pass_options

Accepts game_state + team_id + player_id from the MCP schema,
extracts the relevant data, and calculates pass success probability
for each teammate based on distance and interception risk.
"""

import json
import math


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


def _interception_risk(passer, receiver, opponents):
    pass_dist = _distance(passer, receiver)
    if pass_dist < 1:
        return 0.0
    dx = receiver["x"] - passer["x"]
    dy = receiver["y"] - passer["y"]
    risk = 0.0
    for opp in opponents:
        ox = opp["x"] - passer["x"]
        oy = opp["y"] - passer["y"]
        t = max(0, min(1, (ox * dx + oy * dy) / (pass_dist ** 2)))
        cx = passer["x"] + t * dx
        cy = passer["y"] + t * dy
        d = math.sqrt((opp["x"] - cx) ** 2 + (opp["y"] - cy) ** 2)
        if d < 8:
            risk = max(risk, 1.0 - (d / 8.0))
    return min(risk, 0.95)


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    game_state = body.get("game_state", body)
    team_id = body.get("team_id", 0)
    player_id = body.get("player_id", 0)

    players = game_state.get("players", [])
    me = next((p for p in players if _player_idx(p) == player_id and _is_team(p, team_id)), None)
    passer_pos = me["position"] if me else {"x": 0, "y": 0}

    teammates = [
        {"player_id": _player_idx(p), "position": p["position"]}
        for p in players if _is_team(p, team_id) and _player_idx(p) != player_id
    ]
    opp_positions = [p["position"] for p in players if not _is_team(p, team_id)]

    options = []
    for tm in teammates:
        dist = round(_distance(passer_pos, tm["position"]), 1)
        risk = _interception_risk(passer_pos, tm["position"], opp_positions)
        success = round(max(0.05, 1.0 - risk - (dist / 120.0)), 2)
        options.append({
            "player_id": tm["player_id"],
            "distance": dist,
            "interception_risk": round(risk, 2),
            "success_probability": success,
            "recommended_type": "GROUND" if dist < 20 else ("THROUGH" if success > 0.5 else "AERIAL"),
        })

    options.sort(key=lambda x: x["success_probability"], reverse=True)
    return {"statusCode": 200, "body": json.dumps({"pass_options": options})}
