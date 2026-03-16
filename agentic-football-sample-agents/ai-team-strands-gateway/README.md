# AI Team (Strands + Gateway) — Per-Position Soccer Agents with MCP Tactical Tools

Five AI agents that each control a single player in a 5v5 soccer match, built with
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) and
[Amazon Bedrock AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/) for
MCP-based tactical analysis tools.

## What's Different from the Balanced Team?

Each agent connects to an AgentCore Gateway via MCP and can autonomously call
tactical analysis tools during gameplay. The agent decides which tools to use
based on its current situation — no forced tool calls.

Available MCP tools:
- `calculate_pass_options` — Pass success probability based on interception risk
- `find_open_space` — Grid-based open space finder by zone (attack/midfield/defense)
- `evaluate_shot` — Shot success probability with aim recommendation
- `get_defensive_assignment` — Opponent threat ranking for marking priority

Key differences from balanced team:
- `MCPClient` connected to AgentCore Gateway for tool access
- `gateway_invoke_handler.py` wraps agent calls inside `with mcp_client:` context
- System prompts guide agents on WHEN to use tools, but agents decide autonomously
- Gateway uses NONE auth (no token required)
- Requires `GATEWAY_URL` environment variable (auto-set by deploy-all.sh)

## Architecture

```
agents/
├── lib/                          # Shared library (same as other teams)
└── ai-team-strands-gateway/
    ├── ai-gk/                    # Goalkeeper  (player 0) — Nova Micro + Gateway
    ├── ai-def/                   # Defender    (player 1) — Nova Lite  + Gateway
    ├── ai-mid/                   # Midfielder  (player 2) — Nova Pro   + Gateway
    ├── ai-fwd1/                  # Forward 1   (player 3) — Nova Micro + Gateway
    ├── ai-fwd2/                  # Forward 2   (player 4) — Nova Lite  + Gateway
    ├── gateway_agent_base.py     # Agent factory with MCP client
    ├── gateway_invoke_handler.py # Invoke handler with MCP context
    ├── gateway_tools/            # Lambda handlers for tactical tools
    ├── deploy-all.sh             # Build + deploy script
    └── README.md
```

## How Agents Use Tools

Each agent's system prompt suggests which tools are most relevant for their position,
but the agent autonomously decides whether and when to call them:

| Position | Primary Tools | When |
|----------|--------------|------|
| GK | `get_defensive_assignment`, `calculate_pass_options` | Identify threats, distribute after saves |
| DEF | `get_defensive_assignment`, `calculate_pass_options` | Mark opponents, find outlet passes |
| MID | `calculate_pass_options`, `find_open_space`, `evaluate_shot` | Distribute, position, decide shoot vs pass |
| FWD1 | `evaluate_shot`, `calculate_pass_options`, `find_open_space` | Shoot decisions, passing under pressure |
| FWD2 | `evaluate_shot`, `calculate_pass_options`, `find_open_space` | Shoot decisions, attacking runs |

## Prerequisites

- Same as the balanced team (Python 3.10+, AWS CLI, AgentCore CLI)
- `boto3` installed (`pip install boto3`)
- Valid AWS credentials with permissions for IAM, Lambda, and Bedrock AgentCore

## Deploy

Everything is handled by a single command. The script automatically:
1. Creates Lambda IAM role (reuses if exists)
2. Deploys 4 Lambda functions for tactical tools
3. Creates Gateway execution role (reuses if exists)
4. Creates MCP Gateway with NONE auth via boto3 (reuses if exists)
5. Registers Lambda targets on the gateway
6. Deploys all 5 agents to AgentCore

```bash
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh
```

To deploy a single agent:
```bash
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh ai-gk
```

To skip gateway setup (if you already have one):
```bash
export GATEWAY_URL=https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
./deploy-all.sh
```

## Local Test

Tests verify state summary, command parsing, and fallback logic without
requiring a deployed Gateway or LLM calls:

```bash
python3 ai-gk/test_local.py
python3 ai-def/test_local.py
python3 ai-mid/test_local.py
python3 ai-fwd1/test_local.py
python3 ai-fwd2/test_local.py
```
