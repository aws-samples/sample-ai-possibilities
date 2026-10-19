"""The Cars Edition arena, measured on the sandbox relay (docs/game-server/cars/CONTRACT.md).

Shared by the prompt, the parser and the fallback so every agent is told about, and clamped to, the
same field. Coordinates are metres: x runs across the pitch, z along it; MOVE_TO takes target_x = x
and target_y = z. The pitch is 53 x 84 with the goal lines at |z| = 42 and an 18 m wide goal mouth.
"""

HALF_X = 26.5
HALF_Z = 42.0
GOAL_HALF_WIDTH = 9.0
GOAL_HEIGHT = 8.0
# Keep MOVE_TO targets a little inside the walls so a car never drives into a corner it cannot leave.
MARGIN = 1.5


def clamp_x(value: float) -> float:
    return max(-HALF_X + MARGIN, min(HALF_X - MARGIN, float(value)))


def clamp_z(value: float) -> float:
    return max(-HALF_Z + MARGIN, min(HALF_Z - MARGIN, float(value)))


def third(z: float, attacking_z: int) -> str:
    """Which third of the pitch a z coordinate is in, from the agent's team's point of view."""
    towards_their_goal = z * attacking_z
    if towards_their_goal > HALF_Z / 3:
        return "attacking third"
    if towards_their_goal < -HALF_Z / 3:
        return "defensive third"
    return "middle third"


def side(x: float) -> str:
    if x > HALF_X / 3:
        return "right"
    if x < -HALF_X / 3:
        return "left"
    return "centre"
