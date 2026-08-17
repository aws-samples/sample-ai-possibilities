#!/bin/bash
set -euo pipefail

# Deploy the unified team using existing AgentCore Memory and Gateway resources.
# This script never creates or updates Gateway, Lambda, or Memory resources.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/_build"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
TEAM_ID="${TEAM_ID:-kasia-rook}"
ALL_AGENTS=("ai-gk" "ai-def" "ai-mid" "ai-fwd1" "ai-fwd2")

export AWS_DEFAULT_REGION TEAM_ID

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [ai-gk|ai-def|ai-mid|ai-fwd1|ai-fwd2]"
  exit 2
fi

if [[ $# -eq 1 ]]; then
  AGENTS=("$1")
else
  AGENTS=("${ALL_AGENTS[@]}")
fi

case " ${ALL_AGENTS[*]} " in
  *" ${AGENTS[0]} "*) ;;
  *) echo "ERROR: Unknown agent '${AGENTS[0]}'."; exit 2 ;;
esac

for command in agentcore aws rsync; do
  command -v "$command" >/dev/null || { echo "ERROR: '$command' is required."; exit 1; }
done

: "${MEMORY_ID:?ERROR: Set MEMORY_ID to the existing AgentCore Memory resource ID.}"
: "${GATEWAY_URL:?ERROR: Set GATEWAY_URL to the existing AgentCore Gateway MCP endpoint.}"

AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
GATEWAY_ID="$(printf '%s' "$GATEWAY_URL" | sed -E 's#^https://([^.]+)\.gateway\.bedrock-agentcore\..*$#\1#')"
if [[ "$GATEWAY_ID" == "$GATEWAY_URL" || -z "$GATEWAY_ID" ]]; then
  echo "ERROR: GATEWAY_URL is not a valid AgentCore Gateway endpoint."
  exit 1
fi

cleanup() {
  rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

printf 'Deploying unified team for %s in %s\n' "$TEAM_ID" "$AWS_DEFAULT_REGION"
printf 'Using Memory %s and Gateway %s\n' "$MEMORY_ID" "$GATEWAY_ID"

DEPLOYED=()
FAILED=()
for agent in "${AGENTS[@]}"; do
  source_dir="$SCRIPT_DIR/$agent"
  stage="$BUILD_DIR/$agent"
  rm -rf "$stage"
  mkdir -p "$stage/src" "$stage/lib"

  cp "$source_dir/src/main.py" "$stage/src/main.py"
  rsync -a --exclude='__pycache__' "$SCRIPT_DIR/../lib/" "$stage/lib/"
  cp "$SCRIPT_DIR/gateway_agent_base.py" "$stage/gateway_agent_base.py"
  cp "$SCRIPT_DIR/gateway_invoke_handler.py" "$stage/gateway_invoke_handler.py"
  cp "$source_dir/requirements.txt" "$stage/requirements.txt"
  sed \
    -e "s|\${AWS_ACCOUNT_ID}|$AWS_ACCOUNT_ID|g" \
    -e "s|\${AWS_DEFAULT_REGION}|$AWS_DEFAULT_REGION|g" \
    "$source_dir/.bedrock_agentcore.yaml.template" > "$stage/.bedrock_agentcore.yaml"

  deploy_envs=(
    --env "MEMORY_ID=$MEMORY_ID"
    --env "GATEWAY_URL=$GATEWAY_URL"
    --env "TEAM_ID=$TEAM_ID"
    --env "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION"
  )
  if [[ -n "${GATEWAY_ACCESS_TOKEN:-}" ]]; then
    deploy_envs+=(--env "GATEWAY_ACCESS_TOKEN=$GATEWAY_ACCESS_TOKEN")
  fi

  if (cd "$stage" && agentcore deploy --auto-update-on-conflict "${deploy_envs[@]}"); then
    DEPLOYED+=("$agent")
  else
    FAILED+=("$agent")
  fi
done

# AgentCore creates runtime roles during deploy. Resource scope is limited to the
# selected existing Memory resource and Gateway instead of all account resources.
policy_document="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"bedrock-agentcore:ListEvents\",\"bedrock-agentcore:CreateEvent\",\"bedrock-agentcore:GetEvent\",\"bedrock-agentcore:DeleteEvent\",\"bedrock-agentcore:RetrieveMemoryRecords\",\"bedrock-agentcore:GetMemoryRecord\",\"bedrock-agentcore:ListMemoryRecords\"],\"Resource\":\"arn:aws:bedrock-agentcore:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:memory/${MEMORY_ID}\"},{\"Effect\":\"Allow\",\"Action\":\"bedrock-agentcore:InvokeGateway\",\"Resource\":\"arn:aws:bedrock-agentcore:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:gateway/${GATEWAY_ID}\"}]}"
roles="$(aws iam list-roles --query "Roles[?starts_with(RoleName, 'AmazonBedrockAgentCoreSDKRuntime-${AWS_DEFAULT_REGION}-')].RoleName" --output text)"
for role in $roles; do
  aws iam put-role-policy --role-name "$role" --policy-name AiTeamUnifiedAccess --policy-document "$policy_document"
done

printf 'Deployed: %s\nFailed: %s\n' "${DEPLOYED[*]:-none}" "${FAILED[*]:-none}"
[[ ${#FAILED[@]} -eq 0 ]]
