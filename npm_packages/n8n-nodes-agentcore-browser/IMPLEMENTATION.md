# Implementation Details

## How It Works (Simplified)

You were absolutely right! The implementation is actually quite simple. Here's what happens:

### 1. Start Browser Session (AWS API Call)
```typescript
// Call AWS AgentCore API to start a browser session
const command = new StartBrowserSessionCommand({
  browserIdentifier: 'aws.browser.v1',
  name: 'my-session',
  sessionTimeoutSeconds: 300,
  viewPort: { height: 1080, width: 1920 }
});

const response = await client.send(command);
// Response contains: { sessionId: 'session-123...' }
```

### 2. Generate CDP WebSocket URL
```typescript
// Simple URL construction from AWS docs
const wsUrl = `wss://bedrock-agentcore.${region}.amazonaws.com/browser-streams/${browserId}/sessions/${sessionId}/automation`;
```

### 3. Sign the URL with AWS SigV4
```typescript
// Standard AWS signing
const signer = new SignatureV4({
  service: 'bedrock-agentcore',
  region: region,
  credentials: credentials,
  sha256: Sha256,
});

const signedRequest = await signer.sign(httpRequest);
const headers = signedRequest.headers;
```

### 4. Connect Playwright (Your Code!)
```typescript
// This is exactly what you showed me!
const browser = await chromium.connectOverCDP(wsUrl, { headers });
const context = browser.contexts()[0] || await browser.newContext();
const page = await context.newPage();

// Now use Playwright normally:
await page.goto('https://www.some-website.com');
await page.fill('#twotabsearchtextbox', 'laptop');
await page.press('#twotabsearchtextbox', 'Enter');
await page.waitForSelector('div.s-main-slot', { timeout: 10000 });
await page.screenshot({ path: 'amazon_search.png' });
```

## Key Points

1. **The Playwright part is standard** - Your code example was perfect!
2. **The missing piece was the AWS API call** - `StartBrowserSessionCommand` from `@aws-sdk/client-bedrock-agentcore`
3. **URL format is documented** - `wss://bedrock-agentcore.{region}.amazonaws.com/browser-streams/{browserId}/sessions/{sessionId}/automation`
4. **Standard AWS SigV4 signing** - Nothing special, just sign the WebSocket upgrade request

## File Structure

```
utils/AgentcoreBrowserSession.ts
├── startSession()           # Calls AWS API, gets sessionId, generates signed CDP URL
├── connectBrowser()         # Your Playwright code!
├── executeScript()          # Runs user scripts
├── takeScreenshot()         # Takes screenshots
└── close()                  # Cleanup & stop AWS session
```

## AWS SDK Commands Used

From `@aws-sdk/client-bedrock-agentcore`:
- **StartBrowserSessionCommand** - Start a new browser session
- **StopBrowserSessionCommand** - Stop the session (cleanup)
- **GetBrowserSessionCommand** - Get session details (optional)

## What Changed from Original

**Before (over-complicated):**
- Made up fake session IDs
- Unclear what API to call
- Placeholder implementations

**After (simple & real):**
- Uses real AWS SDK: `StartBrowserSessionCommand`
- Real CDP URL format from AWS docs
- Proper SigV4 signing
- Your Playwright code unchanged!

## Testing the Implementation

```bash
# Install dependencies (now includes the correct SDK)
npm install

# Build
npm run build

# Set up local N8N
./setup-local-n8n.sh

# Test in N8N!
```

## What You Need to Test

1. **AWS Credentials** with AgentCore Browser permissions
2. **Region**: `us-east-1` (where AgentCore is available)
3. **Browser Tool ARN**: `arn:aws:bedrock-agentcore:us-east-1:aws:browser/aws.browser.v1`

## Expected Flow

1. N8N node calls `startSession()`
2. SDK calls AWS: `StartBrowserSessionCommand` → gets `sessionId`
3. Constructs CDP URL: `wss://bedrock-agentcore.us-east-1.amazonaws.com/browser-streams/aws.browser.v1/sessions/{sessionId}/automation`
4. Signs URL with SigV4
5. Playwright connects with signed headers
6. Your automation runs!
7. Session stops on cleanup

## Potential Issues to Watch For

### 1. SigV4 Header Passing
- Some browser automation frameworks don't pass custom headers to WebSocket handshake
- Playwright DOES support this: `chromium.connectOverCDP(url, { headers })`

### 2. Session Timeout
- Default: 300 seconds (5 minutes)
- Configurable in `startSession()`
- Make sure your automation completes in time

### 3. Region Availability
- AgentCore Browser is in preview
- Not available in all regions
- Use `us-east-1` for testing

### 4. Permissions
Must have:
- `bedrock-agentcore:StartBrowserSession`
- `bedrock-agentcore:StopBrowserSession`
- `bedrock-agentcore:ConnectBrowserAutomationStream`

## Next Steps

1. ✅ Implementation is now complete and uses real AWS SDK
2. ⬜ Test with your AWS credentials
3. ⬜ Verify it works end-to-end
4. ⬜ Debug any WebSocket connection issues
5. ⬜ Publish to npm once working

## Debugging

If connection fails:

1. **Check AWS credentials**: `aws sts get-caller-identity`
2. **Check browser tool exists**: `aws bedrock-agentcore list-browsers --region us-east-1`
3. **Check permissions**: Verify IAM policy
4. **Check WebSocket connection**: Look for 403 errors (signature issue) or 404 (wrong URL)
5. **Enable N8N debug logs**: `N8N_LOG_LEVEL=debug n8n start`

## Resources

- [AWS AgentCore Browser Docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html)
- [Starting a Browser Session](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-start-session.html)
- [Playwright CDP Documentation](https://playwright.dev/docs/api/class-browsertype#browser-type-connect-over-cdp)
- [AWS SDK for JavaScript v3](https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/)
