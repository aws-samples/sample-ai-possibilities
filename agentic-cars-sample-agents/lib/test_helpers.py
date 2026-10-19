"""Shared helpers for the agents' local tests.

  - mock_agentcore()  stubs bedrock_agentcore so an agent module imports without the runtime installed
  - GAME_STATE        a real relay /match/{id}/status snapshot from a sandbox match (team codes anonymised)
  - TEAM_CODE / AGENT_ID / ATTACKING_Z   the home side of that snapshot
"""

import json
import sys
import types

TEAM_CODE = "HOME1"
AGENT_ID = "HOME1-1"
ATTACKING_Z = 1


class _FakeApp:
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
    """Inject a fake bedrock_agentcore.runtime so agent code imports cleanly without the SDK."""
    runtime = types.ModuleType("bedrock_agentcore.runtime")
    runtime.BedrockAgentCoreApp = _FakeApp
    pkg = types.ModuleType("bedrock_agentcore")
    pkg.runtime = runtime
    sys.modules.setdefault("bedrock_agentcore", pkg)
    sys.modules.setdefault("bedrock_agentcore.runtime", runtime)


GAME_STATE = json.loads('''
{
  "tick": 1075,
  "gameTime": 43.040794,
  "playMode": "OPEN_PLAY",
  "score": {
    "home": 0,
    "away": 0
  },
  "ball": {
    "position": {
      "x": -24.46161,
      "y": 0.9599999,
      "z": 19.860186
    },
    "velocity": {
      "x": -6.259219,
      "y": -2.3543835e-06,
      "z": -15.392977
    },
    "rotation": {
      "x": 351.1365,
      "y": 294.0689,
      "z": 267.97324
    },
    "angularVelocity": {
      "x": -8.426401,
      "y": 3.164187,
      "z": 3.4264176
    },
    "isFree": true,
    "controllerCarId": null
  },
  "cars": [
    {
      "teamCode": "HOME1",
      "agentId": "HOME1-1",
      "position": {
        "x": -8.194836,
        "y": 0.4000002,
        "z": -16.854439
      },
      "velocity": {
        "x": 3.6503022,
        "y": 0,
        "z": -3.2630084
      },
      "rotation": {
        "x": 0,
        "y": 303.16278,
        "z": 0
      },
      "steerAngle": 35,
      "speed": -4.4253235,
      "role": "GOALKEEPER",
      "isDribbling": false
    },
    {
      "teamCode": "HOME1",
      "agentId": "HOME1-2",
      "position": {
        "x": -16.50777,
        "y": 0.40000013,
        "z": 14.991811
      },
      "velocity": {
        "x": 26.726606,
        "y": -1.206994e-06,
        "z": 10.457952
      },
      "rotation": {
        "x": 0,
        "y": 95.7231,
        "z": 0
      },
      "steerAngle": 35,
      "speed": 25.547098,
      "role": "DEFENDER",
      "isDribbling": false
    },
    {
      "teamCode": "HOME1",
      "agentId": "HOME1-3",
      "position": {
        "x": -24.989758,
        "y": 0.40098873,
        "z": 24.187452
      },
      "velocity": {
        "x": -4.1447635,
        "y": 0,
        "z": -15.266385
      },
      "rotation": {
        "x": 359.9678,
        "y": 199.42305,
        "z": 0.021139443
      },
      "steerAngle": 0.47298792,
      "speed": 15.774802,
      "role": "STRIKER",
      "isDribbling": false
    },
    {
      "teamCode": "HOME1",
      "agentId": "HOME1-4",
      "position": {
        "x": -19.34141,
        "y": 0.40000033,
        "z": 29.183416
      },
      "velocity": {
        "x": 0.031405274,
        "y": 0,
        "z": -12.402595
      },
      "rotation": {
        "x": 0,
        "y": 164.8751,
        "z": 0
      },
      "steerAngle": -35,
      "speed": 12.172822,
      "role": "STRIKER",
      "isDribbling": false
    },
    {
      "teamCode": "HOME1",
      "agentId": "HOME1-5",
      "position": {
        "x": -2.5359447,
        "y": 0.40001738,
        "z": 40.142956
      },
      "velocity": {
        "x": -11.282653,
        "y": -1.0296702e-05,
        "z": 6.9846954
      },
      "rotation": {
        "x": 0.00049784576,
        "y": 279.74554,
        "z": -0.0004887045
      },
      "steerAngle": -35,
      "speed": 12.054393,
      "role": "STRIKER",
      "isDribbling": false
    },
    {
      "teamCode": "AWAY1",
      "agentId": "AWAY1-1",
      "position": {
        "x": -10.834216,
        "y": 0.4065753,
        "z": 39.840725
      },
      "velocity": {
        "x": -9.511671,
        "y": -0.25106472,
        "z": -5.393734
      },
      "rotation": {
        "x": 0,
        "y": 228.95145,
        "z": 0
      },
      "steerAngle": -35,
      "speed": 10.68442,
      "role": "GOALKEEPER",
      "isDribbling": false
    },
    {
      "teamCode": "AWAY1",
      "agentId": "AWAY1-2",
      "position": {
        "x": -11.41784,
        "y": 0.40012455,
        "z": 36.20754
      },
      "velocity": {
        "x": 13.803908,
        "y": 2.9802322e-08,
        "z": 2.3918235
      },
      "rotation": {
        "x": -0.0027752747,
        "y": 92.3615,
        "z": 0.005140622
      },
      "steerAngle": 35,
      "speed": 14.530978,
      "role": "DEFENDER",
      "isDribbling": false
    },
    {
      "teamCode": "AWAY1",
      "agentId": "AWAY1-3",
      "position": {
        "x": -23.185076,
        "y": 0.40000004,
        "z": 22.552044
      },
      "velocity": {
        "x": -2.3652446,
        "y": 0,
        "z": -15.608903
      },
      "rotation": {
        "x": 0,
        "y": 190.78502,
        "z": 0
      },
      "steerAngle": 2.0189636,
      "speed": 15.775888,
      "role": "SUPPORT",
      "isDribbling": false
    },
    {
      "teamCode": "AWAY1",
      "agentId": "AWAY1-4",
      "position": {
        "x": 24.446135,
        "y": 0.3992498,
        "z": 37.476326
      },
      "velocity": {
        "x": -0.005492687,
        "y": -0.000119656324,
        "z": 0.79685915
      },
      "rotation": {
        "x": -2.2119273e-05,
        "y": 51.72639,
        "z": 0.0012576699
      },
      "steerAngle": -6.9195957,
      "speed": 0.4892916,
      "role": "STRIKER",
      "isDribbling": false
    },
    {
      "teamCode": "AWAY1",
      "agentId": "AWAY1-5",
      "position": {
        "x": -14.561905,
        "y": 0.40000004,
        "z": 8.805652
      },
      "velocity": {
        "x": -16.910038,
        "y": -4.7683716e-06,
        "z": -1.3712559
      },
      "rotation": {
        "x": 0,
        "y": 244.71231,
        "z": 0
      },
      "steerAngle": -16.382372,
      "speed": 15.844453,
      "role": "STRIKER",
      "isDribbling": false
    }
  ],
  "teamChat": [],
  "currentPhase": "PLAYING",
  "homeTeamCode": "HOME1"
}
''')
