# Quick Start Guide

Get up and running with AgentCore Browser N8N node in 10 minutes.

## 1. Install the Node

### ⚠️ Important: N8N Cloud Limitation
**N8N Cloud only supports verified community nodes.** This node is currently unverified, so you must use **self-hosted N8N** for testing.

### Self-Hosted Installation
```bash
# Option 1: If package is published to npm
npm install n8n-nodes-agentcore-browser

# Option 2: For development/testing
cd /path/to/agentcore_browser_extension
npm install
npm run build
npm link
cd /path/to/n8n
npm link n8n-nodes-agentcore-browser

# Restart N8N
```

For detailed setup instructions, see [TESTING.md](TESTING.md)

## 2. Set Up AWS Credentials

### Create IAM User

1. Go to AWS IAM Console
2. Create new user: `n8n-agentcore-browser`
3. Attach this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:ListBrowserTools",
        "bedrock-agentcore:GetBrowserTool",
        "bedrock-agentcore:InvokeAgent",
        "bedrock-agent-runtime:InvokeAgent"
      ],
      "Resource": "*"
    }
  ]
}
```

4. Create access key and save the credentials

## 3. Configure N8N Credentials

1. In N8N, add **AgentCore Browser** node
2. Create new credential:
   - **AWS Region**: `us-east-1`
   - **Authentication**: Access Key
   - **Access Key ID**: Your access key
   - **Secret Access Key**: Your secret key
3. Test connection and save

## 4. First Workflow: Extract Page Title

Let's create a simple workflow to extract a page title:

1. Add **Manual Trigger** node
2. Add **AgentCore Browser** node
3. Configure:
   - **Operation**: Navigate and Extract
   - **Start URL**: `https://example.com`
   - **Selector**: `h1`
   - **Extract Mode**: Text Content
   - **Take Screenshot**: Yes
4. Execute and view results!

## 5. Second Workflow: Search and Extract

Now let's do something more interesting - search for something and extract results:

1. Add **Manual Trigger** node
2. Add **AgentCore Browser** node
3. Configure:
   - **Operation**: Navigate and Extract
   - **Start URL**: `https://www.google.com`
   - **Selector**: `.g h3`
   - **Extract Mode**: Text Content

4. Add Actions:
   - Action 1: Type Text
     - Selector: `[name="q"]`
     - Value: `n8n automation`
   - Action 2: Press Key
     - Selector: `[name="q"]`
     - Value: `Enter`
   - Action 3: Wait
     - Value: `3000`

5. Set **Wait for Selector**: `#search`
6. Execute!

## 6. Advanced: Custom Script

For full control, use the Run Script operation:

```javascript
// Wait for page load
await page.waitForLoadState('networkidle');

// Click accept cookies
try {
  await page.click('#accept', { timeout: 5000 });
} catch (e) {
  // No cookie banner
}

// Get page info
const title = await page.title();
const url = page.url();

// Extract specific data
const data = await page.evaluate(() => {
  return {
    headings: Array.from(document.querySelectorAll('h1, h2'))
      .map(h => h.textContent),
    links: Array.from(document.querySelectorAll('a'))
      .slice(0, 10)
      .map(a => ({ text: a.textContent, href: a.href }))
  };
});

// Return results
return {
  title,
  url,
  ...data
};
```

## Common Use Cases

### Price Monitoring
- Schedule trigger (daily)
- Extract price from product page
- Compare with threshold
- Send email alert if price drops

### Form Automation
- Webhook trigger
- Fill form with webhook data
- Submit form
- Return success/error

### Data Collection
- Extract data from multiple pages
- Store in Google Sheets/database
- Generate reports

### Testing
- Navigate through user flows
- Take screenshots at each step
- Verify expected elements exist

## Tips

1. **Use DevTools**: Open the target site in Chrome DevTools to find the right selectors
2. **Start Simple**: Begin with Navigate & Extract, then move to scripts for complex tasks
3. **Add Waits**: Websites load at different speeds; use waits for dynamic content
4. **Take Screenshots**: Enable screenshots during development for debugging
5. **Handle Errors**: Enable "Continue on Fail" in node settings for production workflows

## Troubleshooting

**Node doesn't appear in palette**
- Restart N8N after installation
- Check package is installed: `npm list n8n-nodes-agentcore-browser`

**Connection failed**
- Verify AWS credentials are correct
- Check region is `us-east-1` (or region where AgentCore is available)
- Verify IAM permissions

**Selector not found**
- Use Chrome DevTools to find the correct selector
- Add "Wait for Selector" parameter
- Check if content loads dynamically

**Timeout errors**
- Increase timeout value
- Check website is accessible
- Verify selectors are correct

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Check [examples/](examples/) for workflow templates
3. Join N8N community for support
4. Explore [Playwright documentation](https://playwright.dev/docs/api/class-page) for advanced scripting

## Need Help?

- GitHub Issues: Report bugs or request features
- N8N Community: Ask questions and share workflows
- AWS Docs: Learn about AgentCore Browser

Happy automating!
