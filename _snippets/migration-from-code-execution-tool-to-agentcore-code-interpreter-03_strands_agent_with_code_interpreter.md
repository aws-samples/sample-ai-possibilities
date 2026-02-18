---
title: "03 Strands Agent With Code Interpreter"
date: 2026-02-18
layout: snippet
language: python
description: "03 - Strands SDK + AgentCore Code Interpreter (Recommended)

This is the RECOMMENDED migration path. Strands handles the agentic loop
automatically — you define a tool, create an agent, and call it.
The result is as simple as the Anthropic experience: one call does everything.

Requirements:
    pip install strands-agents bedrock-agentcore

Usage:
    # Configure AWS credentials (IAM, SSO, or environment variables)
    python 03_strands_agent_with_code_interpreter.py"
source_file: "snippets/migration-from-code-execution-tool-to-agentcore-code-interpreter/03_strands_agent_with_code_interpreter.py"
---

# 03 Strands Agent With Code Interpreter

03 - Strands SDK + AgentCore Code Interpreter (Recommended)

This is the RECOMMENDED migration path. Strands handles the agentic loop
automatically — you define a tool, create an agent, and call it.
The result is as simple as the Anthropic experience: one call does everything.

Requirements:
    pip install strands-agents bedrock-agentcore

Usage:
    # Configure AWS credentials (IAM, SSO, or environment variables)
    python 03_strands_agent_with_code_interpreter.py

```python
"""
03 - Strands SDK + AgentCore Code Interpreter (Recommended)

This is the RECOMMENDED migration path. Strands handles the agentic loop
automatically — you define a tool, create an agent, and call it.
The result is as simple as the Anthropic experience: one call does everything.

Requirements:
    pip install strands-agents bedrock-agentcore

Usage:
    # Configure AWS credentials (IAM, SSO, or environment variables)
    python 03_strands_agent_with_code_interpreter.py
"""

from strands import Agent, tool
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
import json

# --- Configuration ---
REGION = "us-west-2"
MODEL_ID = "global.anthropic.claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an AI assistant that validates answers through code execution.
When asked to perform calculations or data analysis, use the execute_python tool
to run Python code and verify your results."""


@tool
def execute_python(code: str) -> str:
    """Execute Python code in a secure sandbox.

    Use this for calculations, data analysis, or to verify results.
    Common libraries like numpy, pandas, and matplotlib are available.

    Args:
        code: Python code to execute.
    """
    code_client = CodeInterpreter(REGION)
    code_client.start()

    try:
        response = code_client.invoke("executeCode", {
  "language": "python",
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


# --- Create agent: Claude via Bedrock + code execution via AgentCore ---
agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_python],
    model=MODEL_ID
)

# --- Run ---
if __name__ == "__main__":
    # One call — just like the Anthropic experience
    response = agent(
        "Calculate the mean and standard deviation of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"
    )
    print("\n--- Final Answer ---")
    print(response)

```

<div class='source-links'>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/blob/main/snippets/migration-from-code-execution-tool-to-agentcore-code-interpreter/03_strands_agent_with_code_interpreter.py' class='btn btn-primary'>
    View Raw File
  </a>
</div>
