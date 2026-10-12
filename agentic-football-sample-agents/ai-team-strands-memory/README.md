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
- A `team_memory` resource is declared in `agentcore/agentcore.json` and created
  by the same `agentcore deploy` that deploys the agents — no separate
  create-memory step
- The CDK stack grants every agent runtime access to the memory and injects its
  ID as the `MEMORY_TEAM_MEMORY_ID` environment variable
- `AgentCoreMemorySessionManager` wired into each Strands Agent
  (`memory_agent_base_cdk.py`, staged into each agent at deploy time)
- System prompts instruct agents to leverage recalled history

## Architecture

```
agents/
├── lib/                          # Shared library (same as other teams)
└── ai-team-strands-memory/
    ├── ai-gk/                    # Goalkeeper  (player 0) — Nova Micro + Memory
    ├── ai-def/                   # Defender    (player 1) — Nova Lite  + Memory
    ├── ai-mid/                   # Midfielder  (player 2) — Nova Pro   + Memory
    ├── ai-fwd1/                  # Forward 1   (player 3) — Nova Micro + Memory
    ├── ai-fwd2/                  # Forward 2   (player 4) — Nova Lite  + Memory
    ├── agentcore/                # AgentCore project config (agents + memory)
    │   ├── agentcore.json        # Runtimes + team_memory declaration
    │   └── cdk/                  # CDK app used by `agentcore deploy`
    ├── memory_agent_base_cdk.py  # Memory-aware agent factory (CDK flow)
    ├── deploy_all.py             # Cross-platform deploy script
    ├── destroy_all.py            # Cross-platform teardown script
    └── README.md
```

## Prerequisites

- Python 3.10+
- Node.js 20+ and npm
- AWS CLI configured with valid credentials
- AgentCore CLI and CDK: `npm install -g @aws/agentcore aws-cdk`
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — used by the AgentCore CLI to package Python dependencies
- AWS account with Bedrock model access (Nova Micro, Lite, and/or Pro)
- CDK bootstrap (one-time per account/region): `cdk bootstrap aws://<account-id>/<region>`

Works on macOS, Linux, and Windows (PowerShell) — no WSL required.
No Python packages needed to deploy — `deploy_all.py` uses only the standard library.

## Quick Start

### 1. Deploy (memory + all 5 agents)

```bash
# macOS/Linux
AWS_DEFAULT_REGION=us-east-1 python deploy_all.py
```

```powershell
# Windows PowerShell
$env:AWS_DEFAULT_REGION = "us-east-1"
python deploy_all.py
```

On AWS CloudShell, `cdk`, Node.js 20 and the AWS CLI are pre-installed. Install the
AgentCore CLI outside the 1 GB home directory and keep the package caches in `/tmp`
(`npm config set cache /tmp/npm-cache`, `export UV_CACHE_DIR=/tmp/uv-cache`,
`sudo npm install -g @aws/agentcore`). The CLI install lives on the ephemeral root
filesystem, so re-run it in each new CloudShell session.

The script checks prerequisites, writes the deploy target, bootstraps CDK if
needed, stages the shared `lib/` and `memory_agent_base_cdk.py` into each agent
directory, and runs `agentcore deploy --yes`. That single deploy creates the
`team_memory` resource, grants the runtimes access to it, and injects
`MEMORY_TEAM_MEMORY_ID` into every agent — nothing to export or configure.

### 2. Local test

```bash
python3 ai-gk/test_local.py
python3 ai-gk/test_local.py --llm  # needs AWS credentials
```

### 3. Teardown

```bash
python destroy_all.py            # remove all 5 agents
python destroy_all.py ai-gk      # remove one agent
```

The memory resource is kept; remove its entry from `agentcore/agentcore.json`
and redeploy (or delete the CloudFormation stack) to delete it.

## Legacy scripts

`deploy-all.sh` / `deploy-all-windows.ps1` (with `create_memory.py` and
`memory_agent_base.py`) are the previous deployment path and still work.
Note the two paths manage **separate resources**: the legacy flow creates a
memory named `AITeamMatchMemory` outside CloudFormation, while this flow
creates `team_memory` inside the stack. Running both against one account
leaves two memory resources and two sets of agent runtimes.
