"""Gateway Tool: get_defensive_assignment

Ranks opponent players by threat level and recommends which opponent
a defender should mark, based on proximity to goal, ball possession,
and positioning.

Deployed as a Lambda behind AgentCore Gateway.
"""

import json
import math

GOAL_HOME = {"x": -55, "y": 0}
GOAL_AWAY = {"x": 55, "y": 0}


def _distance(p1: dict, p2: dict) -> float:
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def lambda_handler(event, context):
    """Lambda handler — input: opponents, ball info, team side, my position."""
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    opponents = body["opponents"]
    ball = body["ball"]
    team_side = body.get("team_side", "HOME")
    my_position = body["my_position"]

    my_goal = GOAL_HOME if team_side == "HOME" else GOAL_AWAY

    threats = []
    for opp in opponents:
        pos = opp["position"]
        dist_to_goal = _distance(pos, my_goal)
        dist_to_ball = _distance(pos, {"x": ball["x"], "y": ball["y"]})
        dist_to_me = _distance(pos, my_position)

        # Threat score: closer to goal = more dangerous
        goal_threat = max(0, 1.0 - (dist_to_goal / 80.0))

        # Ball proximity bonus
        ball_bonus = 0.3 if dist_to_ball < 10 else (0.15 if dist_to_ball < 20 else 0)

        # Has ball bonus
        has_ball = opp.get("player_id") == ball.get("possession_player_id")
        possession_bonus = 0.4 if has_ball else 0.0

        threat_score = round(goal_threat + ball_bonus + possession_bonus, 2)

        threats.append({
            "player_id": opp["player_id"],
            "threat_score": threat_score,
            "distance_to_goal": round(dist_to_goal, 1),
            "distance_to_me": round(dist_to_me, 1),
            "has_ball": has_ball,
            "recommended_tightness": "TIGHT" if threat_score > 0.7 else "LOOSE",
        })

    threats.sort(key=lambda x: x["threat_score"], reverse=True)

    top_threat = threats[0] if threats else None

    return {
        "statusCode": 200,
        "body": json.dumps({
            "threats": threats,
            "recommended_mark": top_threat,
            "action": "MARK" if top_threat and top_threat["distance_to_me"] < 30 else "INTERCEPT",
        }),
    }
