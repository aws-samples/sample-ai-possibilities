---
name: strands-agents
description: "Activate when the user chooses Strands or asks about Strands SDK concepts"
---

# Strands Agents SDK Guide

Comprehensive reference for building, enhancing, and deploying football agents with the Strands Agents SDK.

## Sample Agent File Structure

```
sample-agent-strands/
├── src/main.py              # Main agent with Strands SDK
├── test_local.py            # Local testing
├── requirements.txt         # strands-agents dependency
└── .bedrock_agentcore.yaml  # AgentCore config
```

**What the sample does:**
1. Creates a Strands Agent with `Agent(model=BedrockModel(...), system_prompt=...)`
2. Summarizes game state JSON into readable text
3. Invokes the agent: `response = agent(state_summary)`
4. Parses the response into game commands
5. Falls back to rule-based logic if the LLM fails

**Key code pattern:**

```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")
agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

response = agent(state_summary)
commands = parse_commands(str(response), team_id)
```

## Core Strands SDK Concepts (23 Total)

### 1. Structured Output

Return validated, type-safe responses using Pydantic models instead of raw text.

```python
from pydantic import BaseModel, Field
from strands import Agent

class FootballAction(BaseModel):
    commandType: str = Field(description="MOVE_TO, SHOOT, PASS, etc.")
    playerId: int
    parameters: dict
    duration: int = 0

agent = Agent(system_prompt="Analyze game state, return ONE action.")
result = agent("Ball at (10,5), I'm at (0,0).", structured_output_model=FootballAction)
action = result.structured_output  # Type-safe FootballAction
```

### 2. Custom Tools

Give your agent callable functions for tactical analysis:

```python
from strands import Agent, tool

@tool
def should_shoot(player_x: float, goal_x: float) -> dict:
    """Determine if player should shoot based on distance to goal.
    Args:
        player_x: Player's x coordinate
        goal_x: Goal's x coordinate (55 or -55)
    """
    distance = abs(player_x - goal_x)
    return {'should_shoot': distance < 30, 'power': max(0.5, min(1.0, 1.0 - distance/100))}

agent = Agent(tools=[should_shoot], system_prompt="Use tools to decide actions.")
```

### 3. Model Providers

Switch between models easily:

```python
from strands.models import BedrockModel

model = BedrockModel(model_id="us.amazon.nova-micro-v1:0")  # Fast, cheap
# model = BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0")  # More capable
agent = Agent(model=model)
```

### 4. Observability

Track tokens, latency, and tool usage:

```python
result = agent("What should I do?")
summary = result.metrics.get_summary()
print(f"Tokens: {summary['accumulated_usage']['totalTokens']}")
print(f"Latency: {summary['accumulated_metrics']['latencyMs']}ms")
print(f"Tool calls: {summary['tool_usage']}")
```

### 5. Hooks

Monitor and control agent behavior at lifecycle points:

```python
from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent, AfterToolCallEvent

class FootballMonitoringHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.log_start)
        registry.add_callback(AfterToolCallEvent, self.log_end)
    def log_start(self, event: BeforeToolCallEvent) -> None:
        print(f"Calling: {event.tool_use['name']}")
    def log_end(self, event: AfterToolCallEvent) -> None:
        print(f"Result: {event.result}")

agent = Agent(tools=[should_shoot], hooks=[FootballMonitoringHook()])
```

Advanced: limit tool calls per invocation with `BeforeInvocationEvent` to reset counters and `BeforeToolCallEvent` to check limits via `event.cancel_tool`.

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
    print("Blocked by guardrails")
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
agent = Agent(tools=[calculator, python_repl])
```

Useful for football: `calculator` (math), `python_repl` (complex calculations), `current_time` (match timing).

### 9. Conversation Management

Control how message history is handled:

```python
from strands.agent.conversation_manager import (
    NullConversationManager, SlidingWindowConversationManager, SummarizingConversationManager
)

# Keep recent messages (default)
agent = Agent(conversation_manager=SlidingWindowConversationManager(window_size=10))

# No trimming
agent = Agent(conversation_manager=NullConversationManager())

# Summarize old messages
agent = Agent(conversation_manager=SummarizingConversationManager(
    summary_ratio=0.3, preserve_recent_messages=10
))
```

For football: typically stateless per tick (fresh agent each time).

### 10. Agent State Management

Key-value storage across invocations — not sent to the model:

```python
from strands import tool, ToolContext

@tool(context=True)
def track_opponent(opponent_id: int, tendency: str, tool_context: ToolContext) -> str:
    """Record an opponent's tendency.
    Args:
        opponent_id: Opponent player ID
        tendency: Observed tendency
    """
    tendencies = tool_context.agent.state.get("opponent_tendencies") or {}
    tendencies[str(opponent_id)] = tendency
    tool_context.agent.state.set("opponent_tendencies", tendencies)
    return f"Recorded: player {opponent_id} → {tendency}"

agent = Agent(tools=[track_opponent], state={"opponent_tendencies": {}})
```

### 11. Session Management

Persist state and conversation across restarts:

```python
from strands.session.file_session_manager import FileSessionManager

session_mgr = FileSessionManager(session_id="team-alpha", storage_dir="./sessions")
agent = Agent(session_manager=session_mgr, state={"patterns": {}})
# After redeployment, restore with same session_id
```

Use `S3SessionManager` for cloud deployments.

### 12. Retry Strategies

Handle model throttling during high-frequency ticks:

```python
from strands import ModelRetryStrategy
agent = Agent(retry_strategy=ModelRetryStrategy(max_attempts=3, initial_delay=2, max_delay=60))
# Or disable: agent = Agent(retry_strategy=None)
```

### 13. Streaming

Monitor decisions in real-time with async iterators:

```python
async for event in agent.stream_async("Ball at (30,10), should I shoot?"):
    if "data" in event:
        print(event["data"], end="")
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
        """Record a shot attempt. Args: result: 'goal', 'saved', or 'missed'"""
        self.shots_taken += 1
        return f"Shot #{self.shots_taken}: {result}"

analytics = MatchAnalytics()
agent = Agent(tools=[analytics.record_shot])
```

### 15. MCP Tools

Connect to external tool servers via Model Context Protocol:

```python
from strands.tools.mcp import MCPClient
from mcp.client.sse import sse_client

mcp_client = MCPClient(lambda: sse_client("http://localhost:8000/sse"))
with mcp_client:
    agent = Agent(tools=mcp_client.list_tools_sync())
```

### 16. Multi-Agent — Agents as Tools

Wrap specialist agents as tools for an orchestrator:

```python
@tool
def defensive_analyst(game_state: str) -> str:
    """Analyze defensive positioning.
    Args: game_state: Current game state summary"""
    return str(Agent(system_prompt="You are a defensive analyst.")(game_state))

@tool
def offensive_strategist(game_state: str) -> str:
    """Plan attacking moves.
    Args: game_state: Current game state summary"""
    return str(Agent(system_prompt="You are an attacking strategist.")(game_state))

coach = Agent(tools=[defensive_analyst, offensive_strategist],
    system_prompt="Route to the right specialist based on game situation.")
```

### 17. Multi-Agent — Swarm

Collaborative agents that autonomously hand off tasks:

```python
from strands.multiagent import Swarm

scout = Agent(name="scout", system_prompt="Analyze opponent weaknesses.")
tactician = Agent(name="tactician", system_prompt="Design game plans.")
coach = Agent(name="coach", system_prompt="Finalize tactics.")

swarm = Swarm([scout, tactician, coach], entry_point=scout, max_handoffs=10)
result = swarm("Prepare a plan against a 4-4-2 high-pressing team")
```

### 18. Multi-Agent — Graph

Structured pipeline with defined execution order:

```python
from strands.multiagent import GraphBuilder

analyzer = Agent(name="analyzer", system_prompt="Analyze game state.")
planner = Agent(name="planner", system_prompt="Create tactical plan.")
executor = Agent(name="executor", system_prompt="Convert plan to player actions.")

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

### 19. Interrupts

Pause execution for human input (coaching decisions):

```python
from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

class SubstitutionApproval(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.approve)
    def approve(self, event: BeforeToolCallEvent) -> None:
        if event.tool_use["name"] == "substitute_player":
            approval = event.interrupt("coach-approval",
                reason={"out": event.tool_use["input"]["player_out"],
                        "in": event.tool_use["input"]["player_in"]})
            if approval.lower() != "y":
                event.cancel_tool = "Coach rejected the substitution"

# Handle interrupt: check result.stop_reason == "interrupt", then respond
```

### 20. Agent Loop

The core cycle: invoke model → check for tool call → execute tool → re-invoke model → repeat until final response.

Stop reasons: `end_turn` (normal), `tool_use` (loop continues), `max_tokens` (truncated), `guardrail_intervened` (blocked), `interrupt` (paused).

```python
result = agent("Ball at (30,10), should I shoot?")
print(f"Stop reason: {result.stop_reason}")
print(f"Messages: {len(agent.messages)}")
```

### 21. Tool Executors

Control concurrent vs sequential tool execution:

```python
from strands.tools.executors import SequentialToolExecutor

agent = Agent(tools=[...])  # Default: concurrent (faster)
agent = Agent(tool_executor=SequentialToolExecutor(), tools=[...])  # Sequential
```

### 22. Multi-Modal Prompting

Send images/documents alongside text (useful for pre/post-match analysis):

```python
with open("opponent_heatmap.png", "rb") as f:
    image_bytes = f.read()
result = agent([
    {"text": "Analyze this opponent heatmap. Where are the gaps?"},
    {"image": {"format": "png", "source": {"bytes": image_bytes}}}
])
```

Note: During live gameplay your agent receives JSON game state, not images.

### 23. Debug Logging

Enable detailed logs for diagnosing agent behavior:

```python
import logging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()])
```

## Enhancement Patterns

Apply these to the sample agent — each maps to a core concept above:

| Enhancement | How | Core Concept |
|-------------|-----|--------------|
| Structured Output | Pass `structured_output_model=GameCommand` (Pydantic) to `agent()` — replaces manual parsing | #1 |
| Custom Tools | Add `@tool` functions (e.g., shooting angle calculator) to `Agent(tools=[...])` | #2 |
| Observability | Read `result.metrics.get_summary()` for tokens, latency, tool usage | #4 |
| Hooks | Create a `HookProvider` subclass, register callbacks for `BeforeInvocationEvent` | #5 |
| Model Switching | Swap `BedrockModel(model_id=...)` — Nova Micro for speed, Claude for complex tactics | #3 |
| Guardrails | Add `guardrail_id` and `guardrail_version` to `BedrockModel(...)` | #6 |
| State Tracking | Use `tool_context.agent.state.get/set` in `@tool(context=True)` functions | #10 |
| Retry Strategy | Add `retry_strategy=ModelRetryStrategy(max_attempts=3, initial_delay=1)` | #12 |
| Multi-Agent Pipeline | Use `GraphBuilder` to chain analyzer → planner → executor agents | #18 |

## Deploying to AgentCore

### Step 1: Test Locally

```bash
python test_local.py          # Without LLM
python test_local.py --llm    # With LLM
```

### Step 2: Deploy

```bash
agentcore deploy
```

After deployment you receive a Runtime ARN — use it to register your agent for matches.

### Step 3: View Logs

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs" --follow
```

### Step 4: Register for Matches

Use the Runtime ARN from the AgentCore console to register your agent. You can use one ARN for all 5 players or create separate agents per player for diversity.

## References

- See `content-reference/en/strands-guide.md` for full detail
