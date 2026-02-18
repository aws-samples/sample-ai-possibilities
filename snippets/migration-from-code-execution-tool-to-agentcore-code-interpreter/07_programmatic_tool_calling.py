"""
07 - Programmatic Tool Calling Pattern with AgentCore Code Interpreter

Demonstrates the programmatic tool calling pattern on Bedrock: reduced
round-trips, data processed in code, and only summaries returned to the
model's context window.

Instead of one model round-trip per tool call:

  Traditional:  Model → tool_A → Model → tool_B → Model → tool_C → Model
  Programmatic: Model → code(tool_A, tool_B, tool_C) → Model

How it works:
  1. Pre-load your tool functions into the Code Interpreter sandbox session
  2. Tell the model which functions are available (via system prompt)
  3. Model writes Python that calls the tools and processes results
  4. One code execution replaces multiple tool round-trips

Architectural note — Anthropic vs. this pattern:
  Anthropic's managed PTC uses a pause-and-resume mechanism: the code container
  pauses when a tool is called, dispatches execution back to YOUR application,
  then resumes with the result. Tools run client-side.

  This pattern pre-loads tool functions INTO the sandbox so they execute directly
  inside it. The efficiency outcome is the same (fewer round-trips, data filtering
  in code, only processed results reach the model), but the tools run in the
  sandbox rather than being dispatched to the client.

  Both approaches keep intermediate tool results OUT of the model's context —
  only the final printed output is returned.

Network modes and real tools:
  This example uses the default sandbox (aws.codeinterpreter.v1) with static
  data — no network needed. In production, you have two options:

  - DEFAULT (no network): Tools must be self-contained (static data, local
    computation). Good for demos, testing, and data processing.

  - PUBLIC network mode (custom Code Interpreter): Tools can make real HTTP
    requests, AWS SDK calls, and database queries directly from inside the
    sandbox. Combined with an IAM execution role for credentials, your
    pre-loaded functions can call real services, process the results in code,
    and return only the summary to the model.
    See 05_claude_code_in_code_interpreter/ for setup.

  Example of a real tool in PUBLIC mode:
    def get_weather(city: str) -> dict:
        resp = requests.get(f"https://api.weather.com/v1/current?city={city}")
        return resp.json()

NOTE: This pattern works with any API — InvokeModel (shown here), Converse API,
or Strands Agents. The core idea (pre-load tools, model writes code) is the same.

Requirements:
    pip install boto3 bedrock-agentcore

Usage:
    python 07_programmatic_tool_calling.py
"""

import boto3
import json

# --- Configuration ---
REGION = "us-west-2"
MODEL_ID = "global.anthropic.claude-sonnet-4-6"

# --- AWS Clients ---
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
agentcore = boto3.client("bedrock-agentcore", region_name=REGION)


# --- Tool functions to pre-load into the sandbox ---
# In production, replace these with real API calls, SDK calls, or DB queries.
TOOL_FUNCTIONS = '''
def get_weather(city: str) -> dict:
    """Get current weather for a city. (Simulated — replace with a real weather API.)"""
    data = {
        "Seattle": {"temp_f": 58, "humidity_pct": 82, "condition": "Cloudy", "wind_mph": 12},
        "Portland": {"temp_f": 62, "humidity_pct": 75, "condition": "Partly Cloudy", "wind_mph": 8},
        "San Francisco": {"temp_f": 65, "humidity_pct": 70, "condition": "Foggy", "wind_mph": 15},
        "Los Angeles": {"temp_f": 78, "humidity_pct": 45, "condition": "Sunny", "wind_mph": 5},
        "Denver": {"temp_f": 72, "humidity_pct": 30, "condition": "Clear", "wind_mph": 10},
    }
    return data.get(city, {"error": f"No weather data for {city}"})


def get_population(city: str) -> dict:
    """Get population stats. (Simulated — replace with a census API or database query.)"""
    data = {
        "Seattle": {"population": 749256, "metro_population": 4018762, "state": "WA"},
        "Portland": {"population": 652503, "metro_population": 2512859, "state": "OR"},
        "San Francisco": {"population": 808437, "metro_population": 4749008, "state": "CA"},
        "Los Angeles": {"population": 3898747, "metro_population": 13200998, "state": "CA"},
        "Denver": {"population": 713252, "metro_population": 2963821, "state": "CO"},
    }
    return data.get(city, {"error": f"No population data for {city}"})


def get_cost_of_living(city: str) -> dict:
    """Get cost of living index. (Simulated — replace with a real data source.)"""
    data = {
        "Seattle": {"index": 172, "median_rent_1br": 2100, "median_home_price": 850000},
        "Portland": {"index": 130, "median_rent_1br": 1650, "median_home_price": 550000},
        "San Francisco": {"index": 190, "median_rent_1br": 2800, "median_home_price": 1400000},
        "Los Angeles": {"index": 166, "median_rent_1br": 2400, "median_home_price": 950000},
        "Denver": {"index": 128, "median_rent_1br": 1700, "median_home_price": 580000},
    }
    return data.get(city, {"error": f"No cost data for {city}"})


print("Tools loaded: get_weather(), get_population(), get_cost_of_living()")
'''


# --- System prompt: tells the model about pre-loaded tools ---
SYSTEM_PROMPT = """You are a helpful assistant. You have access to a Python sandbox with
these functions already loaded and ready to call:

- get_weather(city: str) -> dict
  Returns: {"temp_f", "humidity_pct", "condition", "wind_mph"}

- get_population(city: str) -> dict
  Returns: {"population", "metro_population", "state"}

- get_cost_of_living(city: str) -> dict
  Returns: {"index", "median_rent_1br", "median_home_price"}

Available cities: Seattle, Portland, San Francisco, Los Angeles, Denver.

IMPORTANT: When answering questions, write Python code that calls MULTIPLE tools
in a single code block, processes the results, and prints a clear summary.
This is more efficient than calling tools one at a time — you reduce round-trips
and can filter/aggregate data before it reaches your context window."""


# --- Single tool: execute code in the sandbox ---
TOOLS = [{
    "name": "execute_python",
    "description": (
        "Execute Python code in the sandbox. Pre-loaded functions available: "
        "get_weather(city), get_population(city), get_cost_of_living(city). "
        "Call multiple functions in a single code block for efficiency."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            }
        },
        "required": ["code"]
    }
}]


def execute_code(code: str, session_id: str) -> str:
    """Execute code via AgentCore and return the output."""
    response = agentcore.invoke_code_interpreter(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        sessionId=session_id,
        name="executeCode",
        arguments={"language": "python", "code": code}
    )
    parts = []
    for event in response["stream"]:
        if "result" in event:
            for item in event["result"].get("content", []):
                if item["type"] == "text":
                    parts.append(item["text"])
    return "\n".join(parts)


def ask(user_message: str, session_id: str) -> dict:
    """
    Send a message to Claude. The model writes code that calls pre-loaded
    tools programmatically — multiple tools in a single execution.

    Returns the final answer and the number of model round-trips.
    """
    messages = [{"role": "user", "content": [{"type": "text", "text": user_message}]}]
    round_trips = 0

    while True:
        round_trips += 1

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": [{"type": "text", "text": SYSTEM_PROMPT}],
            "messages": messages,
            "tools": TOOLS,
        }

        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(response["body"].read())
        messages.append({"role": "assistant", "content": result["content"]})

        # Done — no more tool calls
        if result["stop_reason"] != "tool_use":
            answer = "\n".join(
                b["text"] for b in result["content"] if b["type"] == "text"
            )
            return {"answer": answer, "round_trips": round_trips}

        # Execute tool calls
        tool_results = []
        for block in result["content"]:
            if block["type"] == "tool_use":
                print(f"  [Executing code block...]")
                output = execute_code(block["input"]["code"], session_id)
                print(f"  [Output: {output[:150]}...]")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": [{"type": "text", "text": output}],
                })

        messages.append({"role": "user", "content": tool_results})


def main():
    # Start a session
    session = agentcore.start_code_interpreter_session(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        name="programmatic-tools",
        sessionTimeoutSeconds=900,
    )
    session_id = session["sessionId"]
    print(f"Session: {session_id}\n")

    try:
        # Step 1: Pre-load tool functions into the sandbox
        # The session persists state — functions stay available for all subsequent calls.
        print("--- Loading tools into sandbox ---")
        output = execute_code(TOOL_FUNCTIONS, session_id)
        print(output)

        # Step 2: Ask a question that requires MULTIPLE tools
        #
        # Without programmatic tool calling (traditional approach):
        #   Round 1: Model → get_weather("Seattle")     → result back to model
        #   Round 2: Model → get_weather("Portland")    → result back to model
        #   Round 3: Model → get_weather("SF")          → result back to model
        #   ... repeat for population and cost_of_living ...
        #   ~15 tool calls = ~16 model round-trips
        #
        # With programmatic tool calling:
        #   Round 1: Model → code that calls ALL tools   → processed summary
        #   Round 2: Model → final answer
        #   = 2 model round-trips
        #
        query = (
            "Compare all 5 cities across weather, population, and cost of living. "
            "Which city has the best combination of warm weather, large metro area, "
            "and affordable rent? Rank them."
        )
        print(f"\n--- Query ---\n{query}\n")

        result = ask(query, session_id)

        print(f"\n--- Answer ---\n{result['answer']}")
        print(f"\n--- Efficiency ---")
        print(f"Model round-trips used: {result['round_trips']}")
        print(f"Traditional approach would need ~16 round-trips (15 tool calls + final answer)")
        print(f"Programmatic approach: model calls all tools in code, processes results, returns summary")

    finally:
        agentcore.stop_code_interpreter_session(
            codeInterpreterIdentifier="aws.codeinterpreter.v1",
            sessionId=session_id,
        )
        print(f"\nSession stopped: {session_id}")


if __name__ == "__main__":
    main()
