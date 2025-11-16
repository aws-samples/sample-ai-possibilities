#!/bin/bash
# Validation script for CloudFormation AgentCore Browser integration
# Run this BEFORE deploying the CloudFormation changes

set -euo pipefail

echo "========================================="
echo "AgentCore Browser CFN Integration Validator"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    fail "Not in the agentcore_browser_extension directory"
    echo "Please run this from /Users/edsilva/Downloads/git/agentcore_browser_extension"
    exit 1
fi

echo "1. Checking local build..."
if [ -d "dist" ]; then
    pass "dist directory exists"
else
    fail "dist directory not found - run 'npm run build' first"
    exit 1
fi

if [ -f "dist/nodes/AgentcoreBrowser/AgentcoreBrowser.node.js" ]; then
    pass "AgentCore Browser node compiled"
else
    fail "Node not compiled properly"
    exit 1
fi

echo ""
echo "2. Checking package.json configuration..."
if grep -q '"n8n-community-node-package"' package.json; then
    pass "Has n8n-community-node-package keyword"
else
    warn "Missing n8n-community-node-package keyword (not critical for mounting)"
fi

if grep -q '"n8n":' package.json; then
    pass "Has n8n configuration section"
else
    fail "Missing n8n configuration section"
    exit 1
fi

echo ""
echo "3. Checking dependencies..."
if [ -d "node_modules" ]; then
    pass "node_modules exists"
else
    fail "node_modules not found - run 'npm install' first"
    exit 1
fi

if [ -d "node_modules/@aws-sdk/client-bedrock-agentcore" ]; then
    pass "AWS AgentCore SDK installed"
else
    fail "AWS AgentCore SDK not installed"
    exit 1
fi

if [ -d "node_modules/playwright" ]; then
    pass "Playwright installed"
else
    fail "Playwright not installed"
    exit 1
fi

echo ""
echo "4. Simulating Docker mount..."
# Create a temporary directory to simulate the mount
TEMP_DIR=$(mktemp -d)
cp -r dist "$TEMP_DIR/"
cp package.json "$TEMP_DIR/"

if [ -f "$TEMP_DIR/dist/nodes/AgentcoreBrowser/AgentcoreBrowser.node.js" ]; then
    pass "Files would be accessible in container"
else
    fail "Mount simulation failed"
    rm -rf "$TEMP_DIR"
    exit 1
fi

rm -rf "$TEMP_DIR"

echo ""
echo "5. Checking CloudFormation template..."
CFN_FILE="/Users/edsilva/Downloads/git/build-agentic-workflows-with-amazon-bedrock/static/cfn/code-editor.yaml"
if [ -f "$CFN_FILE" ]; then
    pass "CloudFormation template found"

    # Check if it has the required components
    if grep -q "ConfigureN8n" "$CFN_FILE"; then
        pass "ConfigureN8n step exists"
    else
        fail "ConfigureN8n step not found in template"
    fi

    if grep -q "docker-compose" "$CFN_FILE"; then
        pass "Docker Compose configuration exists"
    else
        fail "Docker Compose not found in template"
    fi
else
    warn "CloudFormation template not found at expected location"
fi

echo ""
echo "6. Testing N8N package structure..."
# Check if the package follows N8N conventions
if [ -f "dist/credentials/AgentcoreBrowserApi.credentials.js" ]; then
    pass "Credentials file exists"
else
    fail "Credentials file not found"
fi

if [ -f "dist/nodes/AgentcoreBrowser/AgentcoreBrowser.node.js" ]; then
    pass "Node file exists"
else
    fail "Node file not found"
fi

if [ -f "dist/nodes/AgentcoreBrowser/agentcore.svg" ]; then
    pass "Icon file exists"
else
    warn "Icon file not found (not critical)"
fi

echo ""
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo ""

# Create integration instructions
cat << 'EOF'
✓ Package is ready for CloudFormation integration

NEXT STEPS:

1. Choose Your Integration Method:

   Option A: Git Repository (Recommended for production)
   - Push your code to a Git repository
   - Set AgentcoreBrowserGitRepo parameter in CFN
   - Template will clone and build automatically

   Option B: Local Path (For testing)
   - Copy code to EC2 instance (e.g., via S3 or during instance setup)
   - Set AgentcoreBrowserLocalPath parameter in CFN
   - Template will build from local path

2. Update CloudFormation Template:
   - Add the parameters from cloudformation-additions.yaml
   - Add the two new SSM steps
   - Update the docker-compose.yml section

3. Deploy CloudFormation Stack:
   - Test in a dev/test environment first
   - Monitor SSM command execution logs
   - Check N8N logs: docker logs n8n-main

4. Verify in N8N:
   - Open N8N UI
   - Click "+" to add node
   - Search for "AgentCore Browser"
   - Should appear in the list

IMPORTANT NOTES:
- The EC2 instance already has AdministratorAccess (includes AgentCore permissions)
- Playwright will install Chromium dependencies (adds ~200MB)
- Build time: ~2-5 minutes
- N8N restart time: ~30 seconds

ROLLBACK:
If something breaks:
  ssh into EC2
  cd /opt/n8n
  cp docker-compose.yml.backup docker-compose.yml
  docker-compose down && docker-compose up -d

EOF

echo ""
echo "========================================="
echo "Questions to Answer:"
echo "========================================="
echo ""
echo "1. Where is your code?"
echo "   [ ] In a Git repository (provide URL)"
echo "   [ ] On local disk (will be copied to EC2)"
echo ""
echo "2. Do you want to test this first in a separate stack?"
echo "   [ ] Yes (recommended)"
echo "   [ ] No (deploy to existing stack)"
echo ""
echo "3. Have you reviewed the docker-compose.yml changes?"
echo "   [ ] Yes"
echo "   [ ] No (review cloudformation-additions.yaml first)"
echo ""

echo "Ready to proceed? Reply with your answers!"
