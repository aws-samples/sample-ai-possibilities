---
name: bedrock-agentcore
description: "Activate when discussing deployment, AgentCore CLI, or production infrastructure"
---

# Amazon Bedrock AgentCore Guide

Enterprise-grade services for deploying and operating AI agents at scale. AgentCore eliminates undifferentiated infrastructure work — identity, memory, tool management, observability — so you can focus on agent logic.

AgentCore works with any framework (Strands, LangGraph, CrewAI, LlamaIndex) and any foundation model in or outside Amazon Bedrock.

## Why AgentCore?

- **Faster time to value** — Fully-managed services eliminate infrastructure complexity
- **Flexibility and choice** — Any framework, any model, full control over agent operations
- **Security and trust** — Enterprise-grade security, complete session isolation, comprehensive controls

## AgentCore Services

### 1. Runtime

Securely deploy and run agents at scale. Runtime provides:

- Containerized agent execution with automatic scaling
- Session isolation between concurrent users
- Health monitoring and automatic restarts
- Support for any Python-based agent framework

**Football context:** Runtime hosts your football agent so it can respond to game ticks in real-time. Each deployed agent gets a unique Runtime ARN used for match registration.

**Configuration file:** `.bedrock_agentcore.yaml` in your agent project root defines runtime settings.

### 2. Memory

Context-aware agents with managed memory infrastructure:

- **Short-term memory** — Multi-turn conversation context within a session
- **Long-term memory** — Persistent knowledge shared across agents and sessions
- Industry-leading accuracy for memory retrieval

**Football context:** Your agent can remember opponent tendencies from previous matches (long-term) and track patterns within the current match (short-term). Memory can be shared across your team — when one defender learns an opponent's dribbling pattern, all defenders gain that knowledge.

### 3. Gateway

Secure tool discovery and management for agents:

- Transform APIs, Lambda functions, and existing services into agent-compatible tools
- Built-in semantic search to find the right tool for the context
- Support for thousands of tools while minimizing prompt size and latency
- Eliminates weeks of custom integration code

**Football context:** Instead of hardcoding every tool into every player agent, Gateway lets agents discover the right tool for the moment — a midfielder under pressure finds the "quick pass" tool, while a striker in the box discovers the "power shot" tool.

### 4. Identity

Secure agent identity and access management:

- Compatible with existing identity providers (no user migration needed)
- Secure token vault to minimize consent fatigue
- Just-enough access and secure permission delegation
- Agents can securely access AWS resources and third-party services

**Football context:** Each player agent gets a unique identity with role-specific permissions. Your striker accesses shooting tools, your goalkeeper controls the penalty area, and your midfielder accesses passing tools — each agent only accesses actions relevant to their role.

### 5. Observability

Trace, debug, and monitor agent performance in production:

- OpenTelemetry-compatible telemetry
- Detailed visualizations of each step in the agent workflow
- Unified operational dashboards
- Quality standards monitoring at scale

**Football context:** Trace your agent's decision-making step by step — which tools it called, what data it received, where logic failed. Monitor all 5 player agents simultaneously, identify performance bottlenecks, and optimize responsiveness.

### 6. Code Interpreter

Secure code execution in isolated sandbox environments:

- Run Python code in sandboxed containers
- Advanced configuration support
- Seamless integration with popular frameworks
- Enterprise security requirements met

**Football context:** Your agent can run physics calculations in real-time — given positions of players, goalkeeper, and defenders, calculate the optimal shooting angle and power dynamically instead of pre-programming every scenario.

### 7. Browser

Cloud-based browser runtime for AI agents:

- Fast, secure, scalable browser interactions
- Enterprise-grade security and comprehensive observability
- Automatic scaling without infrastructure management

**Football context:** Agents can browse tactical analysis sites, watch video clips of professional players, and extract positioning patterns to bring real-world football intelligence into your simulation.

## Deploying Your Football Agent

### Prerequisites

- Agent code with `.bedrock_agentcore.yaml` config file
- AWS credentials configured (from Workshop Studio)
- AgentCore CLI installed

### Step 1: Test Locally

```bash
# Test without LLM (rule-based fallback)
python test_local.py

# Test with LLM (Bedrock model)
python test_local.py --llm
```

### Step 2: Install AgentCore CLI

Install from the Bedrock AgentCore Starter Toolkit:

```
https://github.com/aws/bedrock-agentcore-starter-toolkit
```

### Step 3: Deploy

```bash
agentcore deploy
```

This packages your agent code, uploads it to AgentCore Runtime, and starts the service. On success you receive a **Runtime ARN** — a unique Amazon Resource Name identifying your deployed agent.

### Step 4: Get Your Runtime ARN

Find your Runtime ARN in the Bedrock AgentCore console:

```
https://us-east-1.console.aws.amazon.com/bedrock-agentcore/agents?region=us-east-1
```

The Runtime ARN looks like:

```
arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<runtime-id>
```

### Step 5: Register for Matches

Use the Runtime ARN to register your agent for football matches. Options:

- **Single ARN** — Use one Runtime ARN for all 5 players (same agent logic for every position)
- **Multiple ARNs** — Deploy separate agents per player for position-specific strategies

### Step 6: View Logs

Monitor your deployed agent with CloudWatch Logs:

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs" \
  --follow
```

This streams real-time logs showing:

- Agent invocations and responses
- Tool calls and results
- Errors and exceptions
- Latency metrics

### Step 7: Iterate

After watching your agent play:

1. Analyze logs for decision-making issues
2. Update agent code locally
3. Test with `python test_local.py --llm`
4. Redeploy with `agentcore deploy`
5. Re-register if you get a new Runtime ARN

## AgentCore Configuration

### `.bedrock_agentcore.yaml`

This file in your agent project root configures the Runtime deployment:

```yaml
# Example configuration
runtime:
  name: my-football-agent
  entry_point: src/main.py
  requirements: requirements.txt
```

### Logging and Observability Configuration

Enable detailed logging in your agent code to leverage AgentCore Observability:

**For Strands agents:**

```python
import logging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
```

**For LangGraph agents:**

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log key decision points
logger.info(f"Game state received: {state_summary}")
logger.info(f"Agent action: {action}")
```

**Metrics via Strands SDK:**

```python
result = agent("Analyze game state...")
summary = result.metrics.get_summary()
print(f"Tokens used: {summary['accumulated_usage']['totalTokens']}")
print(f"Latency: {summary['accumulated_metrics']['latencyMs']}ms")
print(f"Tool calls: {summary['tool_usage']}")
```

### Runtime ARN Usage for Match Registration

After deployment, the Runtime ARN is your agent's identity in the competition system:

1. **Copy the ARN** from the AgentCore console
2. **Register** via the workshop match registration page
3. **Assign positions** — map the ARN to player slots (1-5)
4. **Monitor** — watch matches and check logs for your agent's decisions

You can update your agent code and redeploy without changing the ARN (the runtime endpoint stays the same).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `agentcore deploy` fails | Check AWS credentials: `aws sts get-caller-identity` |
| Agent times out during match | Ensure response time < 500ms; use a faster model (Nova Micro) |
| No logs appearing | Verify the runtime ID in the log group path; check region |
| Runtime ARN not found | Check the AgentCore console; deployment may still be in progress |
| Model throttling errors | Add retry strategy in agent code; reduce token usage |

## Resources

- [Amazon Bedrock AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
- [AgentCore Starter Toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [AgentCore FAQs](https://aws.amazon.com/bedrock/agentcore/faqs/)
- [AgentCore Runtime Deep Dive (YouTube)](https://www.classcentral.com/course/youtube-amazon-bedrock-agentcore-deep-dive-series-runtime-aws-show-and-tell-476591)
- [AgentCore Gateway Deep Dive (YouTube)](https://www.classcentral.com/course/youtube-amazon-bedrock-agentcore-deep-dive-series-gateway-aws-show-and-tell-480974)
- [AgentCore Memory Deep Dive (YouTube)](https://www.classcentral.com/course/youtube-amazon-bedrock-agentcore-deep-dive-series-memory-aws-show-and-tell-488968)
- [AgentCore Observability (YouTube)](https://www.classcentral.com/course/youtube-gain-visibility-into-ai-agents-with-amazon-bedrock-agentcore-observability-aws-show-and-tell-495900)
- [AgentCore Identity (YouTube)](https://www.classcentral.com/course/youtube-secure-your-agent-workflows-using-agentcore-identity-aws-show-tell-484501)
