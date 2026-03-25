"""Gateway Tool: get_defensive_assignment

Accepts game_state + team_id + player_id from the MCP schema,
extracts opponents/ball/position, and ranks threats for marking.
"""

import json
import math

GOAL_HOME = {"x": -55, "y": 0}
GOAL_AWAY = {"x": 55, "y": 0}


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


def _possession_idx(ball):
    agent_id = ball.get("possessionAgentId")
    if agent_id is not None:
        try:
            return int(agent_id.rsplit("_", 1)[-1])
        except (ValueError, IndexError):
            return None
    return ball.get("possessionPlayerId")


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    game_state = body.get("game_state", body)
    team_id = body.get("team_id", 0)
    player_id = body.get("player_id", 0)

    players = game_state.get("players", [])
    ball = game_state.get("ball", {})
    ball_pos = ball.get("position", {"x": 0, "y": 0})

    me = next((p for p in players if _player_idx(p) == player_id and _is_team(p, team_id)), None)
    my_position = me["position"] if me else {"x": 0, "y": 0}

    my_goal = GOAL_HOME if team_id == 0 else GOAL_AWAY
    possession_id = _possession_idx(ball)

    threats = []
    for opp in players:
        if _is_team(opp, team_id):
            continue
        pos = opp["position"]
        opp_id = _player_idx(opp)
        dist_to_goal = _distance(pos, my_goal)
        dist_to_ball = _distance(pos, ball_pos)
        dist_to_me = _distance(pos, my_position)

        goal_threat = max(0, 1.0 - (dist_to_goal / 80.0))
        ball_bonus = 0.3 if dist_to_ball < 10 else (0.15 if dist_to_ball < 20 else 0)
        has_ball = opp_id == possession_id
        possession_bonus = 0.4 if has_ball else 0.0
        threat_score = round(goal_threat + ball_bonus + possession_bonus, 2)

        threats.append({
            "player_id": opp_id,
            "threat_score": threat_score,
            "distance_to_goal": round(dist_to_goal, 1),
            "distance_to_me": round(dist_to_me, 1),
            "has_ball": has_ball,
            "recommended_tightness": "TIGHT" if threat_score > 0.7 else "LOOSE",
        })

    threats.sort(key=lambda x: x["threat_score"], reverse=True)
    top_threat = threats[0] if threats else None

    return {"statusCode": 200, "body": json.dumps({
        "threats": threats,
        "recommended_mark": top_threat,
        "action": "MARK" if top_threat and top_threat["distance_to_me"] < 30 else "INTERCEPT",
    })}
