# Cars Edition AI Team (defensive)

Five car agents for Agentic Football Cup - Cars Edition, defensive squad. See the
[folder README](../README.md) for the arena, the command reference and the deploy walkthrough.

| Car | Role | Model |
|---|---|---|
| `car-goalkeeper/` | GOALKEEPER | `us.amazon.nova-lite-v1:0` |
| `car-defender/` | DEFENDER | `us.amazon.nova-lite-v1:0` |
| `car-support/` | SUPPORT | `us.amazon.nova-2-lite-v1:0` |
| `car-striker-1/` | STRIKER | `us.amazon.nova-micro-v1:0` |
| `car-striker-2/` | STRIKER | `us.amazon.nova-micro-v1:0` |

```bash
python3 car-goalkeeper/test_local.py          # offline checks
python3 car-goalkeeper/test_local.py --llm    # one real model call
AWS_DEFAULT_REGION=us-east-1 python3 deploy_all.py   # deploy all five with the AgentCore CLI
agentcore status --json                       # the five runtime ARNs to register in the portal
```
