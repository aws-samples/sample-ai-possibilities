"""
Step 2: Run Claude Code inside an AgentCore Code Interpreter sandbox.

This script:
  1. Starts a session on your custom Code Interpreter (PUBLIC network)
  2. Downloads and installs Node.js + Claude Code inside the sandbox
  3. Runs `claude -p "<prompt>"` in headless mode via Bedrock
  4. Returns the output

The sandbox gets IAM credentials from the execution role (no keys needed).
Claude Code calls Bedrock using those credentials automatically.

Usage:
    python run.py <code-interpreter-id> "Your prompt here"

Examples:
    python run.py claudeCodePublic-abc123 "Write a Python fibonacci function"
    python run.py claudeCodePublic-abc123 "Explain what quicksort does"

Prerequisites:
    - Run setup_infrastructure.py first (one-time)
    - AWS credentials configured with AgentCore access
"""

import boto3
import sys
from botocore.config import Config

# --- Configuration ---
REGION = "us-west-2"
MODEL_ID = "global.anthropic.claude-sonnet-4-6"

# Longer timeout — Claude Code may take a while on complex prompts
BOTO_CONFIG = Config(read_timeout=600, connect_timeout=10)

# Node.js version to install in the sandbox
NODE_VERSION = "v22.16.0"

# --- Setup code that runs inside the sandbox ---
INSTALL_CODE = f"""
import subprocess, os, urllib.request, tarfile, platform

NODE_VERSION = '{NODE_VERSION}'
INSTALL_DIR = '/tmp/claude-code'
NODE_DIR = f'{{INSTALL_DIR}}/node'
arch = 'arm64' if platform.machine() == 'aarch64' else 'x64'

os.makedirs(INSTALL_DIR, exist_ok=True)

# Download and install Node.js (if not already cached in this session)
if not os.path.exists(f'{{NODE_DIR}}/bin/node'):
    url = f'https://nodejs.org/dist/{{NODE_VERSION}}/node-{{NODE_VERSION}}-linux-{{arch}}.tar.gz'
    print(f'Downloading Node.js {{NODE_VERSION}}...')
    urllib.request.urlretrieve(url, '/tmp/node.tar.gz')

    os.makedirs(NODE_DIR, exist_ok=True)
    print('Extracting...')
    with tarfile.open('/tmp/node.tar.gz', 'r:gz') as tar:
        tar.extractall('/tmp/node-extract', filter='data')

    extracted = f'/tmp/node-extract/node-{{NODE_VERSION}}-linux-{{arch}}'
    subprocess.run(f'cp -r {{extracted}}/* {{NODE_DIR}}/', shell=True, check=True)
    os.remove('/tmp/node.tar.gz')
    print(f'Node.js installed')
else:
    print('Node.js already cached')

# Install Claude Code via npm (if not already cached)
claude_cli = f'{{NODE_DIR}}/lib/node_modules/@anthropic-ai/claude-code/cli.js'
if not os.path.exists(claude_cli):
    env = os.environ.copy()
    env['PATH'] = f'{{NODE_DIR}}/bin:' + env.get('PATH', '')
    env['HOME'] = '/tmp/claude-home'
    os.makedirs('/tmp/claude-home', exist_ok=True)

    print('Installing Claude Code...')
    r = subprocess.run(
        [f'{{NODE_DIR}}/bin/npm', 'install', '-g', '@anthropic-ai/claude-code'],
        capture_output=True, text=True, env=env, timeout=120
    )
    if r.returncode != 0:
        print(f'ERROR: {{r.stderr[-500:]}}')
    else:
        print('Claude Code installed')
else:
    print('Claude Code already cached')

# Verify
r = subprocess.run(
    [f'{{NODE_DIR}}/bin/node', claude_cli, '--version'],
    capture_output=True, text=True,
    env={{**os.environ, 'HOME': '/tmp/claude-home'}},
    timeout=15
)
print(f'Version: {{r.stdout.strip()}}')
"""


def make_run_code(prompt: str) -> str:
    """Generate the Python code to run Claude Code with the given prompt."""
    return f"""
import subprocess, os

NODE_DIR = '/tmp/claude-code/node'
CLAUDE_CLI = f'{{NODE_DIR}}/lib/node_modules/@anthropic-ai/claude-code/cli.js'

env = os.environ.copy()
env['PATH'] = f'{{NODE_DIR}}/bin:' + env.get('PATH', '')
env['HOME'] = '/tmp/claude-home'
env['CLAUDE_CODE_USE_BEDROCK'] = '1'
env['ANTHROPIC_MODEL'] = '{MODEL_ID}'
env['AWS_REGION'] = '{REGION}'

os.makedirs('/tmp/workspace', exist_ok=True)

result = subprocess.run(
    [f'{{NODE_DIR}}/bin/node', CLAUDE_CLI,
     '-p', {repr(prompt)},
     '--output-format', 'text',
     '--allowedTools', 'Edit', 'Write', 'Bash(*)'],
    capture_output=True, text=True,
    env=env,
    cwd='/tmp/workspace',
    timeout=300
)

if result.stdout:
    print(result.stdout)
if result.returncode != 0 and result.stderr:
    for line in result.stderr.splitlines():
        if any(skip in line.lower() for skip in [
            'experimentalwarning', 'deprecated', 'punycode'
        ]):
            continue
        if line.strip():
            print('STDERR:', line)
"""


def execute_code(agentcore, ci_id: str, session_id: str, code: str) -> str:
    """Run Python code in the sandbox and return output."""
    response = agentcore.invoke_code_interpreter(
        codeInterpreterIdentifier=ci_id,
        sessionId=session_id,
        name="executeCode",
        arguments={"language": "python", "code": code},
    )
    parts = []
    for event in response["stream"]:
        if "result" in event:
            for item in event["result"].get("content", []):
                if item["type"] == "text":
                    parts.append(item["text"])
    return "\n".join(parts)


def main():
    if len(sys.argv) < 3:
        print("Usage: python run.py <code-interpreter-id> \"<prompt>\"")
        print('Example: python run.py claudeCodePublic-abc123 "Write hello world"')
        sys.exit(1)

    ci_id = sys.argv[1]
    prompt = sys.argv[2]

    agentcore = boto3.client(
        "bedrock-agentcore", region_name=REGION, config=BOTO_CONFIG
    )

    # Start session
    session = agentcore.start_code_interpreter_session(
        codeInterpreterIdentifier=ci_id,
        name="claude_code_session",
        sessionTimeoutSeconds=1800,
    )
    session_id = session["sessionId"]
    print(f"Session: {session_id}\n")

    try:
        # Install Node.js + Claude Code (cached within session)
        print("--- Setup ---")
        setup_output = execute_code(agentcore, ci_id, session_id, INSTALL_CODE)
        print(setup_output)

        # Run Claude Code
        print(f"\n--- Claude Code: {prompt} ---")
        run_output = execute_code(
            agentcore, ci_id, session_id, make_run_code(prompt)
        )
        print(run_output)

    finally:
        agentcore.stop_code_interpreter_session(
            codeInterpreterIdentifier=ci_id,
            sessionId=session_id,
        )
        print(f"\n--- Session stopped: {session_id} ---")


if __name__ == "__main__":
    main()
