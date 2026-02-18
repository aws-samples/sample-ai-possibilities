"""
01 - Bedrock Converse API + AgentCore Code Interpreter

This is the custom agentic loop approach using the Converse API.
It wires together two AWS services:
  - Bedrock Runtime (Converse API) for Claude
  - AgentCore Code Interpreter for sandboxed code execution

The loop: Claude → tool_use? → execute code → return result → Claude → final answer.

Requirements:
    pip install boto3 bedrock-agentcore

Usage:
    # Configure AWS credentials (IAM, SSO, or environment variables)
    python 01_converse_api_with_code_interpreter.py
"""

import boto3

# --- Configuration ---
REGION = "us-west-2"
MODEL_ID = "global.anthropic.claude-sonnet-4-6"

# --- AWS Clients ---
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
agentcore = boto3.client("bedrock-agentcore", region_name=REGION)

# --- Tool definition for Claude ---
tool_config = {
    "tools": [{
        "toolSpec": {
            "name": "execute_python",
            "description": (
                "Execute Python code in a secure sandbox. "
                "Use this for calculations, data analysis, or to verify results. "
                "Common libraries like numpy, pandas, and matplotlib are available."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        }
                    },
                    "required": ["code"]
                }
            }
        }
    }]
}


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


def converse_with_code_execution(user_message: str) -> str:
    """Full agentic loop: Converse API + AgentCore Code Interpreter."""

    # Start a code interpreter session
    session = agentcore.start_code_interpreter_session(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        name="converse-session",
        sessionTimeoutSeconds=900
    )
    session_id = session["sessionId"]
    print(f"[Session started: {session_id}]")

    messages = [{"role": "user", "content": [{"text": user_message}]}]

    try:
        while True:
            # Step 1: Call Claude via Converse API
            response = bedrock.converse(
                modelId=MODEL_ID,
                messages=messages,
                toolConfig=tool_config,
                inferenceConfig={"maxTokens": 4096}
            )

            assistant_msg = response["output"]["message"]
            messages.append(assistant_msg)

            # Step 2: If Claude is done (no tool request), return the answer
            if response["stopReason"] != "tool_use":
                break

            # Step 3: Execute any requested tools
            tool_results = []
            for block in assistant_msg["content"]:
                if "toolUse" in block:
                    tool = block["toolUse"]
                    print(f"[Executing code...]")
                    try:
                        result = execute_code(tool["input"]["code"], session_id)
                        print(f"[Code output: {result[:100]}...]")
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool["toolUseId"],
                                "content": [{"text": result}],
                                "status": "success"
                            }
                        })
                    except Exception as e:
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool["toolUseId"],
                                "content": [{"text": str(e)}],
                                "status": "error"
                            }
                        })

            # Step 4: Send tool results back to Claude and loop
            messages.append({"role": "user", "content": tool_results})

        # Extract final text response
        return "\n".join(
            b["text"] for b in assistant_msg["content"] if "text" in b
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
    answer = converse_with_code_execution(
        "Calculate the mean and standard deviation of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"
    )
    print("\n--- Final Answer ---")
    print(answer)
