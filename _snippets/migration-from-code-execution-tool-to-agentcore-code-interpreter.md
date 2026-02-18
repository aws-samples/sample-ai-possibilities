---
title: "Migration: Anthropic Code Execution Tool to AgentCore Code Interpreter"
date: 2026-02-18
description: "This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file."
layout: snippet
difficulty: intermediate
source_folder: "snippets/migration-from-code-execution-tool-to-agentcore-code-interpreter"

tags:
  - `migration`, `code-interpreter`, `bedrock`, `agentcore`, `anthropic`, `strands`, `prompt-caching`, `claude-code`, `programmatic-tool-calling`
technologies:
  - Amazon Bedrock (Claude via Converse API and InvokeModel API)
  - Amazon Bedrock AgentCore Code Interpreter
  - Strands Agents SDK
  - Claude Code CLI (in sandbox)
  - Bedrock Prompt Caching
  - Anthropic API (reference only)
  - Python 3.10+
---

# Migration: Anthropic Code Execution Tool to AgentCore Code Interpreter

## Overview

This snippet shows how to migrate from the **Anthropic API Code Execution tool** to **Amazon Bedrock + AgentCore Code Interpreter**. It provides side-by-side working examples: the original Anthropic approach (one API call, everything handled server-side) and multiple equivalent implementations on AWS.

All examples (00-04, 06) use the same prompt (a simple math calculation) — *"Calculate the mean and standard deviation of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"* — so you can directly compare the code and output across approaches.

### Key Architectural Difference

| Anthropic | AWS (Bedrock + AgentCore) |
|---|---|
| One API call does everything | Two services composed together |
| No agentic loop needed | Orchestration layer required (or use Strands) |
| No session management | Explicit session start/stop lifecycle |

## Tags

`migration`, `code-interpreter`, `bedrock`, `agentcore`, `anthropic`, `strands`, `prompt-caching`, `claude-code`, `programmatic-tool-calling`

## Technologies

- Amazon Bedrock (Claude via Converse API and InvokeModel API)
- Amazon Bedrock AgentCore Code Interpreter
- Strands Agents SDK
- Claude Code CLI (in sandbox)
- Bedrock Prompt Caching
- Anthropic API (reference only)
- Python 3.10+

## Difficulty

Intermediate

## Sample Files

| File | Approach | Description |
|---|---|---|
| `00_anthropic_code_execution.py` | Anthropic API | **BEFORE** — The original. One API call, Claude handles code execution server-side. No loop, no session management. |
| `01_converse_api_with_code_interpreter.py` | Converse API + AgentCore | Custom agentic loop using the AWS-recommended Converse API. Model-agnostic format that works across Claude, Nova, etc. |
| `02_invoke_model_with_code_interpreter.py` | InvokeModel API + AgentCore | Custom agentic loop using native Anthropic Messages format. Easiest to port from existing Anthropic code. |
| `03_strands_agent_with_code_interpreter.py` | Strands SDK + AgentCore | **RECOMMENDED** — Strands handles the agentic loop automatically. Closest to the Anthropic "one call" simplicity. |
| `04_code_interpreter_highlevel_api.py` | AgentCore SDK (direct) | Execute code directly without a model. Useful for batch jobs, testing, or when you already know what code to run. |
| `05_claude_code_in_code_interpreter/` | Claude Code in sandbox | Run Claude Code CLI inside a Code Interpreter sandbox. Requires a custom Code Interpreter with PUBLIC network mode and an IAM execution role. See [05 README](05_claude_code_in_code_interpreter/README.md). |
| `06_invoke_model_with_caching.py` | InvokeModel + Prompt Caching | Demonstrates Bedrock prompt caching to reduce cost and latency in agentic loops. Uses a regional model ID (required for caching). |
| `07_programmatic_tool_calling.py` | Programmatic Tool Calling | Demonstrates the programmatic tool calling pattern on Bedrock: pre-loads tools into the sandbox so the model can call multiple tools in a single code execution — reducing round-trips and token usage. |

### Choosing the Right Approach

- **Migrating existing Anthropic code?** Start with `02` (InvokeModel) — the request format is nearly identical.
- **New project or want simplicity?** Use `03` (Strands) — one call does everything, just like Anthropic.
- **Need model-agnostic code?** Use `01` (Converse) — works with Claude, Nova, Cohere, etc.
- **Don't need a model?** Use `04` (direct) — just run code in a sandbox.
- **Want a full coding agent in a sandbox?** Use `05` (Claude Code) — runs the full Claude Code CLI inside Code Interpreter.
- **Optimizing cost for agentic loops?** Use `06` (caching) — caches system prompt and tools across repeated calls.
- **Calling many tools per turn?** Use `07` (programmatic) — model writes code that calls all tools at once, reducing round-trips.

### Network Mode Impact

Most examples (01-04, 06, 07) use the **default sandbox** (`aws.codeinterpreter.v1`) — no network access, no custom setup. This is sufficient for computation, data analysis, and demos with static data.

For **real tool integrations** (APIs, databases, AWS services), use a **custom Code Interpreter with PUBLIC network mode** and an IAM execution role. This lets your pre-loaded functions make real HTTP/SDK calls directly from inside the sandbox. See `05_claude_code_in_code_interpreter/` for setup.

| Network Mode | Use Case | Setup |
|---|---|---|
| Default (no network) | Computation, data analysis, demos | None — works out of the box |
| PUBLIC + IAM role | Real API calls, DB queries, AWS SDK | Custom Code Interpreter ([setup guide](05_claude_code_in_code_interpreter/README.md)) |

### Model ID Notes

- Scripts 01-04 use `global.anthropic.claude-sonnet-4-6` (cross-region routing for lowest latency).
- Script 06 uses `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (regional ID, **required for prompt caching** — cross-region IDs route to different regions, preventing cache hits).

## Prerequisites

- AWS Account with [Amazon Bedrock](https://aws.amazon.com/bedrock/) access
- Claude model enabled in the Bedrock console (us-west-2)
- IAM credentials with AgentCore and Bedrock permissions
- Python 3.10+
- AWS CLI configured (`aws configure` or SSO)

## Setup

```bash
# Navigate to the snippet directory
cd snippets/migration-from-code-execution-tool-to-agentcore-code-interpreter

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the examples

```bash
# Recommended: Strands SDK (simplest, closest to Anthropic experience)
python 03_strands_agent_with_code_interpreter.py

# Converse API with custom agentic loop
python 01_converse_api_with_code_interpreter.py

# InvokeModel API with custom agentic loop (native Anthropic format)
python 02_invoke_model_with_code_interpreter.py

# Direct code execution (no model)
python 04_code_interpreter_highlevel_api.py

# InvokeModel with prompt caching
python 06_invoke_model_with_caching.py

# Programmatic tool calling (multiple tools in one code execution)
python 07_programmatic_tool_calling.py

# Claude Code in sandbox (see 05_claude_code_in_code_interpreter/README.md)
cd 05_claude_code_in_code_interpreter
python setup_infrastructure.py  # one-time
python run.py <code-interpreter-id> "Your prompt"

# Anthropic reference (requires ANTHROPIC_API_KEY)
# export ANTHROPIC_API_KEY=your_key
# python 00_anthropic_code_execution.py
```

## Security

See [CONTRIBUTING](../../CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](../../LICENSE) file.


<div class='source-links'>
  <h3>View Source</h3>
  <a href='https://github.com/aws-samples/sample-ai-possibilities/tree/main/snippets/migration-from-code-execution-tool-to-agentcore-code-interpreter' class='btn btn-primary'>
    View on GitHub
  </a>
</div>
