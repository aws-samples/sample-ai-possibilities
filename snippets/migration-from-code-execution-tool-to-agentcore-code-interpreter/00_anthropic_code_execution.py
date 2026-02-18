"""
00 - Anthropic Code Execution Tool (BEFORE - Reference)

This is the ORIGINAL Anthropic approach. One API call — Claude decides to execute
code, runs it in a managed container, and returns the answer inline.
No agentic loop. No tool-use handling. No session management.

This is what we are migrating FROM.

Requirements:
    pip install anthropic

Usage:
    export ANTHROPIC_API_KEY=your_key
    python 00_anthropic_code_execution.py
"""

import anthropic

client = anthropic.Anthropic()

# One API call — Claude handles everything server-side
response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250929",
    betas=["code-execution-2025-08-25"],
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": "Calculate the mean and standard deviation of "
                   "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"
    }],
    tools=[{
        "type": "code_execution_20250825",
        "name": "code_execution"
    }]
)

# Results are inline — no loop needed
for block in response.content:
    if block.type == "text":
        print(block.text)
    elif block.type == "code_execution_tool_result":
        print(f"[Code Output] {block.content}")
