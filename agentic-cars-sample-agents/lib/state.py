"""State briefing for Cars Edition agents.

Turns the relay's /status into a short football-first briefing: score and clock, where the ball is in
the agent's own terms (which third, which side, who has it), the agent's car, and its teammates and
opponents with the car indexes the moment commands take. Short on purpose: long prompts make slow
agents.
"""

import math

import arena


def summarize_state(status: dict, team_code: str, agent_id: str, role: str, attacking_z: int = 1,
                    coach_instructions=None, duration_seconds=None) -> str:
    status = status or {}
    score = status.get("score") or {}
    cars = status.get("cars") or []
    mine = [c for c in cars if c.get("teamCode") == team_code]
    theirs = [c for c in cars if c.get("teamCode") != team_code]
    me = next((c for c in mine if c.get("agentId") == agent_id), None)
    my_side = _my_side(status, mine)
    my_goals = score.get("home", 0) if my_side == "home" else score.get("away", 0)
    their_goals = score.get("away", 0) if my_side == "home" else score.get("home", 0)
    diff = my_goals - their_goals
    score_state = "LEADING" if diff > 0 else "TRAILING" if diff < 0 else "LEVEL"
    game_time = float(status.get("gameTime") or 0.0)
    clock = f"{int(game_time)}s played"
    if duration_seconds:
        clock += f", {max(0, int(duration_seconds - game_time))}s left"

    ball = status.get("ball") or {}
    bp = ball.get("position") or {}
    bx, bz = float(bp.get("x", 0.0)), float(bp.get("z", 0.0))
    controller = ball.get("controllerCarId")
    holder = _holder(controller, mine, theirs)

    lines = [
        f"You are car {agent_id} ({role}) on the {my_side.upper()} team; you attack towards z = {'+' if attacking_z > 0 else '-'}{int(arena.HALF_Z)}.",
        f"Phase {status.get('currentPhase', '?')}; {clock}. Score: you {my_goals} - {their_goals} them ({score_state}).",
        f"Ball: {arena.third(bz, attacking_z)}, {arena.side(bx)} (x {bx:.1f}, z {bz:.1f}); {holder}.",
    ]
    if me:
        p = me.get("position") or {}
        lines.append(f"You: x {float(p.get('x', 0)):.1f}, z {float(p.get('z', 0)):.1f}, speed {float(me.get('speed') or 0):.1f} m/s, "
                     f"{_dist(p, bp):.1f} m from the ball.")
    if mine:
        lines.append("Teammates (index: role, distance to ball): " + ", ".join(
            f"{i}: {c.get('role', '?')} {_dist(c.get('position') or {}, bp):.0f}m" for i, c in enumerate(mine) if c is not me))
    if theirs:
        nearest = min(theirs, key=lambda c: _dist(c.get("position") or {}, bp), default=None)
        lines.append("Opponents (index: role, distance to ball): " + ", ".join(
            f"{i}: {c.get('role', '?')} {_dist(c.get('position') or {}, bp):.0f}m" for i, c in enumerate(theirs)))
        if nearest is not None:
            lines.append(f"Nearest opponent to the ball: index {theirs.index(nearest)} ({nearest.get('role', '?')}).")
    chat = status.get("teamChat") or []
    if chat:
        lines.append("Coach shouts: " + " | ".join(str(m.get("message", ""))[:80] for m in chat[-3:]))
    if coach_instructions:
        lines.append("Coach instructions: " + " | ".join(str(c)[:120] for c in list(coach_instructions)[-3:]))
    lines.append("Reply with a JSON array of 1-3 commands. Change posture only when the situation changed.")
    return "\n".join(lines)


def _my_side(status: dict, mine: list) -> str:
    if status.get("homeTeamCode") and mine:
        return "home" if mine[0].get("teamCode") == status.get("homeTeamCode") else "away"
    return str(status.get("mySide") or "home")


def _holder(controller, mine: list, theirs: list) -> str:
    if controller is None:
        return "loose ball"
    for i, c in enumerate(mine):
        if str(c.get("carId", "")) == str(controller) or str(i) == str(controller):
            return f"your teammate index {i} has it"
    for i, c in enumerate(theirs):
        if str(c.get("carId", "")) == str(controller) or str(i) == str(controller):
            return f"opponent index {i} has it"
    return "contested"


def _dist(a: dict, b: dict) -> float:
    return math.hypot(float(a.get("x", 0)) - float(b.get("x", 0)), float(a.get("z", 0)) - float(b.get("z", 0)))
