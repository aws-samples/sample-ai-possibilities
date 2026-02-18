"""
04 - AgentCore Code Interpreter High-Level API (Direct, No Model)

This uses the AgentCore SDK's high-level CodeInterpreter class to execute
code directly — no Claude, no agentic loop. Useful when your application
already knows what code to run (batch jobs, testing, pipelines).

Requirements:
    pip install bedrock-agentcore

Usage:
    # Configure AWS credentials (IAM, SSO, or environment variables)
    python 04_code_interpreter_highlevel_api.py
"""

from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
import json

# --- Configuration ---
REGION = "us-west-2"


def run_code(code: str, language: str = "python") -> str:
    """Execute code using the high-level CodeInterpreter API."""
    code_client = CodeInterpreter(REGION)
    code_client.start()

    try:
        response = code_client.invoke("executeCode", {
            "language": language,
            "code": code
        })

        results = []
        for event in response["stream"]:
            if "result" in event:
                for item in event["result"].get("content", []):
                    if item["type"] == "text":
                        results.append(item["text"])
        return "\n".join(results)
    finally:
        code_client.stop()


# --- Run ---
if __name__ == "__main__":
    # Example: Same calculation as the Anthropic example, but executed directly
    code = """
import numpy as np

data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
mean = np.mean(data)
std = np.std(data)

print(f"Data: {data}")
print(f"Mean: {mean}")
print(f"Standard Deviation: {std:.4f}")
print(f"Population Std Dev: {np.std(data):.4f}")
print(f"Sample Std Dev:     {np.std(data, ddof=1):.4f}")
"""

    print("--- Executing code via AgentCore Code Interpreter ---")
    output = run_code(code)
    print(output)
