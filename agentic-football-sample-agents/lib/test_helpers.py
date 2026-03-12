"""Shared test helpers for AI soccer agent local tests.

Provides:
  - mock_agentcore()  — stubs out bedrock_agentcore so agents can import without it
  - GAME_STATE        — a realistic sample game state used by all tests
  - TEAM_ID           — default team for tests (0 = HOME)
"""

import sys


# ---------------------------------------------------------------------------
# AgentCore mock — must be called BEFORE importing any agent code
# ---------------------------------------------------------------------------

class _FakeApp:
    """Minimal stand-in for BedrockAgentCoreApp."""
    class logger:
        @staticmethod
        def info(msg): print(f"  [INFO] {msg}")
        @staticmethod
        def warn(msg): print(f"  [WARN] {msg}")
        @staticmethod
        def error(msg): print(f"  [ERROR] {msg}")
    def entrypoint(self, fn): return fn
    def run(self): pass


def mock_agentcore():
    """Inject fake bedrock_agentcore modules so agent code can import cleanly."""
    sys.modules["bedrock_agentcore"] = type(sys)("bedrock_agentcore")
    sys.modules["bedrock_agentcore.runtime"] = type(sys)("bedrock_agentcore.runtime")
    sys.modules["bedrock_agentcore.runtime"].BedrockAgentCoreApp = _FakeApp


# ---------------------------------------------------------------------------
# Sample game state — shared across all agent tests
# ---------------------------------------------------------------------------

TEAM_ID = 0

GAME_STATE = {
    "tick": 150, "gameTime": 120.5, "playMode": 0,
    "score": {"home": 1, "away": 0},
    "ball": {
        "position": {"x": 15.3, "y": -5.2, "z": 0},
        "velocity": {"x": 0, "y": 0, "z": 0},
        "isFree": False, "possessionPlayerId": 3,
    },
    "players": [
        {"playerId": 0, "teamId": 0, "position": {"x": -50, "y": 0}, "stamina": 95},
        {"playerId": 1, "teamId": 0, "position": {"x": -10, "y": 12}, "stamina": 80},
        {"playerId": 2, "teamId": 0, "position": {"x": 5, "y": -8}, "stamina": 70},
        {"playerId": 3, "teamId": 0, "position": {"x": 14, "y": -5}, "stamina": 65},
        {"playerId": 4, "teamId": 0, "position": {"x": 20, "y": 15}, "stamina": 85},
        {"playerId": 0, "teamId": 1, "position": {"x": 50, "y": 0}, "stamina": 95},
        {"playerId": 1, "teamId": 1, "position": {"x": 10, "y": -3}, "stamina": 75},
        {"playerId": 2, "teamId": 1, "position": {"x": 25, "y": 10}, "stamina": 80},
        {"playerId": 3, "teamId": 1, "position": {"x": 30, "y": -12}, "stamina": 90},
        {"playerId": 4, "teamId": 1, "position": {"x": 35, "y": 5}, "stamina": 70},
    ],
}
