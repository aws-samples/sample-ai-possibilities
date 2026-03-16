#!/usr/bin/env python3
"""Create/reuse MCP Gateway and register Lambda targets via boto3.

Usage:
  python3 manage_gateway.py

Outputs (to stdout, one per line):
  GATEWAY_ID=<id>
  GATEWAY_URL=<url>

Env vars required:
  AWS_DEFAULT_REGION (default: us-east-1)
  GATEWAY_ROLE_ARN   — IAM role for the gateway
  LAMBDA_PREFIX      — e.g. afwc-gateway-tool
  AWS_ACCOUNT_ID     — AWS account ID
"""

import os
import sys
import json
import time
import boto3

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
GATEWAY_NAME = os.environ.get("GATEWAY_NAME", "afwc-tactical-tools")
ROLE_ARN = os.environ["GATEWAY_ROLE_ARN"]
ACCOUNT_ID = os.environ["AWS_ACCOUNT_ID"]
LAMBDA_PREFIX = os.environ.get("LAMBDA_PREFIX", "afwc-gateway-tool")

TOOLS = [
    {
        "name": "calculate-pass-options",
        "lambda_suffix": "calculate-pass-options",
        "description": "Calculate pass success probability based on interception risk",
        "schema": [
            {
                "name": "calculate_pass_options",
                "description": "Calculate pass success probability for each teammate",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "game_state": {"type": "object", "description": "Current game state"},
                        "team_id": {"type": "integer", "description": "Team ID (0 or 1)"},
                        "player_id": {"type": "integer", "description": "Player ID (0-4)"},
                    },
                    "required": ["game_state", "team_id", "player_id"],
                },
            }
        ],
    },
    {
        "name": "evaluate-shot",
        "lambda_suffix": "evaluate-shot",
        "description": "Evaluate shot success probability with aim recommendation",
        "schema": [
            {
                "name": "evaluate_shot",
                "description": "Evaluate shot success probability and recommend aim point",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "game_state": {"type": "object", "description": "Current game state"},
                        "team_id": {"type": "integer", "description": "Team ID (0 or 1)"},
                        "player_id": {"type": "integer", "description": "Player ID (0-4)"},
                    },
                    "required": ["game_state", "team_id", "player_id"],
                },
            }
        ],
    },
    {
        "name": "find-open-space",
        "lambda_suffix": "find-open-space",
        "description": "Find open space on the field by zone",
        "schema": [
            {
                "name": "find_open_space",
                "description": "Grid-based open space finder by zone (attack/midfield/defense)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "game_state": {"type": "object", "description": "Current game state"},
                        "team_id": {"type": "integer", "description": "Team ID (0 or 1)"},
                        "zone": {"type": "string", "description": "Zone: attack, midfield, or defense"},
                    },
                    "required": ["game_state", "team_id"],
                },
            }
        ],
    },
    {
        "name": "get-defensive-assignment",
        "lambda_suffix": "get-defensive-assignment",
        "description": "Get opponent threat ranking for marking priority",
        "schema": [
            {
                "name": "get_defensive_assignment",
                "description": "Rank opponent threats for defensive marking priority",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "game_state": {"type": "object", "description": "Current game state"},
                        "team_id": {"type": "integer", "description": "Team ID (0 or 1)"},
                        "player_id": {"type": "integer", "description": "Player ID (0-4)"},
                    },
                    "required": ["game_state", "team_id", "player_id"],
                },
            }
        ],
    },
]

client = boto3.client("bedrock-agentcore-control", region_name=REGION)


def find_existing_gateway():
    """Return gateway dict if it already exists, else None."""
    resp = client.list_gateways()
    for gw in resp.get("items", []):
        if gw.get("name") == GATEWAY_NAME:
            return gw
    return None


def create_gateway():
    """Create MCP gateway with NONE auth."""
    print(f"  Creating MCP Gateway: {GATEWAY_NAME} (NONE auth)", file=sys.stderr)
    resp = client.create_gateway(
        name=GATEWAY_NAME,
        roleArn=ROLE_ARN,
        protocolType="MCP",
        protocolConfiguration={"mcp": {"searchType": "SEMANTIC"}},
        authorizerType="NONE",
    )
    return resp["gatewayId"]


def wait_for_gateway(gateway_id, max_wait=150):
    """Poll until gateway is READY/ACTIVE."""
    for _ in range(max_wait // 5):
        resp = client.get_gateway(gatewayIdentifier=gateway_id)
        status = resp.get("status", "UNKNOWN")
        if status in ("READY", "ACTIVE", "AVAILABLE"):
            print(f"  ✅ Gateway is {status}", file=sys.stderr)
            return True
        print(f"  Status: {status} (waiting...)", file=sys.stderr)
        time.sleep(5)
    print("  ⚠️  Gateway did not become ready in time", file=sys.stderr)
    return False


def register_targets(gateway_id):
    """Register Lambda targets if not already registered."""
    existing = set()
    try:
        resp = client.list_gateway_targets(gatewayIdentifier=gateway_id)
        for t in resp.get("items", []):
            existing.add(t.get("name"))
    except Exception:
        pass

    for tool in TOOLS:
        if tool["name"] in existing:
            print(f"  Already registered: {tool['name']}", file=sys.stderr)
            continue

        lambda_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{LAMBDA_PREFIX}-{tool['lambda_suffix']}"
        print(f"  Registering: {tool['name']} -> {lambda_arn}", file=sys.stderr)
        try:
            client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=tool["name"],
                description=tool["description"],
                targetConfiguration={
                    "mcp": {
                        "lambda": {
                            "lambdaArn": lambda_arn,
                            "toolSchema": {"inlinePayload": tool["schema"]},
                        }
                    }
                },
                credentialProviderConfigurations=[
                    {"credentialProviderType": "GATEWAY_IAM_ROLE"}
                ],
            )
        except client.exceptions.ConflictException:
            print(f"  Already registered (conflict): {tool['name']}", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️  Failed to register {tool['name']}: {e}", file=sys.stderr)


def main():
    gw = find_existing_gateway()
    if gw:
        gateway_id = gw["gatewayId"]
        print(f"  Gateway already exists: {gateway_id}", file=sys.stderr)
    else:
        gateway_id = create_gateway()
        wait_for_gateway(gateway_id)

    gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{REGION}.amazonaws.com/mcp"

    print(f"  Registering targets...", file=sys.stderr)
    register_targets(gateway_id)

    # Output for shell to capture
    print(f"GATEWAY_ID={gateway_id}")
    print(f"GATEWAY_URL={gateway_url}")


if __name__ == "__main__":
    main()
