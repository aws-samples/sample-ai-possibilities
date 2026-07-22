"""Rule-based fallback policies for Space Football agents.

When the LLM fails to produce a valid command, the agent still needs to play competently. Each
cycle the fallback issues ONE sensible standing-policy command (space football is one-command-per-
cycle). The opening cycles set the ship's role, a middle-of-the-road tactics vote, and the two
insurance contingencies from STARTER_AGENT_PROMPT (trailing-late / leading-late) so the team
reacts to a late goal instantly even with a slow model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleProfile:
    """Per-slot opening policy (the starter squad's defensible middle-of-the-road defaults)."""
    role: str            # KEEPER/SWEEPER/SUPPORT/RUNNER/STRIKER
    aggression: float    # this ship's own chase appetite
    keeper_aggression: float


# Slot 0..4 → opening role, mirroring the roster's DefaultRole ordering.
PROFILES = {
    "KEEPER":  RoleProfile("KEEPER", 0.20, 0.40),
    "SWEEPER": RoleProfile("SWEEPER", 0.35, 0.40),
    "SUPPORT": RoleProfile("SUPPORT", 0.50, 0.40),
    "RUNNER":  RoleProfile("RUNNER", 0.65, 0.40),
    "STRIKER": RoleProfile("STRIKER", 0.80, 0.40),
}


def opening_commands(agent_id: str, team_code: str, role_label: str, cycle: int) -> dict:
    """Return ONE command for this cycle — role first, then vote, then the two contingencies.

    cycle 0 → SET_BIKE_ROLE, 1 → SET_TEAM_TACTICS, 2 → trailing-late contingency,
    3 → leading-late contingency, 4+ → a steady team-tactics vote (idempotent, no spam).
    """
    prof = PROFILES.get(role_label.upper(), PROFILES["SUPPORT"])

    if cycle == 0:
        return _cmd(agent_id, team_code, "SET_BIKE_ROLE",
                    {"agentId": agent_id, "role": prof.role},
                    f"take my slot as {prof.role.lower()}")
    if cycle == 1:
        return _cmd(agent_id, team_code, "SET_TEAM_TACTICS",
                    {"aggression": 0.5, "defensiveLine": "MID", "keeperAggression": prof.keeper_aggression,
                     "shotBias": "FAR_POST", "dashUse": "BALANCED", "width": 0.5},
                    "neutral opening: threaten without overcommitting")
    if cycle == 2:
        return _cmd(agent_id, team_code, "SET_CONTINGENCY",
                    {"trigger": "TRAILING_LATE", "aggression": 0.9, "defensiveLine": "HIGH", "dashUse": "CHASE"},
                    "insurance: chase hard if trailing late")
    if cycle == 3:
        return _cmd(agent_id, team_code, "SET_CONTINGENCY",
                    {"trigger": "LEADING_LATE", "aggression": 0.2, "defensiveLine": "DEEP",
                     "keeperAggression": 0.7, "dashUse": "DEFEND"},
                    "insurance: shut it down if leading late")
    # Steady state: re-affirm a role-appropriate vote (median-safe, not spam).
    return _cmd(agent_id, team_code, "SET_TEAM_TACTICS",
                {"aggression": prof.aggression, "defensiveLine": "MID", "dashUse": "BALANCED"},
                "hold shape")


def last_resort(agent_id: str, team_code: str) -> dict:
    """Absolute floor when even the fallback context is unavailable — a harmless role affirmation."""
    return _cmd(agent_id, team_code, "SET_BIKE_ROLE",
                {"agentId": agent_id, "role": "FREE"}, "safe default")


def _cmd(agent_id: str, team_code: str, command_type: str, parameters: dict, rationale: str) -> dict:
    return {"agentId": agent_id, "teamCode": team_code, "commandType": command_type,
            "parameters": parameters, "rationale": rationale[:200]}
