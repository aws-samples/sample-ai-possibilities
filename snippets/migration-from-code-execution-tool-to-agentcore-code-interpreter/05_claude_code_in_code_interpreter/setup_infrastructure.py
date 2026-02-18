"""
Step 1 (one-time): Create the infrastructure for Claude Code in Code Interpreter.

This script creates:
  1. An IAM execution role with Bedrock invoke permissions
  2. A custom Code Interpreter with PUBLIC network mode

The custom Code Interpreter gives the sandbox:
  - Public internet access (to download Node.js and Claude Code)
  - IAM role credentials (to call Bedrock from inside the sandbox)

Run this ONCE:
    python setup_infrastructure.py

Requirements:
    pip install boto3

Usage:
    python setup_infrastructure.py
"""

import boto3
import json
import time

# --- Configuration ---
REGION = "us-west-2"
ROLE_NAME = "CodeInterpreterClaudeCodeRole"
CODE_INTERPRETER_NAME = "claudeCodePublic"

# --- IAM Trust Policy ---
# The Code Interpreter service assumes this role inside the sandbox
TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "bedrock-agentcore.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}

# --- IAM Permissions Policy ---
# Claude Code needs to invoke Bedrock models
PERMISSIONS_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream"
        ],
        "Resource": "*"
    }]
}


def create_role(iam) -> str:
    """Create the IAM execution role for the Code Interpreter."""
    try:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
            Description="Execution role for Code Interpreter - allows Bedrock invoke"
        )
        role_arn = role["Role"]["Arn"]
        print(f"Created IAM role: {role_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=ROLE_NAME)
        role_arn = role["Role"]["Arn"]
        print(f"IAM role already exists: {role_arn}")

    # Attach Bedrock permissions
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="BedrockInvokeAccess",
        PolicyDocument=json.dumps(PERMISSIONS_POLICY)
    )
    print("  Attached Bedrock invoke permissions")

    return role_arn


def create_code_interpreter(cp_client, role_arn: str) -> str:
    """Create a custom Code Interpreter with PUBLIC network mode."""
    # Check if it already exists
    existing = cp_client.list_code_interpreters()
    for ci in existing.get("codeInterpreters", []):
        if ci.get("name", "").startswith(CODE_INTERPRETER_NAME):
            ci_id = ci["codeInterpreterId"]
            print(f"Code Interpreter already exists: {ci_id}")
            return ci_id

    # Wait for IAM role propagation
    print("Waiting 10s for IAM role propagation...")
    time.sleep(10)

    response = cp_client.create_code_interpreter(
        name=CODE_INTERPRETER_NAME,
        description="Code Interpreter with public network for running Claude Code via Bedrock",
        executionRoleArn=role_arn,
        networkConfiguration={
            "networkMode": "PUBLIC"
        }
    )

    ci_id = response["codeInterpreterId"]
    print(f"Created Code Interpreter: {ci_id}")
    print(f"  Network mode: PUBLIC")
    print(f"  Execution role: {role_arn}")

    return ci_id


def main():
    iam = boto3.client("iam")
    cp_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    print("=== Setting up infrastructure ===\n")

    # Step 1: Create IAM role
    role_arn = create_role(iam)

    # Step 2: Create custom Code Interpreter
    ci_id = create_code_interpreter(cp_client, role_arn)

    print(f"\n=== Setup complete ===")
    print(f"Code Interpreter ID: {ci_id}")
    print(f"\nYou can now run:")
    print(f'  python run.py "{ci_id}" "Your prompt here"')


if __name__ == "__main__":
    main()
