"""Gateway Tool: evaluate_shot

Evaluates shot success probability from a given position,
considering distance to goal, angle, and goalkeeper position.

Deployed as a Lambda behind AgentCore Gateway.
"""

import json
import math

# Goal center positions
GOAL_HOME = {"x": -55, "y": 0}  # HOME team's goal
GOAL_AWAY = {"x": 55, "y": 0}   # AWAY team's goal
GOAL_HALF_WIDTH = 5.0  # approximate half-width of goal


def _distance(p1: dict, p2: dict) -> float:
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def lambda_handler(event, context):
    """Lambda handler — input: shooter position, GK position, team side."""
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    shooter = body["shooter_position"]
    gk_pos = body["goalkeeper_position"]
    team_side = body.get("team_side", "HOME")
    blockers = body.get("blocker_positions", [])

    # Target goal (opponent's goal)
    goal = GOAL_AWAY if team_side == "HOME" else GOAL_HOME

    dist_to_goal = _distance(shooter, goal)
    dist_gk_to_goal = _distance(gk_pos, goal)

    # Angle factor: wider angle = better chance
    dy = abs(shooter["y"])
    angle_to_goal = math.atan2(GOAL_HALF_WIDTH, dist_to_goal)
    angle_factor = min(1.0, angle_to_goal / 0.15)

    # Distance factor: closer = better
    distance_factor = max(0.0, 1.0 - (dist_to_goal / 55.0))

    # GK positioning factor: GK off-center = better chance
    gk_offset = abs(gk_pos["y"])
    gk_factor = min(1.0, gk_offset / 8.0) * 0.3

    # GK distance factor: GK far from goal = better
    gk_dist_factor = min(1.0, dist_gk_to_goal / 15.0) * 0.2

    # Blocker penalty
    blocker_penalty = 0.0
    for b in blockers:
        b_dist = _distance(shooter, b)
        if b_dist < 10:
            blocker_penalty += (10 - b_dist) / 10.0 * 0.15
    blocker_penalty = min(blocker_penalty, 0.4)

    probability = round(
        max(0.02, min(0.95,
            (distance_factor * 0.45) + (angle_factor * 0.25) + gk_factor + gk_dist_factor - blocker_penalty
        )), 2
    )

    # Recommend aim location based on GK position
    if gk_pos["y"] > 1:
        aim = "BL" if shooter["y"] > 0 else "BR"
    elif gk_pos["y"] < -1:
        aim = "TL" if shooter["y"] > 0 else "TR"
    else:
        aim = "TR" if shooter["y"] <= 0 else "TL"

    recommended_power = round(min(1.0, 0.6 + (dist_to_goal / 80.0)), 2)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "success_probability": probability,
            "distance_to_goal": round(dist_to_goal, 1),
            "recommended_aim": aim,
            "recommended_power": recommended_power,
            "should_shoot": probability > 0.25,
        }),
    }
