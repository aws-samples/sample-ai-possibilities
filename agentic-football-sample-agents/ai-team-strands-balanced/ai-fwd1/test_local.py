"""Local test for the FWD1 agent — tests state summary, parsing, fallback, and LLM."""

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
    """FWD1 has the ball at x=14 — far from goal, should MOVE_TO toward goal."""
    print(f"=== FALLBACK ({POSITION_LABEL}, has ball) ===")
    cmds = fallback_commands(GAME_STATE, TEAM_ID, MY_PLAYER_ID)
    for c in cmds:
        pid = c.get("playerId")
        tid = c.get("teamId")
        ok = "OK" if pid == MY_PLAYER_ID and tid == TEAM_ID else "WRONG"
        print(f"  [{ok}] P{pid} T{tid}: {c['commandType']} {c.get('parameters', {})}")
    assert all(c["playerId"] == MY_PLAYER_ID for c in cmds), "FAIL: wrong playerId"
    assert all(c["teamId"] == TEAM_ID for c in cmds), "FAIL: wrong teamId"
    assert cmds[0]["commandType"] == "MOVE_TO", f"FAIL: expected MOVE_TO, got {cmds[0]['commandType']}"
    print(f"  Correctly advances toward goal")
    print()


def test_fallback_shoot():
    """FWD1 has ball near opponent goal — should SHOOT."""
    print(f"=== FALLBACK SHOOT ({POSITION_LABEL}) ===")
    state = json.loads(json.dumps(GAME_STATE))
    state["ball"]["possessionAgentId"] = f"agentId_{MY_PLAYER_ID}"
    state["players"][3]["position"] = {"x": 40, "y": -5}  # near opp goal
    cmds = fallback_commands(state, TEAM_ID, MY_PLAYER_ID)
    for c in cmds:
        print(f"  P{c['playerId']}: {c['commandType']} {c.get('parameters', {})}")
    assert cmds[0]["commandType"] == "SHOOT", f"FAIL: expected SHOOT, got {cmds[0]['commandType']}"
    print(f"  Correctly shoots near goal")
    print()


def test_fallback_press():
    """Opponent has ball near FWD1 — should PRESS_BALL."""
    print(f"=== FALLBACK PRESS ({POSITION_LABEL}) ===")
    state = json.loads(json.dumps(GAME_STATE))
    state["ball"]["possessionAgentId"] = "agentId_6"  # opponent has ball
    state["ball"]["position"] = {"x": 18, "y": -3}  # near FWD1
    cmds = fallback_commands(state, TEAM_ID, MY_PLAYER_ID)
    for c in cmds:
        print(f"  P{c['playerId']}: {c['commandType']} {c.get('parameters', {})}")
    assert cmds[0]["commandType"] == "PRESS_BALL", f"FAIL: expected PRESS_BALL, got {cmds[0]['commandType']}"
    print(f"  Correctly presses nearby ball")
    print()


def test_parse():
    print("=== PARSE TESTS ===")
    tests = [
        ('[{"commandType":"SHOOT","playerId":3,"parameters":{"aim_location":"TR","power":0.9},"duration":0}]', 1),
        ('[{"commandType":"MOVE_TO","playerId":3,"parameters":{"target_x":33,"target_y":-8,"sprint":true},"duration":0}]', 1),
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

        model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

        summary = summarize_state(GAME_STATE, TEAM_ID, MY_PLAYER_ID, POSITION_LABEL)
        print(f"Sending to Nova Micro ({len(summary)} chars)...")

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
    test_fallback_press()
    test_parse()

    if "--llm" in sys.argv:
        test_llm()
    else:
        print("Skipping LLM test. Run with --llm to test.")
