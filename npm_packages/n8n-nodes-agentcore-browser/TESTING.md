# Testing Guide

This guide explains how to test the AgentCore Browser node before publishing.

## Prerequisites

1. **Self-hosted N8N instance** (N8N Cloud doesn't support unverified community nodes)
2. **AWS Account** with AgentCore Browser access
3. **Node.js 18+** and npm installed

## Quick Setup for Testing

### Option 1: Docker N8N (Easiest)

1. **Start N8N with Docker:**
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

2. **In another terminal, install the node:**
```bash
# Navigate to the project directory
cd /Users/edsilva/Downloads/git/agentcore_browser_extension

# Install dependencies
npm install

# Build
npm run build

# Install into Docker container
docker exec n8n npm install -g /path/to/agentcore_browser_extension

# Restart N8N
docker restart n8n
```

3. **Access N8N:**
Open http://localhost:5678

### Option 2: Local N8N Installation

1. **Install N8N globally (if not already installed):**
```bash
npm install -g n8n
```

2. **Navigate to project and install dependencies:**
```bash
cd /Users/edsilva/Downloads/git/agentcore_browser_extension
npm install
```

3. **Build the project:**
```bash
npm run build
```

4. **Link the package:**
```bash
# In the project directory
npm link

# Find your N8N installation
which n8n
# Usually: /usr/local/lib/node_modules/n8n

# Link in the N8N directory
cd /usr/local/lib/node_modules/n8n
npm link n8n-nodes-agentcore-browser
```

5. **Start N8N:**
```bash
n8n start
```

6. **Access N8N:**
Open http://localhost:5678

### Option 3: N8N Desktop App

If you use the N8N Desktop app, you'll need to:
1. Find the app's installation directory
2. Install the node package there
3. Restart the app

**Note:** This is more complex and Option 1 or 2 is recommended.

## Verifying Installation

1. Open N8N at http://localhost:5678
2. Create a new workflow
3. Click the **+** button to add a node
4. Search for "AgentCore Browser"
5. The node should appear with the AWS/AgentCore icon

If you don't see it:
- Check build succeeded: `ls dist/` should show compiled files
- Check N8N logs for errors
- Restart N8N completely
- Try unlinking and relinking: `npm unlink && npm link`

## Testing the Node

### Test 1: Basic Credential Setup

1. Add AgentCore Browser node to workflow
2. Click on credential dropdown
3. Click "Create New"
4. Fill in AWS credentials:
   - Region: `us-east-1`
   - Access Key ID: Your AWS access key
   - Secret Access Key: Your AWS secret
5. Save credentials

**Expected:** No errors, credentials saved successfully

### Test 2: Simple Navigate & Extract

1. Add Manual Trigger node
2. Add AgentCore Browser node
3. Configure:
   - Operation: Navigate and Extract
   - Start URL: `https://example.com`
   - Selector: `h1`
   - Extract Mode: Text Content
4. Click "Execute Node"

**Expected:**
- Execution succeeds
- Output contains extracted h1 text
- Session info with browserId and sessionId

**Common Issues:**
- **Timeout**: Increase timeout in node settings
- **Connection error**: Verify AWS credentials and permissions
- **Selector not found**: Check the selector exists on the page

### Test 3: Navigate & Extract with Actions

1. Add AgentCore Browser node
2. Configure:
   - Operation: Navigate and Extract
   - Start URL: `https://www.google.com`
   - Add Actions:
     - Type Text → Selector: `[name="q"]`, Value: `n8n`
     - Press Key → Selector: `[name="q"]`, Value: `Enter`
     - Wait → Value: `2000`
   - Wait for Selector: `#search`
   - Selector: `.g h3`
   - Extract Mode: Text
3. Execute

**Expected:**
- Search executes
- Results extracted
- Array of search result titles returned

### Test 4: Custom Script

1. Add AgentCore Browser node
2. Configure:
   - Operation: Run Script
   - Start URL: `https://example.com`
   - Script:
   ```javascript
   await page.waitForLoadState('networkidle');
   const title = await page.title();
   const url = page.url();
   return { title, url };
   ```
3. Execute

**Expected:**
- Script runs successfully
- Returns object with title and url
- No errors in execution

### Test 5: Screenshot Capture

1. Add AgentCore Browser node
2. Configure:
   - Operation: Navigate and Extract
   - Start URL: `https://example.com`
   - Selector: `h1`
   - Take Screenshot: Yes
3. Execute

**Expected:**
- Execution succeeds
- Binary data contains screenshot
- Can download/view the screenshot image

### Test 6: Error Handling

1. Add AgentCore Browser node
2. Configure with invalid selector:
   - Start URL: `https://example.com`
   - Selector: `.this-selector-does-not-exist-12345`
   - Wait for Selector: `.this-selector-does-not-exist-12345`
3. Execute

**Expected:**
- Node fails gracefully
- Error message is descriptive
- No hanging connections

## Testing AWS Integration

### Verify AWS Setup

Before testing the node, verify AWS AgentCore is accessible:

```bash
# Test AWS credentials
aws sts get-caller-identity

# List browser tools
aws bedrock-agent list-browser-tools --region us-east-1

# Verify default browser tool exists
aws bedrock-agent get-browser-tool \
  --browser-tool-id aws.browser.v1 \
  --region us-east-1
```

**Expected Output:**
- Your AWS account and user info
- List of available browser tools
- Details of the default browser tool

### Common AWS Issues

**"Access Denied":**
- Verify IAM permissions include:
  - `bedrock-agentcore:ListBrowserTools`
  - `bedrock-agentcore:GetBrowserTool`
  - `bedrock-agent-runtime:InvokeAgent`

**"Region not supported":**
- AgentCore Browser is only available in specific regions
- Use `us-east-1` for testing

**"Browser tool not found":**
- AgentCore Browser might not be enabled in your account
- Contact AWS support to enable AgentCore

## Development Workflow

### Making Changes

1. Edit TypeScript files in `nodes/`, `credentials/`, or `utils/`
2. Rebuild: `npm run build`
3. Restart N8N
4. Test changes in workflow
5. Check N8N logs for errors: `~/.n8n/logs/`

### Debug Mode

Enable N8N debug logs:
```bash
export N8N_LOG_LEVEL=debug
n8n start
```

Check logs at: `~/.n8n/logs/`

### Common Development Issues

**"Changes not showing up":**
- Run `npm run build` after every change
- Restart N8N completely
- Clear N8N cache: `rm -rf ~/.n8n/cache`

**"Module not found":**
- Run `npm install` to ensure dependencies are installed
- Check imports in TypeScript files
- Verify package.json dependencies

**"Type errors":**
- Check TypeScript configuration: `npx tsc --noEmit`
- Fix errors shown in output
- Rebuild: `npm run build`

## Performance Testing

### Test Session Cleanup

1. Execute workflow with AgentCore Browser node
2. Check AWS CloudWatch logs
3. Verify browser sessions are closed properly
4. No lingering sessions after execution

### Test Parallel Execution

1. Create workflow with multiple items
2. Each item should create its own browser session
3. Verify all sessions complete successfully
4. Check execution times

### Test Long-Running Scripts

1. Create script with multiple page navigations
2. Set timeout to 120000 (2 minutes)
3. Execute and verify completion
4. Check for memory leaks or hanging connections

## Pre-Publishing Checklist

Before publishing to npm:

- [ ] All tests pass
- [ ] No TypeScript errors: `npm run build`
- [ ] No lint errors: `npm run lint`
- [ ] Documentation is complete
- [ ] Examples work correctly
- [ ] Screenshots load properly
- [ ] Error handling is robust
- [ ] Session cleanup happens on errors
- [ ] README has correct package name and URLs
- [ ] package.json version is correct
- [ ] LICENSE file exists

## Troubleshooting

### N8N Not Starting

```bash
# Check N8N logs
tail -f ~/.n8n/logs/n8n.log

# Try starting with debug output
N8N_LOG_LEVEL=debug n8n start
```

### Node Not Appearing

```bash
# Verify package is linked
npm list -g n8n-nodes-agentcore-browser

# Check N8N's node_modules
ls node_modules/ | grep agentcore

# Rebuild and restart
npm run build
pkill -f n8n
n8n start
```

### AWS Connection Issues

```bash
# Test AWS credentials
aws configure list

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Check AgentCore Browser availability
aws bedrock-agent list-browser-tools --region us-east-1
```

## Next Steps

Once all tests pass:
1. Update version in package.json
2. Commit all changes to git
3. Create GitHub repository
4. Publish to npm: `npm publish`
5. Submit to n8n for verification (optional)
6. Share with community!

## Getting Help

- **N8N Issues**: Check N8N logs at `~/.n8n/logs/`
- **AWS Issues**: Check CloudWatch logs in AWS Console
- **Package Issues**: Run `npm doctor`
- **Build Issues**: Delete node_modules and reinstall: `rm -rf node_modules && npm install`

For more help, open an issue on GitHub with:
- N8N version: `n8n --version`
- Node version: `node --version`
- Error logs
- Steps to reproduce
