"""Local test for the FWD1 (Gateway) agent — tests state summary, parsing, and fallback."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from test_helpers import mock_agentcore_gateway, GAME_STATE, TEAM_ID
os.environ.setdefault("GATEWAY_URL", "https://test-gateway.example.com")
os.environ.setdefault("GATEWAY_ACCESS_TOKEN", "test-token")
mock_agentcore_gateway()

from state import summarize_state
from parsing import parse_commands
from fallback import build_fallback, FWD1_CONFIG

MY_PLAYER_ID = 3
POSITION_LABEL = "FWD1"
fallback_commands = build_fallback(FWD1_CONFIG)


def test_summarize():
    print(f"=== STATE SUMMARY ({POSITION_LABEL}, player {MY_PLAYER_ID}) ===")
    summary = summarize_state(GAME_STATE, TEAM_ID, MY_PLAYER_ID, POSITION_LABEL)
    print(summary)
    print()


def test_fallback():
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


def test_parse():
    print("=== PARSE TESTS ===")
    tests = [
        ('[{"commandType":"SHOOT","playerId":3,"parameters":{"aim_location":"TR","power":0.9},"duration":0}]', 1),
        ("invalid json", 0),
    ]
    for resp, expected in tests:
        cmds = parse_commands(resp, TEAM_ID, MY_PLAYER_ID)
        status = "PASS" if len(cmds) == expected else "FAIL"
        print(f"  [{status}] '{resp[:50]}...' -> {len(cmds)} cmds (expected {expected})")
    print()


if __name__ == "__main__":
    test_summarize()
    test_fallback()
    test_parse()
    print("Gateway agent local tests passed (no Gateway/LLM calls).")
