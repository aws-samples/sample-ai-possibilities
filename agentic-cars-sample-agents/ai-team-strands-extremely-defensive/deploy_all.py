#!/usr/bin/env python3
"""
Deploy all 5 Cars Edition car agents to Bedrock AgentCore.

Usage:
    python deploy_all.py

Works on macOS, Linux, and Windows (PowerShell) without WSL.

Prerequisites:
    npm install -g @aws/agentcore aws-cdk
    uv (https://docs.astral.sh/uv/getting-started/installation/)
    AWS credentials configured (AWS_PROFILE or env vars)
    CDK bootstrap run once per account/region (this script does it automatically)

No Python packages required — only the standard library (AWS identity is
resolved by shelling out to the AWS CLI, which is already a prerequisite).
"""

import json
import os
import stat
import sys
import shutil
import signal
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()
LIB_SRC = SCRIPT_DIR.parent / "lib"
ALL_AGENTS = ["car-goalkeeper", "car-defender", "car-support", "car-striker-1", "car-striker-2"]
agents = ALL_AGENTS

_injected: list[Path] = []


# ── Cleanup ───────────────────────────────────────────────────────────────────

def rmtree(path):
    # On Windows, rmtree fails on read-only files — clear the bit and retry.
    def _onerror(func, p, exc_info):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=_onerror)


def cleanup():
    for agent_dir in _injected:
        lib_copy = agent_dir / "lib"
        if lib_copy.exists():
            rmtree(lib_copy)
    if _injected:
        print("\nCleaned up injected files from agent directories.")


def _signal_handler(sig, frame):
    print("\nInterrupted — cleaning up...")
    cleanup()
    sys.exit(1)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
if hasattr(signal, "SIGBREAK"):  # Windows Ctrl+Break
    signal.signal(signal.SIGBREAK, _signal_handler)


# ── Helpers ───────────────────────────────────────────────────────────────────

def resolve_exe(name):
    # npm-installed CLIs are .cmd shims on Windows; subprocess won't find them
    # without an explicit path. shutil.which honors PATHEXT.
    path = shutil.which(name)
    if path is None:
        print(f"ERROR: '{name}' not found on PATH.")
        sys.exit(1)
    return path


def run(cmd, **kwargs):
    cmd = [resolve_exe(cmd[0]), *cmd[1:]]
    print(f"  > {' '.join(str(c) for c in cmd)}")
    kwargs.setdefault("env", os.environ.copy())
    kwargs["env"].setdefault("PYTHONIOENCODING", "utf-8")
    subprocess.run(cmd, check=True, **kwargs)


def check_tool(name):
    try:
        subprocess.run([resolve_exe(name), "--version"], check=True, capture_output=True)
        print(f"  {name}: OK")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"ERROR: '{name}' not found or not working.")
        sys.exit(1)


def check_agentcore_version(minimum):
    # The AgentCore CLI checks and syncs this project's pinned CDK dependency
    # versions (managed dependency versions, since 0.25.0). Older CLIs skip
    # that entirely and can deploy untested version combinations.
    out = subprocess.run(
        [resolve_exe("agentcore"), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    version = out.split()[-1] if out else ""
    try:
        current = tuple(int(p) for p in version.split("-")[0].split("."))
        required = tuple(int(p) for p in minimum.split("."))
    except ValueError:
        print(f"  agentcore version: {version or 'unknown'} (unparseable, continuing)")
        return
    if current < required:
        print(f"ERROR: agentcore {version} is older than {minimum}.")
        print("  Update it with: npm install -g @aws/agentcore@latest")
        sys.exit(1)
    print(f"  agentcore version: {version}")


def aws_cli(*args):
    """Run the AWS CLI and return its stdout, or None on failure."""
    result = subprocess.run(
        [resolve_exe("aws"), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip() if result.returncode == 0 else None


# ── Pre-flight ────────────────────────────────────────────────────────────────

print("==========================================")
print("  Cars Edition AI Team: Deploy Agents")
print("==========================================\n")
print("Checking prerequisites...")

for tool in ["agentcore", "aws", "node", "cdk", "uv"]:
    check_tool(tool)
check_agentcore_version("0.31.0")

account_id = aws_cli("sts", "get-caller-identity", "--query", "Account", "--output", "text")
if not account_id:
    print("ERROR: Could not resolve AWS account. Check your credentials (aws sts get-caller-identity).")
    sys.exit(1)
region = (
    os.environ.get("AWS_REGION")
    or os.environ.get("AWS_DEFAULT_REGION")
    or aws_cli("configure", "get", "region")
    or "us-east-1"
)
print(f"  AWS Account: {account_id}")
print(f"  AWS Region:  {region}")
print()


# ── Point the AgentCore project at this account/region ───────────────────────

targets_file = SCRIPT_DIR / "agentcore" / "aws-targets.json"
targets = [{"name": "default", "account": account_id, "region": region}]
existing = json.loads(targets_file.read_text(encoding="utf-8")) if targets_file.exists() else []
if existing != targets:
    targets_file.write_text(json.dumps(targets, indent=2) + "\n", encoding="utf-8")
    print(f"  Wrote deploy target to {targets_file.relative_to(SCRIPT_DIR)}\n")

try:
    # ── Install CDK node_modules if needed ───────────────────────────────────

    cdk_dir = SCRIPT_DIR / "agentcore" / "cdk"
    if not (cdk_dir / "node_modules").is_dir():
        print("==========================================")
        print("  Installing CDK dependencies (npm install)")
        print("==========================================")
        run(["npm", "install"], cwd=cdk_dir)
        print()

    # ── CDK bootstrap (idempotent) ────────────────────────────────────────────

    print("==========================================")
    print("  CDK Bootstrap")
    print("==========================================")
    run(["cdk", "bootstrap", f"aws://{account_id}/{region}"])
    print()

    # ── Inject lib/ into each agent dir ──────────────────────────────────────

    for agent in agents:
        agent_dir = SCRIPT_DIR / agent

        if not agent_dir.is_dir():
            print(f"ERROR: Agent directory not found: {agent_dir}")
            sys.exit(1)

        print("==========================================")
        print(f"  Preparing: {agent}")
        print("==========================================")

        lib_dest = agent_dir / "lib"
        if lib_dest.exists():
            rmtree(lib_dest)
        shutil.copytree(
            LIB_SRC,
            lib_dest,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )

        _injected.append(agent_dir)
        print(f"  Ready: {agent_dir}")
        print()

    # ── Deploy all agents in one CDK call ────────────────────────────────────

    print("==========================================")
    print("  Deploying via CDK (agentcore deploy)")
    print("==========================================")
    run(
        ["agentcore", "deploy", "--yes"],
        cwd=SCRIPT_DIR,
        env={**os.environ, "AWS_DEFAULT_REGION": region},
    )

except subprocess.CalledProcessError:
    print("\nDeployment failed. Check the output above.")
    cleanup()
    sys.exit(1)

except Exception as e:
    print(f"\nUnexpected error: {e}")
    cleanup()
    sys.exit(1)

else:
    cleanup()

# ── Summary ───────────────────────────────────────────────────────────────────

print()
print("==========================================")
print("  Deployment Summary")
print("==========================================")
print(f"  Agents:   {', '.join(agents)}")
print(f"  Account:  {account_id}")
print(f"  Region:   {region}")
print()
print("All agents deployed successfully.")
