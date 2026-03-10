# LangChain Agents Guide

Comprehensive reference for building football agents with LangChain. Covers setup, the ReAct pattern, deployment, and enhancement strategies.

## Agent Architecture Overview

Each team has 5 players; each player is an agent. Your agent receives game state every tick (60 times/second) and must return actions within 500ms.

```
Game State (JSON) → Your Agent → Player Actions (JSON)
```

---

## LangChain Setup

### Getting the Code

```bash
git clone https://github.com/aws-samples/fifa-agentic-football-langchain.git
cd fifa-agentic-football-langchain
```

### Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The `requirements.txt` includes: `langchain>=0.1.0`, `langchain-aws>=0.1.0`, `bedrock-agentcore>=1.0.3`.

### Sample Agent Structure

```
fifa-agentic-football-langchain/
├── src/
│   └── main.py                          # Agent implementation
├── .bedrock_agentcore.yaml.template     # AgentCore config template
├── deploy-local.sh                      # Deployment script
├── test_local.py                        # Local test suite
└── requirements.txt                     # Python dependencies
```

---

## The ReAct Pattern

LangGraph uses the ReAct (Reasoning and Acting) pattern via `create_react_agent`. The agent systematically:

1. **Reasons** about the current game state
2. **Acts** by calling tools (e.g., calculate distances, evaluate shooting angles)
3. **Observes** tool results
4. **Responds** with a structured action

### Core Concepts

**`create_react_agent`** — The primary function for building ReAct agents in LangGraph. It creates an agent that:
- Receives a prompt with the current game state
- Reasons about available actions
- Calls tools when needed for analysis
- Returns a final action decision

**Tool Integration** — Define Python functions as tools the agent can call during reasoning:
- Distance calculations
- Shooting angle analysis
- Passing option evaluation
- Stamina management checks

**State Management** — LangGraph manages state explicitly. You pass conversation history and custom state (scoreline, tactical mode, formation) through the agent executor at each invocation. This differs from Strands, where state is managed through built-in agent constructs.

### Key Differences from Strands

| Aspect | LangGraph | Strands |
|---|---|---|
| Agent creation | `create_react_agent()` | `Agent()` |
| Abstraction level | Higher — managed ReAct scaffolding | Lower — explicit control over agent loop |
| State management | Explicit — pass through chain/executor | Built-in — agent memory constructs |
| Tool definition | LangChain tool decorators | `@tool` decorator |
| Best for | Structured multi-step reasoning | Custom workflows, fine-grained logic |

---

## Building Your Agent

### Step 1: Test Locally

Start the local development server:
```bash
agentcore dev
```

In a separate terminal, send a test invocation:
```bash
agentcore invoke --dev '{"prompt": "{\"gameState\": {\"ball\": {\"position\": {\"x\": 30, \"y\": 10}}, \"players\": [], \"score\": {\"home\": 0, \"away\": 0}, \"gameTime\": 60}, \"teamId\": 0}"}'
```

### Step 2: Deploy

Run the deployment script:
```bash
./deploy-local.sh
```

The script handles: IAM role creation, dependency packaging for ARM64, S3 upload, and agent deployment.

**Key output:** Agent ARN in format `arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-id>` — save this for portal registration.

---

## Deployment

### AgentCore Deployment

After deploying with `./deploy-local.sh`:

1. Verify deployment: `agentcore status`
2. View logs: `aws logs tail /aws/bedrock-agentcore/runtimes/<id>-DEFAULT --follow`
3. Redeploy after changes: `./deploy-local.sh` (ARN stays the same)
4. Optionally create one agent per player position (up to 5 ARNs)

---

## Enhancement Suggestions

### 1. Integrate Guardrails

Implement responsible AI using Bedrock Guardrails to filter invalid or unsafe agent outputs. See LangChain's Bedrock guardrails integration documentation.

### 2. Improve Prompts

Refine the system prompt to better guide agent reasoning:
- Define the agent's role and position explicitly
- Encode tactical philosophy (possession-based, counter-attacking)
- Set decision-making priorities and risk tolerance
- Specify behavioral constraints

**Prompt engineering tips:**
- Be explicit about priorities (defend a lead vs. chase a game)
- Reduce ambiguity in action descriptions
- Provide match context concisely — only what's needed for the current decision
- Iterate based on observed behavior from replays and traces
- Test edge cases: being a player down, defending corners, time-wasting

### 3. Enhanced Testing

Implement comprehensive testing scenarios:
- Test agent behavior when possession is lost in dangerous positions
- Test unusual game states (player down, corner defense, injury)
- Use LLMs to generate diverse test cases covering edge cases
- Submit multiple evaluation attempts to exploit LLM non-determinism (best result preserved)

### 4. Performance Tuning

- **Parallel processing** — Implement parallel tool calls to reduce latency
- **Efficient usage** — Execute expensive operations only when necessary
- **Model selection** — Try different model sizes based on task complexity (Nova Micro for speed, Claude for capability)
- **Context management** — Keep prompts lean; avoid overloading with irrelevant state

### 5. Multi-Agent Architectures

Consider alternative designs:
- Separate agents for different player positions
- Specialist agents (defensive analyst, offensive strategist) coordinated by a coach agent
- Dedicated calculation functions as external tools to reduce latency

---

## Best Practices

### System Prompts

- Define role, position, and tactical philosophy
- Set priorities for different game situations (winning, losing, drawing)
- Encode constraints (never leave goal undefended, always track back)

### State Management

- Pass only relevant state per tick (not full match history)
- Track opponent tendencies across ticks when possible
- Keep in-game state lean and focused on current decision context

### Agent Loop Awareness

Common problems to watch for:
- **Infinite loops** — Agent re-evaluates without committing to an action; set iteration limits
- **Tool call failures** — Ensure tools handle edge cases and return well-formed responses
- **Context window bloat** — Pass only what's needed for the current decision
- **Premature termination** — Review stopping conditions to ensure full evaluation
- **Conflicting tool outputs** — Encode conflict resolution logic in prompts

### Prompt Engineering

- Be specific about desired behavior
- Specify scope (which players an instruction applies to)
- Avoid conflicting directives in a single message
- Iterate based on observed match behavior
- Test edge cases deliberately
