"""Local smoke test for the SUPPORT ship agent — no AWS, no network.

Verifies the shared lib imports through this agent's path setup and that the rule-based fallback
(used when the LLM is unavailable) still produces a valid opening command for this role. The full
lib unit-test suite lives in ../../lib/test_lib.py.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from prompt import system_prompt_for
from fallback import opening_commands
from parsing import parse_command, VALID_COMMANDS

ROLE_LABEL = "SUPPORT"


def test_prompt_mentions_role_and_vote():
    p = system_prompt_for(ROLE_LABEL)
    assert ROLE_LABEL in p and "TEAM TACTICS ARE A VOTE" in p


def test_fallback_opening_is_a_valid_command():
    cmd = opening_commands("starter-x", "TEAMCODE", ROLE_LABEL, 0)
    assert cmd["commandType"] in VALID_COMMANDS
    assert cmd["agentId"] == "starter-x" and cmd["teamCode"] == "TEAMCODE"


def test_roundtrip_fallback_parses_back():
    import json
    cmd = opening_commands("starter-x", "TEAMCODE", ROLE_LABEL, 1)
    reparsed = parse_command(json.dumps(cmd), "starter-x", "TEAMCODE")
    assert reparsed is not None and reparsed["commandType"] == cmd["commandType"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed ({ROLE_LABEL})")
