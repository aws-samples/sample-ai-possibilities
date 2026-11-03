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
    ├── deploy_all.py   # Build + deploy script
    └── README.md
```

## Quick Start

Prerequisites are the same as the balanced team (see ../ai-team-strands-balanced/README.md).

```bash
# Test a single agent
python3 ai-gk/test_local.py

# Deploy all 5 agents
AWS_DEFAULT_REGION=us-east-1 python deploy_all.py
```

On AWS CloudShell, `cdk`, Node.js 20 and the AWS CLI are pre-installed. The home
directory is limited to 1 GB, which a team deploy exceeds, so use `/tmp` as the
working directory:

```bash
mkdir -p /tmp/work && cd /tmp/work
git clone --depth 1 https://github.com/aws-samples/sample-ai-possibilities.git
npm config set cache /tmp/npm-cache
export UV_CACHE_DIR=/tmp/uv-cache
sudo npm install -g @aws/agentcore
curl -LsSf https://astral.sh/uv/install.sh | sh && source "$HOME/.local/bin/env"
```

`/tmp` is cleared when the CloudShell session ends, so repeat these steps in each new
session and copy any files you edited back to your home directory first. Before
deploying a second team, delete the previous team's `agentcore/.cache` and
`agentcore/cdk/cdk.out`.
