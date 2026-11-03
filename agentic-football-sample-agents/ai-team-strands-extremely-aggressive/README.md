# AI Team (Strands) — Extremely Aggressive

Five AI agents that each control a single player in a 5v5 soccer match with an
**extremely aggressive** play style. Every player prioritizes attacking, the goalkeeper
pushes forward as a sweeper-keeper, and defensive behavior is minimized across all agents.

Built with [Strands Agents SDK](https://github.com/strands-agents/sdk-python) and deployed to
[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/).

## Strategy

- **GK**: Sweeper-keeper — pushes to halfway line, shoots if near goal
- **DEF**: Attacking defender — joins every attack, shoots from distance, rarely tracks back
- **MID**: Second striker — shoots first, passes forward only, never defends
- **FWD1**: Pure goal scorer — camps near goal, shoots at every opportunity
- **FWD2**: Pure goal scorer — same as FWD1, stays on right side

## Architecture

```
agents/
├── lib/            # Shared library (single source of truth)
└── ai-team-strands-extremely-aggressive/
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

On AWS CloudShell, `cdk`, Node.js 20 and the AWS CLI are pre-installed. Clone the
repository into your home directory as usual and edit there; it persists between
sessions. The home directory is limited to 1 GB, which a deploy's generated files
exceed, so keep the tool caches in `/tmp` and let the deploy script work from a
mirror in `/tmp` (`DEPLOY_WORK_DIR`); it copies the deployment state back when done:

```bash
npm config set cache /tmp/npm-cache
export UV_CACHE_DIR=/tmp/uv-cache
sudo npm install -g @aws/agentcore
curl -LsSf https://astral.sh/uv/install.sh | sh && source "$HOME/.local/bin/env"
DEPLOY_WORK_DIR=/tmp/work python3 deploy_all.py
```

`/tmp` is cleared when the CloudShell session ends, so repeat the three install lines in
each new session; your clone and your deployed agents are unaffected.
