"""
02 - Bedrock InvokeModel API + AgentCore Code Interpreter

This approach uses the InvokeModel API with the native Anthropic Messages format.
The request body is nearly identical to what you'd send to api.anthropic.com,
making it the easiest path to minimize changes to existing Anthropic code.

The agentic loop is the same as the Converse API version, but the request/response
format matches the native Anthropic format.

Requirements:
    pip install boto3 bedrock-agentcore

Usage:
    # Configure AWS credentials (IAM, SSO, or environment variables)
    python 02_invoke_model_with_code_interpreter.py
"""

import boto3
import json

# --- Configuration ---
REGION = "us-west-2"
MODEL_ID = "global.anthropic.claude-sonnet-4-6"

# --- AWS Clients ---
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
agentcore = boto3.client("bedrock-agentcore", region_name=REGION)

# --- Tool definition (native Anthropic format) ---
TOOLS = [{
    "name": "execute_python",
    "description": (
        "Execute Python code in a secure sandbox. "
        "Use this for calculations, data analysis, or to verify results. "
        "Common libraries like numpy, pandas, and matplotlib are available."
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


def invoke_model_with_code_execution(user_message: str) -> str:
    """Full agentic loop: InvokeModel API + AgentCore Code Interpreter."""

    # Start a code interpreter session
    session = agentcore.start_code_interpreter_session(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        name="invoke-model-session",
        sessionTimeoutSeconds=900
    )
    session_id = session["sessionId"]
    print(f"[Session started: {session_id}]")

    messages = [{"role": "user", "content": [{"type": "text", "text": user_message}]}]

    try:
        while True:
            # Step 1: Call Claude via InvokeModel (native Anthropic format)
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "tools": TOOLS
            }

            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": result["content"]})

            # Step 2: If Claude is done (no tool request), return the answer
            if result["stop_reason"] != "tool_use":
                break

            # Step 3: Execute any requested tools
            tool_results = []
            for block in result["content"]:
                if block["type"] == "tool_use":
                    print(f"[Executing code...]")
                    try:
                        output = execute_code(block["input"]["code"], session_id)
                        print(f"[Code output: {output[:100]}...]")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": [{"type": "text", "text": output}]
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": [{"type": "text", "text": str(e)}],
                            "is_error": True
                        })

            # Step 4: Send tool results back to Claude and loop
            messages.append({"role": "user", "content": tool_results})

        # Extract final text response
        return "\n".join(
            b["text"] for b in result["content"] if b["type"] == "text"
        )

    finally:
        # Always clean up the session
        agentcore.stop_code_interpreter_session(
            codeInterpreterIdentifier="aws.codeinterpreter.v1",
            sessionId=session_id
        )
        print(f"[Session stopped: {session_id}]")


# --- Run ---
if __name__ == "__main__":
    answer = invoke_model_with_code_execution(
        "Calculate the mean and standard deviation of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"
    )
    print("\n--- Final Answer ---")
    print(answer)
