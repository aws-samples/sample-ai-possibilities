"""Local test for the goalkeeper agent: briefing, fallback and parsing offline; --llm calls the model."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from test_helpers import mock_agentcore, GAME_STATE, TEAM_CODE, ATTACKING_Z
mock_agentcore()

import fallback
from parsing import parse_commands
from state import summarize_state
from main import ROLE, TEAM_VARIANT, MODEL_ID, SYSTEM_PROMPT

AGENT_ID = "HOME1-1"


def test_briefing():
    print(f"=== BRIEFING ({ROLE}, {AGENT_ID}) ===")
    briefing = summarize_state(GAME_STATE, TEAM_CODE, AGENT_ID, ROLE, ATTACKING_Z, ["press high"], 120)
    print(briefing)
    assert ROLE in briefing and "Coach instructions" in briefing
    print()


def test_fallback():
    print(f"=== FALLBACK ({TEAM_VARIANT}) ===")
    opening = fallback.opening_command(AGENT_ID, TEAM_CODE, TEAM_VARIANT, 0)
    moment = fallback.moment_command(GAME_STATE, AGENT_ID, TEAM_CODE, ROLE, ATTACKING_Z)
    for c in (opening, moment):
        if c:
            print(f"  {c['commandType']} {c['parameters']}")
            assert c["agentId"] == AGENT_ID and c["teamCode"] == TEAM_CODE
    assert opening["commandType"] == "SET_TEAM_STANCE"
    print()


def test_parse():
    print("=== PARSE ===")
    cases = [
        ('[{"commandType":"SET_PRESSING","parameters":{"level":"high"}}, {"commandType":"SHOOT","parameters":{"aim_location":"TL","power":0.9}}]', ["SET_PRESSING", "SHOOT"]),
        ('Sure: [{"commandType":"MOVE_TO","parameters":{"target_x":500,"target_y":-900}}]', ["MOVE_TO"]),
        ('[{"commandType":"INTERCEPT","parameters":{"aggressive":True}}]', ["INTERCEPT"]),
        ("no json here", []),
    ]
    for text, expected in cases:
        cmds = parse_commands(text, AGENT_ID, TEAM_CODE)
        got = [c["commandType"] for c in cmds]
        assert got == expected, f"{text[:40]} -> {got} (expected {expected})"
        assert all(c["agentId"] == AGENT_ID and c["teamCode"] == TEAM_CODE for c in cmds)
        print(f"  [PASS] {text[:50]}... -> {got}")
    print()


def test_llm():
    print(f"=== LLM ({MODEL_ID}) ===")
    from strands import Agent
    from strands.models import BedrockModel

    agent = Agent(model=BedrockModel(model_id=MODEL_ID), system_prompt=SYSTEM_PROMPT, callback_handler=None)
    briefing = summarize_state(GAME_STATE, TEAM_CODE, AGENT_ID, ROLE, ATTACKING_Z, None, 120)
    text = str(agent(briefing))
    print(text[:400])
    cmds = parse_commands(text, AGENT_ID, TEAM_CODE)
    print(f"Parsed: {json.dumps(cmds)}")
    assert cmds, "the model returned no valid command"
    print("LLM test PASSED")


if __name__ == "__main__":
    test_briefing()
    test_fallback()
    test_parse()
    if "--llm" in sys.argv:
        test_llm()
    else:
        print("Skipping the LLM test. Run with --llm (needs AWS credentials and Bedrock model access).")
