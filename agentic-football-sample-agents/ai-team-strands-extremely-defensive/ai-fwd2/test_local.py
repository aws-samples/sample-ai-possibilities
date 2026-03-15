"""Local test for the FWD2 agent (Extremely Defensive) — tests state summary, parsing, fallback, and LLM."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from test_helpers import mock_agentcore, GAME_STATE, TEAM_ID
mock_agentcore()

from state import summarize_state
from parsing import parse_commands
from main import fallback_commands, MY_PLAYER_ID, POSITION_LABEL, SYSTEM_PROMPT


def test_summarize():
    print(f"=== STATE SUMMARY ({POSITION_LABEL}, player {MY_PLAYER_ID}) ===")
    summary = summarize_state(GAME_STATE, TEAM_ID, MY_PLAYER_ID, POSITION_LABEL)
    print(summary)
    print()


def test_fallback():
    """FWD2 doesn't have ball, teammate FWD1 does — should MOVE_TO attacking position."""
    print(f"=== FALLBACK ({POSITION_LABEL}) ===")
    cmds = fallback_commands(GAME_STATE, TEAM_ID, MY_PLAYER_ID)
    for c in cmds:
        pid = c.get("playerId")
        tid = c.get("teamId")
        ok = "OK" if pid == MY_PLAYER_ID and tid == TEAM_ID else "WRONG"
        print(f"  [{ok}] P{pid} T{tid}: {c['commandType']} {c.get('parameters', {})}")
    assert all(c["playerId"] == MY_PLAYER_ID for c in cmds), "FAIL: wrong playerId"
    assert all(c["teamId"] == TEAM_ID for c in cmds), "FAIL: wrong teamId"
    print(f"  All {len(cmds)} commands correct")
    print()


def test_fallback_shoot():
    """FWD2 has ball near opponent goal — should SHOOT."""
    print(f"=== FALLBACK SHOOT ({POSITION_LABEL}) ===")
    state = json.loads(json.dumps(GAME_STATE))
    state["ball"]["possessionAgentId"] = f"agentId_{MY_PLAYER_ID}"
    state["players"][4]["position"] = {"x": 40, "y": 8}  # near opp goal
    cmds = fallback_commands(state, TEAM_ID, MY_PLAYER_ID)
    for c in cmds:
        print(f"  P{c['playerId']}: {c['commandType']} {c.get('parameters', {})}")
    assert cmds[0]["commandType"] == "SHOOT", f"FAIL: expected SHOOT, got {cmds[0]['commandType']}"
    assert cmds[0]["parameters"]["aim_location"] == "BL", "FAIL: FWD2 should aim BL"
    print(f"  Correctly shoots (aim BL) near goal")
    print()


def test_fallback_advance():
    """FWD2 has ball far from goal — should advance with MOVE_TO."""
    print(f"=== FALLBACK ADVANCE ({POSITION_LABEL}) ===")
    state = json.loads(json.dumps(GAME_STATE))
    state["ball"]["possessionAgentId"] = f"agentId_{MY_PLAYER_ID}"
    state["players"][4]["position"] = {"x": 10, "y": 8}  # far from goal
    cmds = fallback_commands(state, TEAM_ID, MY_PLAYER_ID)
    for c in cmds:
        print(f"  P{c['playerId']}: {c['commandType']} {c.get('parameters', {})}")
    assert cmds[0]["commandType"] == "MOVE_TO", f"FAIL: expected MOVE_TO, got {cmds[0]['commandType']}"
    assert cmds[0]["parameters"]["sprint"] == True, "FAIL: should sprint when advancing"
    print(f"  Correctly advances with sprint on right side")
    print()


def test_parse():
    print("=== PARSE TESTS ===")
    tests = [
        ('[{"commandType":"SHOOT","playerId":4,"parameters":{"aim_location":"BL","power":0.9},"duration":0}]', 1),
        ('[{"commandType":"MOVE_TO","playerId":4,"parameters":{"target_x":33,"target_y":8,"sprint":true},"duration":0}]', 1),
        ("invalid json", 0),
        ('[]', 0),
    ]
    all_pass = True
    for resp, expected in tests:
        cmds = parse_commands(resp, TEAM_ID, MY_PLAYER_ID)
        ok = len(cmds) == expected
        if cmds:
            ok = ok and all(c["playerId"] == MY_PLAYER_ID for c in cmds)
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] '{resp[:60]}...' -> {len(cmds)} cmds (expected {expected})")
    if all_pass:
        print("  All parse tests passed")
    print()


def test_llm():
    print(f"=== LLM TEST ({POSITION_LABEL}) ===")
    try:
        from strands import Agent
        from strands.models import BedrockModel

        model = BedrockModel(model_id="us.amazon.nova-lite-v1:0")
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

        summary = summarize_state(GAME_STATE, TEAM_ID, MY_PLAYER_ID, POSITION_LABEL)
        print(f"Sending to Nova Lite ({len(summary)} chars)...")

        response = agent(summary)
        response_text = str(response)
        print(f"\nRaw response ({len(response_text)} chars):")
        print(response_text[:500])
        print()

        cmds = parse_commands(response_text, TEAM_ID, MY_PLAYER_ID)
        print(f"Parsed {len(cmds)} commands:")
        for c in cmds:
            print(f"  P{c.get('playerId')}: {c.get('commandType')} {c.get('parameters', {})}")

        if cmds and all(c["playerId"] == MY_PLAYER_ID for c in cmds):
            print(f"\nLLM test PASSED — all commands for player {MY_PLAYER_ID}")
        else:
            print("\nLLM test FAILED")

    except Exception as e:
        print(f"LLM test error: {e}")


if __name__ == "__main__":
    test_summarize()
    test_fallback()
    test_fallback_shoot()
    test_fallback_advance()
    test_parse()

    if "--llm" in sys.argv:
        test_llm()
    else:
        print("Skipping LLM test. Run with --llm to test.")
