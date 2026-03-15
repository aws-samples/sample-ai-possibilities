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
# Memory mock — extends mock_agentcore with memory module stubs
# ---------------------------------------------------------------------------

class _FakeAgentCoreMemoryConfig:
    """Minimal stand-in for AgentCoreMemoryConfig."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeAgentCoreMemorySessionManager:
    """Minimal stand-in for AgentCoreMemorySessionManager."""
    def __init__(self, **kwargs):
        pass

    def register_hooks(self, registry):
        """No-op hook registration for test compatibility with Strands Agent."""
        pass


def mock_agentcore_memory():
    """Inject fake bedrock_agentcore + memory modules for memory-enabled agents.

    Call this INSTEAD of mock_agentcore() when testing memory agents.
    """
    mock_agentcore()

    mem_mod = type(sys)("bedrock_agentcore.memory")
    integ_mod = type(sys)("bedrock_agentcore.memory.integrations")
    strands_mod = type(sys)("bedrock_agentcore.memory.integrations.strands")
    config_mod = type(sys)("bedrock_agentcore.memory.integrations.strands.config")
    session_mod = type(sys)("bedrock_agentcore.memory.integrations.strands.session_manager")

    strands_mod.AgentCoreMemorySessionManager = _FakeAgentCoreMemorySessionManager
    config_mod.AgentCoreMemoryConfig = _FakeAgentCoreMemoryConfig

    sys.modules["bedrock_agentcore.memory"] = mem_mod
    sys.modules["bedrock_agentcore.memory.integrations"] = integ_mod
    sys.modules["bedrock_agentcore.memory.integrations.strands"] = strands_mod
    sys.modules["bedrock_agentcore.memory.integrations.strands.config"] = config_mod
    sys.modules["bedrock_agentcore.memory.integrations.strands.session_manager"] = session_mod


# ---------------------------------------------------------------------------
# Gateway mock — stubs out MCP client so gateway agents can import cleanly
# ---------------------------------------------------------------------------

class _FakeMCPClient:
    """Minimal stand-in for strands MCPClient."""
    def __init__(self, transport_factory=None):
        pass

    def list_tools_sync(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def mock_agentcore_gateway():
    """Inject fake bedrock_agentcore + MCP modules for gateway-enabled agents.

    Call this INSTEAD of mock_agentcore() when testing gateway agents.
    """
    mock_agentcore()

    # Mock MCP client modules
    mcp_mod = type(sys)("mcp")
    mcp_client_mod = type(sys)("mcp.client")
    mcp_http_mod = type(sys)("mcp.client.streamable_http")
    mcp_http_mod.streamablehttp_client = lambda *a, **kw: None

    sys.modules["mcp"] = mcp_mod
    sys.modules["mcp.client"] = mcp_client_mod
    sys.modules["mcp.client.streamable_http"] = mcp_http_mod

    # Mock strands MCP tools
    strands_tools_mod = type(sys)("strands.tools.mcp")
    strands_mcp_client_mod = type(sys)("strands.tools.mcp.mcp_client")
    strands_mcp_client_mod.MCPClient = _FakeMCPClient

    sys.modules.setdefault("strands.tools", type(sys)("strands.tools"))
    sys.modules["strands.tools.mcp"] = strands_tools_mod
    sys.modules["strands.tools.mcp.mcp_client"] = strands_mcp_client_mod


# ---------------------------------------------------------------------------
# Sample game state — shared across all agent tests
# ---------------------------------------------------------------------------

TEAM_ID = 0

GAME_STATE = {
    "tick": 150, "gameTime": 120.5, "playMode": "OPEN_PLAY",
    "modeTeamId": None,
    "score": {"home": 1, "away": 0},
    "ball": {
        "position": {"x": 15.3, "y": -5.2, "z": 0}, "velocity": {"x": 0, "y": 0, "z": 0},
        "isFree": False, "possessionAgentId": "agentId_3",
        "rotation": {}, "angularVelocity": {},
    },
    "players": [
        {"agentId": "agentId_0", "teamCode": "home", "position": {"x": -50, "y": 0}, "velocity": {"x": 0, "y": 0}, "orientation": 0, "stamina": 0.95, "currentAction": 0, "lastAction": "StayNearGoal", "speed": 0, "isSprinting": False},
        {"agentId": "agentId_1", "teamCode": "home", "position": {"x": -10, "y": 12}, "velocity": {"x": 1, "y": 0}, "orientation": 0, "stamina": 0.80, "currentAction": 1, "lastAction": "CoachMoveTo", "speed": 1.0, "isSprinting": False},
        {"agentId": "agentId_2", "teamCode": "home", "position": {"x": 5, "y": -8}, "velocity": {"x": 0, "y": 0}, "orientation": 0, "stamina": 0.70, "currentAction": 0, "lastAction": "RoamRandomly", "speed": 0, "isSprinting": False},
        {"agentId": "agentId_3", "teamCode": "home", "position": {"x": 14, "y": -5}, "velocity": {"x": 2, "y": 0}, "orientation": 0, "stamina": 0.65, "currentAction": 5, "lastAction": "DribbleTo", "speed": 1.5, "isSprinting": True},
        {"agentId": "agentId_4", "teamCode": "home", "position": {"x": 20, "y": 15}, "velocity": {"x": 0, "y": -1}, "orientation": 0, "stamina": 0.85, "currentAction": 1, "lastAction": "FindOpenSpace", "speed": 1.0, "isSprinting": False},
        {"agentId": "agentId_0", "teamCode": "away", "position": {"x": 50, "y": 0}, "velocity": {"x": 0, "y": 0}, "orientation": 0, "stamina": 0.95, "currentAction": 0, "lastAction": "StayNearGoal", "speed": 0, "isSprinting": False},
        {"agentId": "agentId_1", "teamCode": "away", "position": {"x": 10, "y": -3}, "velocity": {"x": -1, "y": 0}, "orientation": 0, "stamina": 0.75, "currentAction": 1, "lastAction": "CoachMoveTo", "speed": 1.0, "isSprinting": False},
        {"agentId": "agentId_2", "teamCode": "away", "position": {"x": 25, "y": 10}, "velocity": {"x": 0, "y": 0}, "orientation": 0, "stamina": 0.80, "currentAction": 0, "lastAction": "MoveToTarget", "speed": 0, "isSprinting": False},
        {"agentId": "agentId_3", "teamCode": "away", "position": {"x": 30, "y": -12}, "velocity": {"x": 0, "y": 0}, "orientation": 0, "stamina": 0.90, "currentAction": 0, "lastAction": "InterceptBallCarrier", "speed": 0, "isSprinting": False},
        {"agentId": "agentId_4", "teamCode": "away", "position": {"x": 35, "y": 5}, "velocity": {"x": -2, "y": 0}, "orientation": 0, "stamina": 0.70, "currentAction": 1, "lastAction": "FindOpenSpace", "speed": 1.5, "isSprinting": True},
    ],
    "teamChat": [],
}
