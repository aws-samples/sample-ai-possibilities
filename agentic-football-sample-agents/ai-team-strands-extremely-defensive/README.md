# AI Team (Strands) — Extremely Defensive

Five AI agents that each control a single player in a 5v5 soccer match with an
**extremely defensive** play style. All players stay in their own half, prioritize
blocking and defending, and scoring attempts are minimal.

Built with [Strands Agents SDK](https://github.com/strands-agents/sdk-python) and deployed to
[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/).

## Strategy

- **GK**: Deep goalkeeper — never leaves goal line, distributes safely
- **DEF**: Ultra-defensive sweeper — never crosses halfway, marks tightly
- **MID**: Defensive midfielder — extra defender, passes backwards only
- **FWD1**: Defensive forward — tracks back, marks opponents, rarely shoots
- **FWD2**: Defensive forward — same as FWD1, covers right flank

## Architecture

```
agents/
├── lib/            # Shared library (single source of truth)
└── ai-team-strands-extremely-defensive/
    ├── ai-gk/          # Goalkeeper  (player 0) — Nova Micro
    ├── ai-def/         # Defender    (player 1) — Nova Lite
    ├── ai-mid/         # Midfielder  (player 2) — Nova Pro
    ├── ai-fwd1/        # Forward 1   (player 3) — Nova Micro
    ├── ai-fwd2/        # Forward 2   (player 4) — Nova Lite
    ├── deploy-all.sh           # Build + deploy script (macOS/Linux)
    ├── deploy-all-windows.ps1  # Build + deploy script (Windows)
    └── README.md
```

## Prerequisites

- Python 3.10+
- AWS CLI configured with valid credentials
- AWS account with Bedrock model access (Nova Micro, Lite, and/or Pro)

**macOS/Linux additionally:**
- AgentCore CLI: `pip install bedrock-agentcore-starter-toolkit`
- `rsync` (pre-installed on macOS/Linux)

**Windows additionally:**
- Node.js 18+ with npm
- AgentCore CLI: `npm install -g @aws/agentcore aws-cdk`

## Quick Start

```bash
# Test a single agent
python3 ai-gk/test_local.py
```

## Deploy to AWS

**macOS / Linux:**
```bash
# Deploy all 5 agents
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh

# Deploy a single agent
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh ai-gk
```

**Windows (PowerShell):**
```powershell
# Deploy all 5 agents
$env:AWS_DEFAULT_REGION = "us-east-1"
.\deploy-all-windows.ps1

# Deploy a single agent
.\deploy-all-windows.ps1 -AgentName ai-gk
```
