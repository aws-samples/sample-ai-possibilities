# Running Claude Code inside AgentCore Code Interpreter

## Overview

This sample runs [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic's AI coding agent CLI) inside an AgentCore Code Interpreter sandbox. Claude Code calls Bedrock using IAM credentials provided by the sandbox's execution role — no API keys needed. We wll be using us-west-2 region in this sample.

### How it works

```
Your machine                          AWS
┌──────────┐     ┌──────────────────────────────────────────────┐
│ run.py   │────>│  Code Interpreter (PUBLIC network)           │
│          │     │  ┌─────────────────────────────────────────┐ │
│          │     │  │  Node.js + Claude Code CLI              │ │
│          │     │  │    │                                    │ │
│          │     │  │    ├─> claude -p "prompt"               │ │
│          │     │  │    │     │                              │ │
│          │     │  │    │     ├─> Bedrock (Claude model)     │ │
│          │     │  │    │     │     via IAM execution role   │ │
│          │     │  │    │     │                              │ │
│          │     │  │    │     ├─> Read/Write files           │ │
│          │     │  │    │     └─> Execute bash commands      │ │
│          │     │  │    │                                    │ │
│          │     │  │    └─> Return output                    │ │
│          │     │  └─────────────────────────────────────────┘ │
│          │<────│  (output)                                    │
└──────────┘     └──────────────────────────────────────────────┘
```

### Key requirements

1. **Custom Code Interpreter** with `PUBLIC` network mode (so the sandbox can download Node.js/npm packages and reach Bedrock)
2. **IAM execution role** with `bedrock:InvokeModel` permissions (so Claude Code can call Bedrock from inside the sandbox)
3. **Environment variables**: `CLAUDE_CODE_USE_BEDROCK=1` tells Claude Code to use Bedrock instead of the Anthropic API

## Prerequisites

- AWS Account with Bedrock and AgentCore access
- Claude Sonnet 4.6 enabled in the Bedrock console
- IAM permissions to create roles and Code Interpreters
- Python 3.10+, AWS CLI configured

## Setup

### Step 1: Create the infrastructure (one-time)

```bash
cd 05_claude_code_in_code_interpreter
python setup_infrastructure.py
```

This creates:

**IAM Role** (`CodeInterpreterClaudeCodeRole`):
```json
{
    "Trust": { "Service": "bedrock-agentcore.amazonaws.com" },
    "Permissions": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
    ]
}
```

**Custom Code Interpreter** (`claudeCodePublic`) with:
- `networkMode: PUBLIC` — sandbox can reach the internet
- `executionRoleArn` — sandbox assumes the IAM role above

The script prints the Code Interpreter ID. Save it for the next step.

### Step 2: Run Claude Code

```bash
# Simple prompt
python run.py <code-interpreter-id> "Write a hello world in Python"

# File creation + execution
python run.py <code-interpreter-id> "Create stats.py that calculates mean of [1..10], run it"

# Code analysis
python run.py <code-interpreter-id> "Read app.py and explain what it does"
```

## What happens when you run it

1. **Start session** — A new Code Interpreter session starts with your custom interpreter
2. **Install Node.js** — Downloads and extracts Node.js v22 inside `/tmp/` (~30s)
3. **Install Claude Code** — `npm install -g @anthropic-ai/claude-code` (~15s)
4. **Run prompt** — Executes `claude -p "<prompt>" --output-format text` with:
   - `CLAUDE_CODE_USE_BEDROCK=1` — Use Bedrock as the model provider
   - `ANTHROPIC_MODEL=global.anthropic.claude-sonnet-4-6` — Model selection
   - `--allowedTools Edit Write Bash(*)` — Allow file and command operations
5. **Return output** — The response is printed and the session is stopped

Node.js and Claude Code are cached within the session, so follow-up calls in the same session skip the install step.

## Cleanup

To remove the infrastructure:

```bash
# Delete the Code Interpreter
aws bedrock-agentcore-control delete-code-interpreter \
    --code-interpreter-identifier <code-interpreter-id> \
    --region us-west-2

# Delete the IAM role
aws iam delete-role-policy --role-name CodeInterpreterClaudeCodeRole --policy-name BedrockInvokeAccess
aws iam delete-role --role-name CodeInterpreterClaudeCodeRole
```
