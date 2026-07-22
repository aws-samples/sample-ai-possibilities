"""Offline unit tests for the Space Football agent lib (no relay / AgentCore / network needed).

Run: python3 -m pytest lib/test_lib.py   (or: python3 lib/test_lib.py)
Gates the command-shape contract the deployed agents rely on.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import fallback
import parsing
from prompt import system_prompt_for
from state import summarize_state


def test_parse_wellformed_and_normalises_enums():
    c = parsing.parse_command(
        '{"commandType":"SET_TEAM_TACTICS","parameters":{"aggression":0.9,"defensiveLine":"high",'
        '"shotBias":"CENTRE","dashUse":"chase","width":2},"rationale":"push"}', "red-5", "REDCODE")
    assert c["commandType"] == "SET_TEAM_TACTICS"
    assert c["agentId"] == "red-5" and c["teamCode"] == "REDCODE"
    assert c["parameters"]["defensiveLine"] == "HIGH"     # upper-cased
    assert c["parameters"]["dashUse"] == "CHASE"
    assert c["parameters"]["width"] == 1.0                # clamped 0..1
    assert len(c["rationale"]) <= 200


def test_parse_from_prose_and_array():
    c = parsing.parse_command('Sure! [{"commandType":"SET_BIKE_ROLE","parameters":{"role":"striker"}}] ok', "r1", "RC")
    assert c["commandType"] == "SET_BIKE_ROLE" and c["parameters"]["role"] == "STRIKER"


def test_parse_rejects_unknown_and_junk():
    assert parsing.parse_command("no json", "a", "B") is None
    assert parsing.parse_command('{"commandType":"FLY_TO_MOON","parameters":{}}', "a", "B") is None


def test_parse_drops_out_of_domain_enum():
    c = parsing.parse_command('{"commandType":"SET_TEAM_TACTICS","parameters":{"defensiveLine":"SIDEWAYS"}}', "a", "B")
    assert "defensiveLine" not in c["parameters"]         # omitted = "no opinion"


def test_fallback_opening_sequence():
    seq = [fallback.opening_commands("r1", "RC", "STRIKER", n)["commandType"] for n in range(5)]
    assert seq == ["SET_BIKE_ROLE", "SET_TEAM_TACTICS", "SET_CONTINGENCY", "SET_CONTINGENCY", "SET_TEAM_TACTICS"]


def test_fallback_contingencies_are_valid_triggers():
    c2 = fallback.opening_commands("r1", "RC", "SUPPORT", 2)
    c3 = fallback.opening_commands("r1", "RC", "SUPPORT", 3)
    assert c2["parameters"]["trigger"] == "TRAILING_LATE"
    assert c3["parameters"]["trigger"] == "LEADING_LATE"


def test_fallback_stamps_identity_and_short_rationale():
    for role in ("KEEPER", "SWEEPER", "SUPPORT", "RUNNER", "STRIKER"):
        c = fallback.opening_commands("blu-3", "BLUCODE", role, 0)
        assert c["agentId"] == "blu-3" and c["teamCode"] == "BLUCODE"
        assert len(c["rationale"]) <= 200


def test_state_summary_detects_score_state_and_uses_derived():
    s = summarize_state({"phase": "PeriodActive", "mode": "STRIKE", "period": 1, "periodTimeLeft": 30,
                         "score": {"home": 1, "away": 3}, "homeTeamCode": "REDCODE", "awayTeamCode": "BLUCODE",
                         "derived": {"possession": "them", "openPost": "near", "threat": "counter"}},
                        "REDCODE", "red-1", "STRIKER")
    assert "TRAILING" in s and "open post" in s and "you 1 - 3 them" in s


def test_system_prompt_has_role_note():
    p = system_prompt_for("KEEPER")
    assert "TEAM TACTICS ARE A VOTE" in p and "KEEPER" in p


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
