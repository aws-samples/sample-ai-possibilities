# AI Team (Strands + Memory) — Per-Position Soccer Agents with AgentCore Memory

Five AI agents that each control a single player in a 5v5 soccer match, built with
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) and
[Amazon Bedrock AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/) for
cross-tick history recall.

## What's Different from the Balanced Team?

Each agent uses `AgentCoreMemorySessionManager` (STM) to persist conversation history
across game ticks. This lets agents recall opponent movement patterns, previous
tactical decisions, and game flow from earlier in the match.

Key differences:
- `memory.mode: STM_AND_LTM` in AgentCore config
- `AgentCoreMemorySessionManager` wired into each Strands Agent
- System prompts instruct agents to leverage recalled history
- Requires `MEMORY_ID` environment variable (created once per deployment)

## Architecture

```
agents/
├── lib/                        # Shared library (same as other teams)
└── ai-team-strands-memory/
    ├── ai-gk/                  # Goalkeeper  (player 0) — Nova Micro + Memory
    ├── ai-def/                 # Defender    (player 1) — Nova Lite  + Memory
    ├── ai-mid/                 # Midfielder  (player 2) — Nova Pro   + Memory
    ├── ai-fwd1/                # Forward 1   (player 3) — Nova Micro + Memory
    ├── ai-fwd2/                # Forward 2   (player 4) — Nova Lite  + Memory
    ├── deploy-all.sh           # Build + deploy script (macOS/Linux)
    ├── deploy-all-windows.ps1  # Build + deploy script (Windows)
    └── README.md
```

## Prerequisites

- Python 3.10+
- AWS CLI configured with valid credentials
- AWS account with Bedrock model access (Nova Micro, Lite, and/or Pro)
- A Bedrock AgentCore Memory resource (created once via `create_memory.py`)

**macOS/Linux additionally:**
- AgentCore CLI: `pip install bedrock-agentcore-starter-toolkit`
- `rsync` (pre-installed on macOS/Linux)

**Windows additionally:**
- Node.js 18+ with npm
- AgentCore CLI: `npm install -g @aws/agentcore aws-cdk`

## Quick Start

### 1. Create the Memory resource (one-time)

```bash
export AWS_DEFAULT_REGION=us-east-1
python3 create_memory.py
# Note the MEMORY_ID printed — set it as env var or in AgentCore config
```

### 2. Deploy

**macOS / Linux:**
```bash
export MEMORY_ID=<your-memory-id>
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh

# Deploy a single agent
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh ai-gk
```

**Windows (PowerShell):**
```powershell
$env:MEMORY_ID = "<your-memory-id>"
$env:AWS_DEFAULT_REGION = "us-east-1"
.\deploy-all-windows.ps1

# Deploy a single agent
.\deploy-all-windows.ps1 -AgentName ai-gk
```

### 3. Local test

```bash
python3 ai-gk/test_local.py
python3 ai-gk/test_local.py --llm  # needs AWS credentials + MEMORY_ID
```
