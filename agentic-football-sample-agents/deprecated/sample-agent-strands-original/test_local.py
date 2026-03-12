"""Local test for the sample agent — tests state summary, parsing, fallback, and LLM."""

import json
import math
import re
import sys
import os

# Skip AgentCore imports for local testing
sys.modules["bedrock_agentcore"] = type(sys)("bedrock_agentcore")
sys.modules["bedrock_agentcore.runtime"] = type(sys)("bedrock_agentcore.runtime")

class FakeApp:
    class logger:
        @staticmethod
        def info(msg): print(f"  [INFO] {msg}")
        @staticmethod
        def warn(msg): print(f"  [WARN] {msg}")
        @staticmethod
        def error(msg): print(f"  [ERROR] {msg}")
    def entrypoint(self, fn): return fn
    def run(self): pass

sys.modules["bedrock_agentcore.runtime"].BedrockAgentCoreApp = FakeApp

# Now import our agent functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from main import summarize_state, parse_commands, fallback_commands

# --- Sample game state ---
GAME_STATE = {
    "tick": 150,
    "gameTime": 120.5,
    "playMode": 0,
    "score": {"home": 1, "away": 0},
    "ball": {
        "position": {"x": 15.3, "y": -5.2, "z": 0},
        "velocity": {"x": 0, "y": 0, "z": 0},
        "isFree": False,
        "possessionPlayerId": 3,
    },
    "players": [
        {"playerId": 0, "teamId": 0, "position": {"x": -50, "y": 0}, "velocity": {"x": 0, "y": 0}, "stamina": 95, "lastAction": "idle", "orientation": 0, "currentAction": 0, "hasYellowCard": False, "currentStance": "Balanced"},
        {"playerId": 1, "teamId": 0, "position": {"x": -10, "y": 12}, "velocity": {"x": 1, "y": 0}, "stamina": 80, "lastAction": "moving", "orientation": 0, "currentAction": 1, "hasYellowCard": False, "currentStance": "Balanced"},
        {"playerId": 2, "teamId": 0, "position": {"x": 5, "y": -8}, "velocity": {"x": 0, "y": 0}, "stamina": 70, "lastAction": "idle", "orientation": 0, "currentAction": 0, "hasYellowCard": False, "currentStance": "Attack"},
        {"playerId": 3, "teamId": 0, "position": {"x": 14, "y": -5}, "velocity": {"x": 2, "y": 0}, "stamina": 65, "lastAction": "dribbling", "orientation": 0, "currentAction": 5, "hasYellowCard": False, "currentStance": "Attack"},
        {"playerId": 4, "teamId": 0, "position": {"x": 20, "y": 15}, "velocity": {"x": 0, "y": -1}, "stamina": 85, "lastAction": "moving", "orientation": 0, "currentAction": 1, "hasYellowCard": False, "currentStance": "Attack"},
        {"playerId": 0, "teamId": 1, "position": {"x": 50, "y": 0}, "velocity": {"x": 0, "y": 0}, "stamina": 95, "lastAction": "idle", "orientation": 0, "currentAction": 0, "hasYellowCard": False, "currentStance": "Balanced"},
        {"playerId": 1, "teamId": 1, "position": {"x": 10, "y": -3}, "velocity": {"x": -1, "y": 0}, "stamina": 75, "lastAction": "moving", "orientation": 0, "currentAction": 1, "hasYellowCard": False, "currentStance": "Defend"},
        {"playerId": 2, "teamId": 1, "position": {"x": 25, "y": 10}, "velocity": {"x": 0, "y": 0}, "stamina": 80, "lastAction": "idle", "orientation": 0, "currentAction": 0, "hasYellowCard": False, "currentStance": "Balanced"},
        {"playerId": 3, "teamId": 1, "position": {"x": 30, "y": -12}, "velocity": {"x": 0, "y": 0}, "stamina": 90, "lastAction": "idle", "orientation": 0, "currentAction": 0, "hasYellowCard": False, "currentStance": "Balanced"},
        {"playerId": 4, "teamId": 1, "position": {"x": 35, "y": 5}, "velocity": {"x": -2, "y": 0}, "stamina": 70, "lastAction": "moving", "orientation": 0, "currentAction": 1, "hasYellowCard": False, "currentStance": "Attack"},
    ],
}


def test_summarize():
    print("=== GAME STATE SUMMARY (Team 0 - HOME) ===")
    summary = summarize_state(GAME_STATE, 0)
    print(summary)
    print()


def test_fallback():
    print("=== FALLBACK COMMANDS (Team 0) ===")
    cmds = fallback_commands(GAME_STATE, 0)
    for c in cmds:
        print(f"  P{c['playerId']}: {c['commandType']} {c.get('parameters', {})}")
    print(f"  Total: {len(cmds)} commands")
    print()


def test_parse():
    print("=== PARSE TESTS ===")
    tests = [
        ('[{"commandType":"SHOOT","playerId":3,"parameters":{"aim_location":"TR","power":0.9},"duration":0}]', 1),
        ('Here are the commands:\n[{"commandType":"PRESS_BALL","playerId":1,"parameters":{"intensity":0.8},"duration":3}]\nDone!', 1),
        ('{"commandType":"MOVE_TO","playerId":2,"parameters":{"target_x":10,"target_y":5,"sprint":true},"duration":0}', 1),
        ("invalid json response", 0),
        ('[]', 0),
    ]
    for resp, expected in tests:
        cmds = parse_commands(resp, 0)
        status = "PASS" if len(cmds) == expected else "FAIL"
        print(f"  [{status}] '{resp[:50]}...' -> {len(cmds)} commands (expected {expected})")
    print()


def test_llm():
    """Test actual LLM invocation via Strands + Bedrock."""
    print("=== LLM TEST (Nova Micro) ===")
    try:
        from strands import Agent
        from strands.models import BedrockModel

        model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")
        from main import SYSTEM_PROMPT
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

        summary = summarize_state(GAME_STATE, 0)
        print(f"Sending to Nova Micro ({len(summary)} chars)...")

        response = agent(summary)
        response_text = str(response)
        print(f"\nRaw LLM response ({len(response_text)} chars):")
        print(response_text[:500])
        print()

        commands = parse_commands(response_text, 0)
        print(f"Parsed {len(commands)} commands:")
        for c in commands:
            print(f"  P{c.get('playerId', '?')}: {c.get('commandType', '?')} {c.get('parameters', {})}")

        if commands:
            print("\nLLM test PASSED")
        else:
            print("\nLLM test FAILED - no valid commands parsed")

    except Exception as e:
        print(f"LLM test error: {e}")
        print("(Make sure AWS credentials are set: source /tmp/tmp.tmp)")


if __name__ == "__main__":
    test_summarize()
    test_fallback()
    test_parse()

    if "--llm" in sys.argv:
        test_llm()
    else:
        print("Skipping LLM test. Run with --llm to test Nova Micro invocation.")
        print("  source /tmp/tmp.tmp && python test_local.py --llm")
