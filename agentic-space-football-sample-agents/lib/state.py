"""State summariser for Space Football policy agents.

Turns the relay's GET /status projection into a compact, football-first briefing for the LLM.
Per STARTER_AGENT_PROMPT: agents should reason about the DERIVED block (possession, threat,
openPost, scoreState) — plain-language football — not do geometry on raw ship coordinates.
Kept short on purpose: long prompts = slow agents = fewer decisions.
"""

import json


def summarize_state(status: dict, team_code: str, my_agent_id: str, role_label: str) -> str:
    """Compact briefing for one agent's ~2s decision cycle."""
    phase = status.get("phase", "?")
    mode = status.get("mode", "STRIKE")
    period = status.get("period", 1)
    time_left = status.get("periodTimeLeft", 0)
    score = status.get("score", {}) or {}
    home, away = score.get("home", 0), score.get("away", 0)

    # Which side am I? The status echoes home/away team codes.
    my_side = "home" if status.get("homeTeamCode") == team_code else \
              "away" if status.get("awayTeamCode") == team_code else "?"
    my_goals, their_goals = (home, away) if my_side == "home" else (away, home)
    diff = my_goals - their_goals
    score_state = "LEADING" if diff > 0 else "TRAILING" if diff < 0 else "LEVEL"

    # Derived block if the relay provides one (plain-language football); else a compact raw view.
    derived = status.get("derived") or {}
    my_bikes = [b for b in status.get("bikes", []) if _same_side(b, my_side)]
    me = next((b for b in my_bikes if b.get("agentId") == my_agent_id), None)

    lines = [
        f"You are agent {my_agent_id}, role {role_label}, on the {my_side.upper()} team.",
        f"Phase {phase} · mode {mode} · period {period} · ~{int(time_left)}s of game-time left in period.",
        f"Score: you {my_goals} - {their_goals} them ({score_state}, diff {diff:+d}).",
    ]

    if derived:
        # Trust the pre-computed football read.
        for key, label in (
            ("possession", "possession"), ("reachAdvantageMeters", "reach advantage (m)"),
            ("defendersBack", "defenders back"), ("exposedToCounter", "exposed to counter"),
            ("openPost", "open post"), ("threat", "threat"), ("opportunity", "opportunity"),
            ("urgency", "urgency"),
        ):
            if key in derived:
                lines.append(f"- {label}: {derived[key]}")
        if derived.get("yourVoteIgnored"):
            lines.append("- NOTE: your last team-tactics vote was OUTVOTED — arguing via SEND_TEAM_MESSAGE beats re-sending it.")
    else:
        # Fallback compact raw view (no derived block yet).
        ball = status.get("ball", {}) or {}
        carrier = ball.get("carrierAgentId")
        lines.append(f"- ball free: {ball.get('isFree', True)}  nearestCarrier: {carrier or 'none'}")
        if me:
            lines.append(f"- you: boost {int(me.get('boost', 0))}  role {me.get('role')}  action {me.get('action')}")

    lines.append("Reply with ONE command as JSON (commandType, parameters, rationale<=200). Only act if something CHANGED.")
    return "\n".join(lines)


def _same_side(bike: dict, my_side: str) -> bool:
    team = str(bike.get("team", "")).lower()
    return team == my_side or team == ("home" if my_side == "home" else "away")
