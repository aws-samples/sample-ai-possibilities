# Strands Agents SDK Guide

Comprehensive reference for building football agents with the Strands Agents SDK. Covers all 23 core concepts, sample agent structure, enhancement patterns, and deployment.

## Agent Architecture Overview

Each team has 5 players; each player is an agent. Your agent receives game state every tick (60 times/second) and must return actions within 500ms.

```
Game State (JSON) → Your Agent → Player Actions (JSON)
```

---

## 23 Core Concepts

### 1. Structured Output

Use Pydantic models to ensure your agent returns validated, type-safe game commands instead of raw text.

```python
from pydantic import BaseModel, Field
from strands import Agent

class FootballAction(BaseModel):
    commandType: str = Field(description="Action type: MOVE_TO, SHOOT, PASS, etc.")
    playerId: int = Field(description="Player ID performing the action")
    parameters: dict = Field(description="Action parameters")
    duration: int = Field(default=0, description="How long action persists")

agent = Agent(system_prompt="You are a football player. Analyze game state and return ONE action.")
result = agent("Ball at (10,5), I'm at (0,0). What should I do?", structured_output_model=FootballAction)
action: FootballAction = result.structured_output
```

### 2. Custom Tools

Tools provide tactical analysis functions your agent can call:

```python
from strands import Agent, tool
import math

@tool
def calculate_distance(pos1: dict, pos2: dict) -> float:
    """Calculate distance between two positions."""
    return math.sqrt((pos1['x'] - pos2['x'])**2 + (pos1['y'] - pos2['y'])**2)

@tool
def should_shoot(player_x: float, goal_x: float) -> dict:
    """Determine if player should shoot based on distance to goal."""
    distance = abs(player_x - goal_x)
    return {'should_shoot': distance < 30, 'recommended_power': max(0.5, min(1.0, 1.0 - distance/100))}

agent = Agent(tools=[calculate_distance, should_shoot], system_prompt="You are a football player agent.")
```

### 3. Model Providers

Switch between models easily:

```python
from strands.models import BedrockModel

model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")  # Fast, cost-effective
# model = BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0")  # More capable
agent = Agent(model=model, tools=[calculate_distance, should_shoot])
```

### 4. Observability

Track metrics, tokens, latency, and tool usage:

```python
result = agent("What should I do?")
summary = result.metrics.get_summary()
# summary['accumulated_usage']['totalTokens']
# summary['accumulated_metrics']['latencyMs']
# summary['tool_usage']
```

Detailed traces available per reasoning cycle via `result.traces`.

### 5. Hooks

Monitor and modify agent behavior at lifecycle points:

```python
from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent, AfterToolCallEvent

class FootballMonitoringHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.log_tool_start)
        registry.add_callback(AfterToolCallEvent, self.log_tool_end)
    def log_tool_start(self, event): print(f"Calling: {event.tool_use['name']}")
    def log_tool_end(self, event): print(f"Result: {event.result}")

agent = Agent(tools=[...], hooks=[FootballMonitoringHook()])
```

Advanced: Use `LimitToolCalls` hook to cap how many times a tool can be called per invocation.

### 6. Guardrails

Content filtering and safety via Bedrock Guardrails:

```python
model = BedrockModel(
    model_id="us.amazon.nova-micro-v1:0",
    guardrail_id="your-guardrail-id", guardrail_version="1", guardrail_trace="enabled"
)
agent = Agent(model=model)
result = agent("Some prompt")
if result.stop_reason == "guardrail_intervened":
    print("Content blocked by guardrails")
```

### 7. Direct Tool Invocation

Call tools programmatically without LLM reasoning:

```python
distance = agent.tool.calculate_distance(pos1={"x": 0, "y": 0}, pos2={"x": 10, "y": 5})
```

### 8. Community Tools

Pre-built tools from `strands-agents-tools`:

```python
from strands_tools import calculator, python_repl
agent = Agent(tools=[calculator, python_repl], system_prompt="You are a football analyst.")
```

Useful community tools: `calculator`, `python_repl`, `current_time`.

### 9. Conversation Management

Three built-in managers for controlling message history:

```python
from strands.agent.conversation_manager import (
    NullConversationManager,           # No trimming
    SlidingWindowConversationManager,   # Keep recent N messages
    SummarizingConversationManager,     # Summarize old messages
)

# Default: sliding window
agent = Agent(conversation_manager=SlidingWindowConversationManager(window_size=10))

# For football: typically stateless per tick (fresh agent each time)
agent = Agent()  # New agent = fresh start
```

### 10. Agent State Management

Key-value storage across invocations (not sent to model):

```python
from strands import tool, ToolContext

@tool(context=True)
def track_opponent(opponent_id: int, tendency: str, tool_context: ToolContext) -> str:
    """Record an opponent's tendency."""
    tendencies = tool_context.agent.state.get("opponent_tendencies") or {}
    tendencies[str(opponent_id)] = tendency
    tool_context.agent.state.set("opponent_tendencies", tendencies)
    return f"Recorded: player {opponent_id} → {tendency}"

agent = Agent(tools=[track_opponent], state={"opponent_tendencies": {}, "match_minute": 0})
```

### 11. Session Management

Persist state and conversation history across agent restarts:

```python
from strands.session.file_session_manager import FileSessionManager

session_manager = FileSessionManager(session_id="team-alpha-session", storage_dir="./sessions")
agent = Agent(session_manager=session_manager, state={"opponent_patterns": {}})
```

For cloud deployments, use `S3SessionManager`.

### 12. Retry Strategies

Handle model throttling during high-frequency game ticks:

```python
from strands import ModelRetryStrategy
agent = Agent(retry_strategy=ModelRetryStrategy(max_attempts=3, initial_delay=2, max_delay=60))
# Or disable retries for lowest latency:
agent = Agent(retry_strategy=None)
```

### 13. Streaming

Monitor agent decisions in real-time:

```python
async for event in agent.stream_async("Ball at (30,10), should I shoot?"):
    if "data" in event: print(event["data"], end="")
    elif "current_tool_use" in event and event["current_tool_use"].get("name"):
        print(f"Using tool: {event['current_tool_use']['name']}")
```

### 14. Class-Based Tools

Share state across related tools using classes:

```python
class MatchAnalytics:
    def __init__(self):
        self.shots_taken = 0
    @tool
    def record_shot(self, result: str) -> str:
        """Record a shot attempt."""
        self.shots_taken += 1
        return f"Shot #{self.shots_taken}: {result}"

analytics = MatchAnalytics()
agent = Agent(tools=[analytics.record_shot])
```

### 15. MCP Tools

Connect to external tool servers via Model Context Protocol:

```python
from strands.tools.mcp import MCPClient
mcp_client = MCPClient(lambda: sse_client("http://localhost:8000/sse"))
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
```

### 16. Multi-Agent — Agents as Tools

Wrap specialist agents as tools for an orchestrator:

```python
@tool
def defensive_analyst(game_state: str) -> str:
    """Analyze defensive positioning."""
    analyst = Agent(system_prompt="You are a defensive football analyst.")
    return str(analyst(game_state))

coach = Agent(tools=[defensive_analyst, offensive_strategist],
    system_prompt="You are the head coach. Route to the right specialist.")
```

### 17. Multi-Agent — Swarm

Collaborative agents that autonomously hand off tasks:

```python
from strands.multiagent import Swarm
scout = Agent(name="scout", system_prompt="Analyze opponent weaknesses.")
tactician = Agent(name="tactician", system_prompt="Design game plans.")
coach = Agent(name="coach", system_prompt="Finalize tactics.")
swarm = Swarm([scout, tactician, coach], entry_point=scout, max_handoffs=10)
result = swarm("Prepare a game plan against a 4-4-2 high-pressing team")
```

### 18. Multi-Agent — Graph

Structured pipeline with defined execution order:

```python
from strands.multiagent import GraphBuilder
builder = GraphBuilder()
builder.add_node(analyzer, "analyze")
builder.add_node(planner, "plan")
builder.add_node(executor, "execute")
builder.add_edge("analyze", "plan")
builder.add_edge("plan", "execute")
builder.set_entry_point("analyze")
graph = builder.build()
result = graph("Possession in midfield, 1-1, 80th minute")
```

### 19. Interrupts (Human-in-the-Loop)

Pause execution for human input (e.g., coaching decisions):

```python
class SubstitutionApproval(HookProvider):
    def approve(self, event: BeforeToolCallEvent) -> None:
        if event.tool_use["name"] != "substitute_player": return
        approval = event.interrupt("coach-approval", reason={...})
        if approval.lower() != "y":
            event.cancel_tool = "Coach rejected the substitution"

result = agent("Player 7 is tired, sub in player 12")
if result.stop_reason == "interrupt":
    for interrupt in result.interrupts:
        # Handle interrupt with user input
        pass
```

### 20. The Agent Loop

The core reasoning cycle: invoke model → check for tool use → execute tool → invoke model again → repeat until final response.

**Stop reasons:**
- `end_turn` — Model finished (normal exit)
- `tool_use` — Model wants to call a tool (loop continues)
- `max_tokens` — Response truncated (error)
- `guardrail_intervened` — Safety block
- `interrupt` — Human-in-the-loop pause

### 21. Tool Executors

Control concurrent vs sequential tool execution:

```python
from strands.tools.executors import SequentialToolExecutor
# Default: concurrent (evaluate multiple options at once)
agent = Agent(tools=[calculate_distance, should_shoot])
# Sequential (when tools depend on each other):
agent = Agent(tool_executor=SequentialToolExecutor(), tools=[...])
```

### 22. Multi-Modal Prompting

Send images/documents alongside text (useful for pre/post-match analysis):

```python
with open("opponent_heatmap.png", "rb") as f:
    image_bytes = f.read()
result = agent([
    {"text": "Analyze this opponent heatmap. Where are the gaps?"},
    {"image": {"format": "png", "source": {"bytes": image_bytes}}},
])
```

Note: During live gameplay, agents receive JSON game state, not images.

### 23. Debug Logging

Enable detailed logs for diagnosing agent behavior:

```python
import logging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s", handlers=[logging.StreamHandler()])
```

---

## Sample Agent Structure

```
fifa-agentic-football-strands/
├── src/
│   └── main.py                          # Agent implementation
├── .bedrock_agentcore.yaml.template     # AgentCore config template
├── deploy-local.sh                      # Deployment script
├── test_local.py                        # Local test suite
└── requirements.txt                     # Python dependencies (strands-agents>=1.13.0, bedrock-agentcore>=1.0.3)
```

**Getting the code:**
```bash
git clone https://github.com/aws-samples/fifa-agentic-football-strands.git
```

**What the sample does:**
1. Uses BedrockAgentCoreApp as the runtime framework for handling invocations
2. Creates a Strands Agent with `Agent(model=BedrockModel(...), system_prompt=...)`
3. Summarizes game state JSON into readable text
4. Invokes agent: `response = agent(state_summary)`
5. Parses response into game commands (JSON array)
6. Falls back to rule-based logic if LLM fails

---

## Enhancement Patterns

1. **Structured Output** — Replace manual parsing with Pydantic models
2. **Custom Tools** — Add tactical analysis (shooting angles, distances)
3. **Observability** — Track tokens, latency, tool usage per tick
4. **Hooks** — Monitor decisions, limit tool calls
5. **Model Switching** — Try Nova Micro (fast) vs Claude (capable)
6. **Guardrails** — Filter invalid commands
7. **State Tracking** — Remember opponent patterns across ticks
8. **Retry Strategy** — Handle Bedrock throttling gracefully
9. **Multi-Agent Pipeline** — Analyze → Plan → Act graph

---

## Local Testing

Start the local development server:
```bash
agentcore dev
```

In a separate terminal, send a test invocation:
```bash
agentcore invoke --dev '{"prompt": "{\"gameState\": {\"ball\": {\"position\": {\"x\": 30, \"y\": 10}}, \"players\": [], \"score\": {\"home\": 0, \"away\": 0}, \"gameTime\": 60}, \"teamId\": 0}"}'
```

## Deployment to AgentCore

Run the deployment script:
```bash
./deploy-local.sh
```

The script handles: IAM role creation, dependency packaging for ARM64, S3 upload, and agent deployment.

**Key output:** Agent ARN in format `arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-id>` — save this for portal registration.

After deployment, verify with:
```bash
agentcore status
```

View logs:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<id>-DEFAULT --follow
```

Redeploy after code changes:
```bash
./deploy-local.sh    # ARN stays the same
```

Optionally create one agent per player position (up to 5 ARNs).
