"""Gateway Tool: calculate_pass_options

Given a player's position, teammates, and opponents, calculates pass
success probability for each teammate based on distance and interception risk.

Deployed as a Lambda behind AgentCore Gateway.
"""

import json
import math


def _distance(p1: dict, p2: dict) -> float:
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def _interception_risk(passer: dict, receiver: dict, opponents: list[dict]) -> float:
    """Estimate interception probability (0-1) based on opponents near the pass lane."""
    pass_dist = _distance(passer, receiver)
    if pass_dist < 1:
        return 0.0

    dx = receiver["x"] - passer["x"]
    dy = receiver["y"] - passer["y"]
    risk = 0.0

    for opp in opponents:
        # Project opponent onto pass vector
        ox = opp["x"] - passer["x"]
        oy = opp["y"] - passer["y"]
        t = max(0, min(1, (ox * dx + oy * dy) / (pass_dist ** 2)))
        closest_x = passer["x"] + t * dx
        closest_y = passer["y"] + t * dy
        dist_to_lane = math.sqrt((opp["x"] - closest_x) ** 2 + (opp["y"] - closest_y) ** 2)

        if dist_to_lane < 8:
            risk = max(risk, 1.0 - (dist_to_lane / 8.0))

    return min(risk, 0.95)


def lambda_handler(event, context):
    """Lambda handler — input: passer position, teammates, opponents."""
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    passer_pos = body["passer_position"]
    teammates = body["teammates"]
    opponents = body["opponents"]

    options = []
    for tm in teammates:
        dist = round(_distance(passer_pos, tm["position"]), 1)
        risk = _interception_risk(passer_pos, tm["position"], [o["position"] for o in opponents])
        success = round(max(0.05, 1.0 - risk - (dist / 120.0)), 2)

        options.append({
            "player_id": tm["player_id"],
            "distance": dist,
            "interception_risk": round(risk, 2),
            "success_probability": success,
            "recommended_type": "GROUND" if dist < 20 else ("THROUGH" if success > 0.5 else "AERIAL"),
        })

    options.sort(key=lambda x: x["success_probability"], reverse=True)

    return {
        "statusCode": 200,
        "body": json.dumps({"pass_options": options}),
    }
