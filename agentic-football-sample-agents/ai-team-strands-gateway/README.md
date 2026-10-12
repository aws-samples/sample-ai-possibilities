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
- The gateway and its four Lambda tools are declared in
  `agentcore/agentcore.json` ("tactical-tools") and created by the same
  `agentcore deploy` that deploys the agents — the CDK app builds the Lambdas
  from `gateway_tools/` and creates all required IAM roles
- The CDK stack injects the gateway endpoint into every agent runtime as the
  `AGENTCORE_GATEWAY_TACTICAL_TOOLS_URL` environment variable
- `MCPClient` connected to the AgentCore Gateway for tool access
  (`gateway_agent_base_cdk.py`, staged into each agent at deploy time)
- `gateway_invoke_handler.py` wraps agent calls inside `with mcp_client:` context
- System prompts guide agents on WHEN to use tools, but agents decide autonomously
- Gateway uses NONE auth (no token required)

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
    ├── agentcore/                # AgentCore project config (agents + gateway + tools)
    │   ├── agentcore.json        # Runtimes + tactical-tools gateway declaration
    │   └── cdk/                  # CDK app used by `agentcore deploy`
    ├── gateway_agent_base_cdk.py # Agent factory with MCP client (CDK flow)
    ├── gateway_invoke_handler.py # Invoke handler with MCP context (both flows)
    ├── gateway_tools/            # Lambda handlers for tactical tools
    ├── deploy_all.py             # Cross-platform deploy script
    ├── destroy_all.py            # Cross-platform teardown script
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

- Python 3.10+
- Node.js 20+ and npm
- AWS CLI configured with valid credentials
- AgentCore CLI and CDK: `npm install -g @aws/agentcore aws-cdk`
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — used by the AgentCore CLI to package Python dependencies
- AWS account with Bedrock model access (Nova Micro, Lite, and/or Pro)
- Permissions for IAM, Lambda, CloudFormation, and Bedrock AgentCore
- CDK bootstrap (one-time per account/region): `cdk bootstrap aws://<account-id>/<region>`

Works on macOS, Linux, and Windows (PowerShell) — no WSL required.
No Python packages needed to deploy — `deploy_all.py` uses only the standard library.

## Deploy

Everything — the four Lambda tools, the MCP gateway, and all five agents — is
one CloudFormation deployment:

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
needed, stages the shared `lib/`, `gateway_agent_base_cdk.py`, and
`gateway_invoke_handler.py` into each agent directory, and runs
`agentcore deploy --yes`. That single deploy builds and deploys the Lambda
tools from `gateway_tools/`, creates the `tactical-tools` gateway with its
targets and IAM roles, and injects `AGENTCORE_GATEWAY_TACTICAL_TOOLS_URL`
into every agent — nothing to export or configure.

## Local Test

```bash
python3 ai-gk/test_local.py
python3 ai-gk/test_local.py --llm  # needs AWS credentials + a deployed gateway
```

## Teardown

```bash
python destroy_all.py            # remove all 5 agents
python destroy_all.py ai-gk      # remove one agent
```

The gateway and Lambda tools are kept; remove the `agentCoreGateways` entry
from `agentcore/agentcore.json` and redeploy (or delete the CloudFormation
stack) to delete them.

## Legacy scripts

`deploy-all.sh` / `deploy-all-windows.ps1` (with `manage_gateway.py` and
`gateway_agent_base.py`) are the previous deployment path and still work.
Note the two paths manage **separate resources**: the legacy flow creates the
`afwc-tactical-tools` gateway and `afwc-gateway-tool-*` Lambdas outside
CloudFormation, while this flow creates `tactical-tools` and its Lambdas
inside the stack. Running both against one account leaves two gateways and
two sets of Lambda functions.
