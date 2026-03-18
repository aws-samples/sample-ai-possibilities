#!/bin/bash
set -e

# ============================================================================
# Deploy all 5 AI Team (Memory) agents to Bedrock AgentCore
# ============================================================================
#
# Usage:
#   AWS_PROFILE=your-profile MEMORY_ID=xxx ./deploy-all.sh          # deploy all
#   AWS_PROFILE=your-profile MEMORY_ID=xxx ./deploy-all.sh ai-gk    # deploy one
#
# Requires MEMORY_ID env var (create via: python3 create_memory.py)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/_build"

AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_DEFAULT_REGION

ALL_AGENTS=("ai-gk" "ai-def" "ai-mid" "ai-fwd1" "ai-fwd2")

if [ -n "$1" ]; then
  AGENTS=("$1")
else
  AGENTS=("${ALL_AGENTS[@]}")
fi

echo "=========================================="
echo "  AI Team (Memory) — Deploy Agents"
echo "=========================================="
echo ""

# ------ Pre-flight ------
echo "Checking prerequisites..."

if [ -z "$MEMORY_ID" ]; then
  echo "  MEMORY_ID not set — creating memory resource automatically..."
  set +e
  CREATE_OUTPUT=$(python3 "$SCRIPT_DIR/create_memory.py" 2>&1)
  CREATE_EXIT=$?
  set -e
  echo "  create_memory.py output:"
  echo "  $CREATE_OUTPUT"
  if [ $CREATE_EXIT -ne 0 ]; then
    echo "ERROR: create_memory.py failed (exit code $CREATE_EXIT)."
    exit 1
  fi
  MEMORY_ID=$(echo "$CREATE_OUTPUT" | sed -n 's/.*export MEMORY_ID=\([^ ]*\).*/\1/p')
  if [ -z "$MEMORY_ID" ]; then
    # Try alternate format: "Memory resource ready: <id>"
    MEMORY_ID=$(echo "$CREATE_OUTPUT" | sed -n 's/.*Memory resource ready: \([^ ]*\).*/\1/p')
  fi
  if [ -z "$MEMORY_ID" ]; then
    echo "ERROR: Could not parse MEMORY_ID from output."
    exit 1
  fi
  export MEMORY_ID
  echo "  Created MEMORY_ID: $MEMORY_ID"
else
  echo "  MEMORY_ID: $MEMORY_ID (from env)"
fi

if ! command -v agentcore &> /dev/null; then
  echo "ERROR: 'agentcore' CLI not found."
  echo "Install: pip install bedrock-agentcore-starter-toolkit"
  exit 1
fi
echo "  agentcore CLI: OK"

if ! command -v aws &> /dev/null; then
  echo "ERROR: 'aws' CLI not found."
  exit 1
fi
echo "  aws CLI: OK"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
  echo "ERROR: No valid AWS credentials."
  exit 1
}
export AWS_ACCOUNT_ID
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  AWS Region:  $AWS_DEFAULT_REGION"
echo ""

# ------ Cleanup on exit ------
cleanup() {
  echo ""
  echo "Cleaning up build directory..."
  rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

# ------ Build & deploy each agent ------
DEPLOYED=()
FAILED=()

for agent in "${AGENTS[@]}"; do
  AGENT_SRC="$SCRIPT_DIR/$agent"
  STAGE="$BUILD_DIR/$agent"

  echo "=========================================="
  echo "  Deploying: $agent"
  echo "=========================================="

  if [ ! -d "$AGENT_SRC" ]; then
    echo "  ERROR: Agent directory not found: $AGENT_SRC"
    FAILED+=("$agent")
    continue
  fi

  rm -rf "$STAGE"
  mkdir -p "$STAGE/src"

  # Copy agent source
  cp "$AGENT_SRC/src/main.py" "$STAGE/src/main.py"

  # Copy shared lib (required: main.py imports _bootstrap, agent_base, fallback, etc.)
  # Try ../lib (full repo layout) then ./lib (team-only layout)
  if [ -d "$SCRIPT_DIR/../lib" ]; then
    LIB_SRC="$SCRIPT_DIR/../lib"
  elif [ -d "$SCRIPT_DIR/lib" ]; then
    LIB_SRC="$SCRIPT_DIR/lib"
  else
    echo "  ERROR: Shared lib not found. Copy lib/ into this directory:"
    echo "  cp -r <path-to>/lib $SCRIPT_DIR/lib"
    FAILED+=("$agent")
    continue
  fi
  mkdir -p "$STAGE/lib"
  cp "$LIB_SRC"/*.py "$STAGE/lib/"
  find "$STAGE/lib" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

  # Copy memory_agent_base.py (team-level shared module)
  cp "$SCRIPT_DIR/memory_agent_base.py" "$STAGE/memory_agent_base.py"

  # Copy requirements.txt
  cp "$AGENT_SRC/requirements.txt" "$STAGE/requirements.txt"

  # Generate .bedrock_agentcore.yaml from template
  sed \
    -e "s|\${AWS_ACCOUNT_ID}|$AWS_ACCOUNT_ID|g" \
    -e "s|\${AWS_DEFAULT_REGION}|$AWS_DEFAULT_REGION|g" \
    "$AGENT_SRC/.bedrock_agentcore.yaml.template" > "$STAGE/.bedrock_agentcore.yaml"

  echo "  Deploying from: $STAGE"
  if (cd "$STAGE" && agentcore deploy --auto-update-on-conflict \
    --env "MEMORY_ID=$MEMORY_ID" \
    --env "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION"); then
    echo "  ✅ $agent: DEPLOYED"
    DEPLOYED+=("$agent")
  else
    echo "  ❌ $agent: FAILED"
    FAILED+=("$agent")
  fi
  echo ""
done

# ------ Attach memory permissions to execution roles ------
echo "Attaching AgentCore Memory permissions to execution roles..."
set +e
EXEC_ROLES=$(aws iam list-roles \
  --query "Roles[?starts_with(RoleName, 'AmazonBedrockAgentCoreSDKRuntime-${AWS_DEFAULT_REGION}-')].RoleName" \
  --output text 2>/dev/null)
set -e

if [ -n "$EXEC_ROLES" ]; then
  for EXEC_ROLE_NAME in $EXEC_ROLES; do
    aws iam put-role-policy \
      --role-name "$EXEC_ROLE_NAME" \
      --policy-name AgentCoreMemoryAccess \
      --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
          \"Effect\": \"Allow\",
          \"Action\": [
            \"bedrock-agentcore:ListEvents\",
            \"bedrock-agentcore:CreateEvent\",
            \"bedrock-agentcore:GetEvent\",
            \"bedrock-agentcore:DeleteEvent\",
            \"bedrock-agentcore:RetrieveMemoryRecords\",
            \"bedrock-agentcore:GetMemoryRecord\",
            \"bedrock-agentcore:ListMemoryRecords\"
          ],
          \"Resource\": \"arn:aws:bedrock-agentcore:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:memory/*\"
        }]
      }" 2>/dev/null && echo "  ✅ Memory permissions attached to: $EXEC_ROLE_NAME" \
      || echo "  ⚠️  Failed to attach memory permissions to: $EXEC_ROLE_NAME"
  done
else
  echo "  ⚠️  Could not find execution roles — attach AgentCoreMemoryAccess policy manually"
fi
echo ""

# ------ Summary ------
echo "=========================================="
echo "  Deployment Summary"
echo "=========================================="
echo ""
echo "  Deployed: ${DEPLOYED[*]:-none}"
echo "  Failed:   ${FAILED[*]:-none}"
echo "  Account:  $AWS_ACCOUNT_ID"
echo "  Region:   $AWS_DEFAULT_REGION"
echo "  Memory:   $MEMORY_ID"
echo ""

if [ ${#FAILED[@]} -gt 0 ]; then
  echo "Some agents failed to deploy. Check the output above."
  exit 1
fi

echo "All agents deployed successfully."
