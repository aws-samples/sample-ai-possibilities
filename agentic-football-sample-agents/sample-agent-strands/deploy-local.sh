#!/bin/bash
set -e

# ============================================================================
# Deploy Sample Agent to Bedrock AgentCore - Local Deployment
# ============================================================================
#
# Usage:
#   # Using default AWS profile:
#   ./deploy-local.sh
#
#   # Using a specific AWS profile (e.g. sandbox account for multi-account testing):
#   AWS_PROFILE=sandbox ./deploy-local.sh
#
#   # Override region:
#   AWS_DEFAULT_REGION=us-west-2 ./deploy-local.sh
#
# Prerequisites:
#   pip install bedrock-agentcore-starter-toolkit
#   aws configure  (or set AWS_PROFILE)
#
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Defaults - override via env vars
PROJECT_NAME="${PROJECT_NAME:-afwc}"
ENV_NAME="${ENV_NAME:-dev}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_DEFAULT_REGION

echo "=========================================="
echo "  Sample Agent - Local Deployment"
echo "=========================================="
echo ""

# ------ Pre-flight checks ------

echo "Checking prerequisites..."

if ! command -v agentcore &> /dev/null; then
  echo "ERROR: 'agentcore' CLI not found."
  echo "Install it with: pip install bedrock-agentcore-starter-toolkit"
  exit 1
fi
echo "  agentcore CLI: OK"

if ! command -v aws &> /dev/null; then
  echo "ERROR: 'aws' CLI not found."
  exit 1
fi
echo "  aws CLI: OK"

# Verify AWS credentials
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
  echo "ERROR: No valid AWS credentials. Run 'aws configure' or set AWS_PROFILE."
  exit 1
}
export AWS_ACCOUNT_ID
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  AWS Region:  $AWS_DEFAULT_REGION"
echo "  AWS Profile: ${AWS_PROFILE:-default}"
echo ""

# ------ Generate config from template ------

echo "Generating .bedrock_agentcore.yaml from template..."

if ! command -v envsubst &> /dev/null; then
  # macOS doesn't have envsubst by default - do simple sed replacement
  sed \
    -e "s|\${AWS_ACCOUNT_ID}|$AWS_ACCOUNT_ID|g" \
    -e "s|\${AWS_DEFAULT_REGION}|$AWS_DEFAULT_REGION|g" \
    .bedrock_agentcore.yaml.template > .bedrock_agentcore.yaml
else
  envsubst < .bedrock_agentcore.yaml.template > .bedrock_agentcore.yaml
fi

echo "  Generated .bedrock_agentcore.yaml"
echo ""

# ------ Deploy ------

echo "Deploying sample-agent-strands to AgentCore..."
echo ""
agentcore deploy --auto-update-on-conflict
echo ""

# ------ Verify ------

echo "Verifying deployment..."
agentcore status
echo ""

# ------ Extract ARN and optionally store in SSM ------

AGENT_RUNTIME_ID=$(agentcore status | grep -o 'runtime/[^[:space:]]*' | head -1 | sed 's|runtime/||' | sed 's|/.*||')

if [ -z "$AGENT_RUNTIME_ID" ]; then
  echo "WARNING: Could not extract agent runtime ID from agentcore status output."
  echo "Check the output above for the runtime ID."
  exit 0
fi

AGENT_ARN="arn:aws:bedrock-agentcore:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:runtime/${AGENT_RUNTIME_ID}"

echo "=========================================="
echo "  Deployment Complete"
echo "=========================================="
echo ""
echo "  Agent Runtime ID: $AGENT_RUNTIME_ID"
echo "  Agent ARN:        $AGENT_ARN"
echo "  Account:          $AWS_ACCOUNT_ID"
echo "  Region:           $AWS_DEFAULT_REGION"
echo ""

echo ""
echo "Next steps:"
echo "  1. Register this agent in the portal (POST /agents with the ARN above)"
echo "  2. Or use the test-match-flow.sh script to run a full integration test"
echo ""
