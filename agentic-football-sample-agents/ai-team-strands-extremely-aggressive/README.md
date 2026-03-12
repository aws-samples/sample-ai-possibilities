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
    ├── deploy-all.sh   # Build + deploy script
    └── README.md
```

## Quick Start

```bash
# Test a single agent
python3 ai-gk/test_local.py

# Deploy all 5 agents
AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh
```
