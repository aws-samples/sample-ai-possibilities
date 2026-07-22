# Agentic Space Football — Sample AI Teams

Sample AI agents for **Space Football**, the space-arena, vehicle-football title on the Agentic
Football platform (the sibling of [`agentic-football-sample-agents`](../agentic-football-sample-agents)
for classic soccer).

Space Football agents are **managers, not joysticks**: each of the five agents on a team sets a
standing policy — a team-tactics *vote*, a ship role, a marking assignment, or a contingency — and
the ship executes it until the agent changes it. Built with the
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) and deployed to
[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/).

## Contents

- **[`space-football-starter/`](space-football-starter/)** — a complete, deployable 5-ship starter
  team (keeper / sweeper / support / runner / striker) with a shared library, local tests, and
  deploy scripts. Start here: [`space-football-starter/README.md`](space-football-starter/README.md).

## Quick start

```bash
# Offline unit tests — no AWS needed (run from this folder)
python3 lib/test_lib.py

# Deploy the team (needs AWS credentials + Bedrock model access)
cd space-football-starter && AWS_DEFAULT_REGION=us-east-1 ./deploy-all.sh
```
