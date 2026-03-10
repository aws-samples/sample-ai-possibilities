---
name: langgraph-agents
description: "Activate when the user chooses LangGraph or asks about LangChain/ReAct patterns"
---

# LangGraph Agents Guide

Comprehensive reference for building, enhancing, and deploying football agents with LangGraph and the LangChain ReAct pattern.

## Sample Agent File Structure

```
langchain-agent/
├── src/main.py              # Main agent with LangGraph ReAct
├── test_local.py            # Local testing (--llm flag for Bedrock)
├── requirements.txt         # langgraph, langchain-aws dependencies
└── .bedrock_agentcore.yaml  # AgentCore config
```

**What the sample does:**
1. Creates a ReAct agent using `create_react_agent` with Amazon Bedrock
2. Summarizes game state JSON into readable text
3. Invokes the agent with the state summary
4. Parses the response into valid game commands
5. Falls back to rule-based logic if the LLM fails

## LangGraph Setup

### Step 1: Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Key packages: `langgraph`, `langchain-aws`, `langchain-core`, `boto3`

### Step 2: Configure the Model

```python
from langchain_aws import ChatBedrock

llm = ChatBedrock(
    model_id="us.amazon.nova-micro-v1:0",
    region_name="us-east-1",
    model_kwargs={"temperature": 0.1}
)
```

Available models via Bedrock: Amazon Nova Micro (fast, low cost), Amazon Nova Lite, Amazon Nova Pro, Anthropic Claude (more capable reasoning).

### Step 3: Test Locally

```bash
python test_local.py          # Without LLM (rule-based fallback)
python test_local.py --llm    # With Bedrock LLM integration
```

## The ReAct Agent Pattern

LangGraph's `create_react_agent` implements the Reasoning + Acting (ReAct) loop:

1. **Observe** — Receive game state (player positions, ball, score, time)
2. **Think** — LLM reasons about the situation using the system prompt
3. **Act** — LLM selects a tool or returns a final action
4. **Repeat** — If a tool was called, feed the result back and reason again

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model=llm,
    tools=[calculate_distance, evaluate_shot],
    prompt=system_prompt
)

# Invoke the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": state_summary}]
})
```

### System Prompt Design

The system prompt defines your agent's tactical identity:

```python
system_prompt = """You are a football player agent in a 5v5 match.
You receive the current game state and must return ONE action.

Available actions: MOVE_TO, SHORT_PASS, LONG_PASS, THROUGH_PASS,
CROSS, SHOOT, DRIBBLE, TACKLE, SLIDE_TACKLE, INTERCEPT, MARK,
SPRINT, WALK, RUN, STOP, IDLE, HEADER

Rules:
- You have 500ms to respond
- Consider your stamina before sprinting
- Prioritize team coordination
- Return format: ACTION_TYPE param1 param2
"""
```

## Tool Integration

Tools give your agent callable functions for tactical analysis. LangGraph uses LangChain's `@tool` decorator:

```python
from langchain_core.tools import tool

@tool
def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate distance between two points on the pitch.
    Args:
        x1: First point x coordinate
        y1: First point y coordinate
        x2: Second point x coordinate
        y2: Second point y coordinate
    """
    return ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5

@tool
def evaluate_shot(player_x: float, player_y: float, goal_x: float) -> dict:
    """Evaluate whether a shot is advisable from current position.
    Args:
        player_x: Player x coordinate
        player_y: Player y coordinate
        goal_x: Goal x coordinate (55 or -55)
    """
    distance = abs(player_x - goal_x)
    return {
        "should_shoot": distance < 30,
        "power": max(0.5, min(1.0, 1.0 - distance / 100)),
        "angle_quality": "good" if abs(player_y) < 15 else "wide"
    }

@tool
def find_open_teammate(game_state: str) -> str:
    """Analyze game state to find the best passing option.
    Args:
        game_state: JSON string of current game state
    """
    # Parse state, evaluate teammate positions, return best option
    return "Player 3 is open at (20, 10)"
```

### Binding Tools to the Agent

```python
tools = [calculate_distance, evaluate_shot, find_open_teammate]

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=system_prompt
)
```

## State Management

LangGraph uses a graph-based state model. The default `MessagesState` tracks conversation history:

```python
from langgraph.graph import MessagesState

# Default state includes a "messages" list
# Each invocation appends to the message history
result = agent.invoke({"messages": [("user", state_summary)]})
final_message = result["messages"][-1].content
```

### Custom State

For tracking match-specific data across ticks:

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages

class FootballState(TypedDict):
    messages: Annotated[list, add_messages]
    possession_count: int
    shots_taken: int
    last_action: str

def analyze_state(state: FootballState) -> FootballState:
    """Node that analyzes the current game state."""
    # Process messages, update counters
    return {"possession_count": state.get("possession_count", 0) + 1}

def decide_action(state: FootballState) -> FootballState:
    """Node that decides the next action."""
    result = llm.invoke(state["messages"])
    return {"messages": [result], "last_action": result.content}

graph = StateGraph(FootballState)
graph.add_node("analyze", analyze_state)
graph.add_node("decide", decide_action)
graph.add_edge("analyze", "decide")
graph.set_entry_point("analyze")
app = graph.compile()
```

### Conversation Management

For football agents, each tick is typically stateless (fresh invocation). If you want cross-tick memory:

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
agent = create_react_agent(model=llm, tools=tools, checkpointer=memory)

# Each invocation with the same thread_id shares history
config = {"configurable": {"thread_id": "match-001"}}
result = agent.invoke({"messages": [("user", state_summary)]}, config)
```

## Building a Custom Graph

For more control than `create_react_agent`, build a graph manually:

```python
from langgraph.graph import StateGraph, MessagesState, START, END

def call_model(state: MessagesState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: MessagesState):
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END

graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")
app = graph.compile()
```

## Deployment

### Option A: Deploy to AgentCore

**Step 1: Test locally**

```bash
python test_local.py --llm
```

**Step 2: Deploy with AgentCore CLI**

Install the CLI: https://github.com/aws/bedrock-agentcore-starter-toolkit

```bash
agentcore deploy
```

After deployment you receive a Runtime ARN — use it to register your agent for matches.

**Step 3: View logs**

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs" --follow
```

**Step 4: Register for matches**

Use the Runtime ARN from the AgentCore console. You can use one ARN for all 5 players or create separate agents per player.

### Option B: Deploy to Lambda

For a Lambda-based deployment:

1. Package your agent code and dependencies into a Lambda deployment package
2. Create a Lambda function with sufficient memory (512MB+) and timeout (30s+)
3. Configure Bedrock model access via IAM role
4. Set environment variables for model ID and region
5. Create an API Gateway endpoint or invoke directly

```python
# Lambda handler pattern
def lambda_handler(event, context):
    game_state = event.get("game_state", {})
    state_summary = summarize_game_state(game_state)
    result = agent.invoke({"messages": [("user", state_summary)]})
    return parse_action(result["messages"][-1].content)
```

## Enhancement Suggestions

### 1. Guardrails

Integrate Amazon Bedrock Guardrails for responsible AI:

```python
llm = ChatBedrock(
    model_id="us.amazon.nova-micro-v1:0",
    guardrails={"guardrailIdentifier": "your-id", "guardrailVersion": "1"}
)
```

Use guardrails to filter inappropriate content and ensure agent responses stay within game action boundaries.

### 2. Prompt Improvement

- **Be explicit about priorities**: Encode situational logic (defending a lead vs chasing a game) directly in the prompt
- **Reduce action ambiguity**: Clearly describe what each action does so the LLM reasons about trade-offs
- **Provide concise context**: Pass only what's needed for the current decision, not full match history
- **Iterate from replays**: Watch agent traces, identify poor decisions, refine the prompt for those scenarios
- **Test edge cases**: Generate unusual game states (player down, corner defense, time wasting) and verify prompt handling

### 3. Testing

- Run `test_local.py` with various game states to cover edge cases
- Test with `--llm` flag to validate Bedrock integration
- Generate diverse test scenarios: winning, losing, tied, overtime
- Verify response parsing handles malformed LLM output gracefully
- Measure response times to stay within the 500ms limit

### 4. Performance Tuning

| Technique | Description |
|-----------|-------------|
| Model selection | Nova Micro for speed, Claude for complex reasoning |
| Parallel tool calls | Enable concurrent tool execution to reduce latency |
| Efficient prompts | Minimize token count while preserving decision quality |
| Selective tool use | Only invoke tools when the situation warrants analysis |
| Temperature tuning | Lower temperature (0.0–0.2) for consistent tactical decisions |
| Caching | Cache repeated calculations (distances, angles) across ticks |

### 5. Multi-Agent Architectures

Scale beyond a single agent per player:

- **Specialist routing**: Orchestrator agent delegates to defensive/offensive specialists
- **Parallel analysis**: Multiple agents analyze different aspects simultaneously
- **Coach + player**: A coach agent sets strategy, player agents execute
- **Graph pipeline**: Chain analyzer → planner → executor nodes for structured decision-making

```python
from langgraph.graph import StateGraph

# Build a multi-step pipeline
graph = StateGraph(MessagesState)
graph.add_node("analyzer", analyze_game_state)
graph.add_node("strategist", plan_strategy)
graph.add_node("executor", execute_action)
graph.add_edge("analyzer", "strategist")
graph.add_edge("strategist", "executor")
graph.set_entry_point("analyzer")
pipeline = graph.compile()
```

## Key Differences from Strands SDK

| Aspect | LangGraph | Strands SDK |
|--------|-----------|-------------|
| Agent creation | `create_react_agent(model, tools)` | `Agent(model=model, tools=tools)` |
| Tool decorator | `@tool` from `langchain_core.tools` | `@tool` from `strands` |
| State model | Graph-based `MessagesState` | Key-value `agent.state` |
| Multi-agent | `StateGraph` with nodes and edges | `Swarm`, `GraphBuilder`, agents-as-tools |
| Conversation | `MemorySaver` checkpointer | `ConversationManager` classes |
| Streaming | `.stream()` / `.astream()` | `agent.stream_async()` |
| Model config | `ChatBedrock(model_id=...)` | `BedrockModel(model_id=...)` |

## References

- See `content-reference/en/langgraph-guide.md` for full detail
