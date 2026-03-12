# AI Team (Strands) — Per-Position Soccer Agents

Five AI agents that each control a single player in a 5v5 soccer match, built with
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) and deployed to
[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/).

## Architecture

```
agents/
├── lib/            # Shared library (single source of truth, used by all teams)
└── ai-team-strands-balanced/
    ├── ai-gk/          # Goalkeeper  (player 0) — Nova Micro
    ├── ai-def/         # Defender    (player 1) — Nova Lite
    ├── ai-mid/         # Midfielder  (player 2) — Nova Pro
    ├── ai-fwd1/        # Forward 1   (player 3) — Nova Micro
    ├── ai-fwd2/        # Forward 2   (player 4) — Nova Lite
    ├── deploy-all.sh   # Build + deploy script
    └── README.md
```

Each agent has the same structure:

```
ai-<position>/
├── src/main.py                          # Agent code
├── .bedrock_agentcore.yaml.template     # AgentCore config template
├── requirements.txt                     # Python dependencies
├── test_local.py                        # Local tests (no AWS needed)
└── .gitignore
```

### How it works

Every agent's `main.py` follows the same pattern:

1. **System prompt** — tells the LLM what position it plays and what commands are available
2. **Fallback config** — rule-based behavior when the LLM fails to respond properly
3. **Wire it up** — `create_agent()` + `create_invoke_handler()` from the shared lib

The shared `lib/` provides:
- `agent_base.py` — agent factory + invoke handler with 3-layer error handling (LLM → fallback → last-resort)
- `fallback.py` — configurable rule-based fallback per position
- `parsing.py` — extracts JSON commands from LLM responses
- `state.py` — summarizes game state into text for the LLM
- `_bootstrap.py` — resolves `lib/` path for both local dev and deployed environments
- `test_helpers.py` — mock AgentCore + sample game state for local tests


## Prerequisites

- Python 3.10+
- AWS CLI configured with valid credentials
- AgentCore CLI: `pip install bedrock-agentcore-starter-toolkit`
- `rsync` (pre-installed on macOS/Linux)
- AWS account with Bedrock model access (Nova Micro, Lite, and/or Pro)

## Quick Start

### 1. Run local tests (no AWS needed)

```bash
# Test a single agent
python3 ai-gk/test_local.py

# Test with a real LLM call (needs AWS credentials)
python3 ai-gk/test_local.py --llm
```

### 2. Deploy to AWS

```bash
# Deploy all 5 agents
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh

# Deploy a single agent
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh ai-gk
```

The deploy script:
1. Creates a `_build/<agent>/` staging directory
2. Copies the agent's `src/` + shared `lib/` + `requirements.txt`
3. Generates `.bedrock_agentcore.yaml` from the agent's template (substituting AWS account/region)
4. Runs `agentcore deploy` from the staging directory
5. Cleans up `_build/` when done

This staging approach keeps `lib/` as a single source of truth — you never copy it into each agent's tree.


## Creating Your Own Agent

The easiest way is to copy an existing agent and modify it:

```bash
cp -r ai-gk ai-myagent
```

Then edit these files:

### `ai-myagent/src/main.py`

```python
# 1. Set which player this agent controls (0-4)
MY_PLAYER_ID = 0
POSITION_LABEL = "GK"

# 2. Write your system prompt — tell the LLM its role and available commands
SYSTEM_PROMPT = f"""You are an AI soccer goalkeeper..."""

# 3. Pick a fallback config (or create your own in lib/fallback.py)
fallback_commands = build_fallback(GK_CONFIG)

# 4. Choose your model
agent = create_agent(SYSTEM_PROMPT, model_id="us.amazon.nova-micro-v1:0")
```

### `ai-myagent/.bedrock_agentcore.yaml.template`

Update the `default_agent` and agent name to match your agent:

```yaml
default_agent: ai_myagent_agent
agents:
  ai_myagent_agent:
    name: ai_myagent_agent
    # ... rest stays the same
```

### `deploy-all.sh`

Add your agent to the `ALL_AGENTS` array:

```bash
ALL_AGENTS=("ai-gk" "ai-def" "ai-mid" "ai-fwd1" "ai-fwd2" "ai-myagent")
```


## Player IDs and Positions

| Player ID | Position   | Default Model |
|-----------|------------|---------------|
| 0         | Goalkeeper | Nova Micro    |
| 1         | Defender   | Nova Lite     |
| 2         | Midfielder | Nova Pro      |
| 3         | Forward 1  | Nova Micro    |
| 4         | Forward 2  | Nova Lite     |

## Available Commands

Commands are what the LLM returns to control the player each tick.

**One-shot** (execute once):
- `MOVE_TO` — target_x, target_y, sprint
- `PASS` — target_player_id, type (GROUND/AERIAL/THROUGH)
- `SHOOT` — aim_location (TL/TR/BL/BR/CENTER), power (0.0-1.0)
- `GK_DISTRIBUTE` — target_player_id, method (THROW/KICK)

**Maintained** (persist across ticks):
- `PRESS_BALL` — intensity (0.0-1.0)
- `MARK` — target_player_id, tightness (LOOSE/TIGHT)
- `INTERCEPT` — aggressive (bool)
- `FOLLOW_PLAYER` — target_player_id, target_team, distance

**Tactical**:
- `SET_STANCE` — stance (0=Balanced, 1=Attack, 2=Defend)
- `CLEAR_OVERRIDE` — return to default AI

## Error Handling

Each agent has three layers of fallback:

1. **LLM response** — parsed into commands via `lib/parsing.py`
2. **Rule-based fallback** — position-specific logic from `lib/fallback.py`
3. **Last-resort command** — a single safe command (e.g., SET_STANCE) when everything else fails

## Field Coordinates

- x: roughly -55 to +55
- y: roughly -35 to +35
- Team 0 (HOME) defends -x, attacks toward +x
- Team 1 (AWAY) defends +x, attacks toward -x
