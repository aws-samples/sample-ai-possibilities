"""Gateway Tool: find_open_space

Finds the best open space on the field for a player to move to,
based on opponent positions and the target zone (attack/midfield/defense).

Uses a grid sampling approach to find the point farthest from all opponents
within the desired zone.

Deployed as a Lambda behind AgentCore Gateway.
"""

import json
import math


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _min_opponent_distance(x: float, y: float, opponents: list[dict]) -> float:
    if not opponents:
        return 999.0
    return min(_distance(x, y, o["x"], o["y"]) for o in opponents)


def lambda_handler(event, context):
    """Lambda handler — input: opponents, zone preference, team side."""
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    opponents = body["opponent_positions"]
    zone = body.get("zone", "attack")  # "attack", "midfield", "defense"
    team_side = body.get("team_side", "HOME")  # HOME defends -x, AWAY defends +x
    my_position = body.get("my_position", {"x": 0, "y": 0})

    # Define zone x-ranges based on team side
    if team_side == "HOME":
        zones = {"defense": (-55, -15), "midfield": (-15, 15), "attack": (15, 52)}
    else:
        zones = {"defense": (15, 55), "midfield": (-15, 15), "attack": (-52, -15)}

    x_min, x_max = zones.get(zone, zones["midfield"])
    y_min, y_max = -30, 30

    # Sample grid points and find the one with max distance from opponents
    best_point = None
    best_score = -1

    step = 5
    x = x_min
    while x <= x_max:
        y = y_min
        while y <= y_max:
            min_opp_dist = _min_opponent_distance(x, y, opponents)
            # Penalize points too far from current position (prefer reachable space)
            my_dist = _distance(x, y, my_position["x"], my_position["y"])
            score = min_opp_dist - (my_dist * 0.15)

            if score > best_score:
                best_score = score
                best_point = {"x": round(x, 1), "y": round(y, 1)}
            y += step
        x += step

    min_opp = round(_min_opponent_distance(best_point["x"], best_point["y"], opponents), 1)
    my_dist = round(_distance(best_point["x"], best_point["y"], my_position["x"], my_position["y"]), 1)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "recommended_position": best_point,
            "nearest_opponent_distance": min_opp,
            "distance_from_current": my_dist,
            "zone": zone,
        }),
    }
