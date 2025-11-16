# n8n-nodes-agentcore-browser

[![NPM Version](https://img.shields.io/npm/v/n8n-nodes-agentcore-browser)](https://www.npmjs.com/package/n8n-nodes-agentcore-browser)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-yellow.svg)](https://opensource.org/licenses/MIT-0)

An n8n community node for browser automation using Amazon Bedrock AgentCore Browser and Playwright. This node enables AI agents and workflows to interact with websites, perform web scraping, fill forms, and execute complex browser tasks using natural language instructions.

## Features

- **AI Agent Compatible**: Works as an n8n AI Agent tool with natural language instructions
- **Dual Authentication**: Support for both standard AWS credentials and custom AgentCore Browser API credentials
- **Three Operation Modes**:
  - **Agent Instructions**: Execute browser tasks from natural language (ideal for AI agents)
  - **Run Script**: Execute custom Playwright scripts
  - **Navigate & Extract**: Navigate to URLs and extract data with CSS selectors
- **Playwright Integration**: Full access to Playwright's browser automation capabilities
- **Screenshot Support**: Capture screenshots during execution
- **Amazon Bedrock AgentCore**: Leverages AWS-managed browser infrastructure with SigV4 authentication

## Installation

### Via n8n Community Nodes

1. In n8n, go to **Settings** → **Community Nodes**
2. Select **Install**
3. Enter `n8n-nodes-agentcore-browser`
4. Agree to the risks and click **Install**
5. Restart n8n

### Via npm (for self-hosted n8n)

```bash
cd ~/.n8n
npm install n8n-nodes-agentcore-browser
```

Then restart your n8n instance.

### Via Docker

Add to your n8n Docker environment:

```bash
docker run -it --rm \
  -p 5678:5678 \
  -e N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

Then install via the n8n UI or use a custom Dockerfile:

```dockerfile
FROM n8nio/n8n:latest
USER root
RUN npm install -g n8n-nodes-agentcore-browser
USER node
```

## Prerequisites

### AWS Requirements

1. **AWS Account** with access to AWS Bedrock AgentCore
2. **IAM Permissions** for `bedrock-agentcore:*` actions
3. **AWS Region**: Currently available in `us-east-1`

### Minimum IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:StartBrowserSession",
        "bedrock-agentcore:GetBrowserSession",
        "bedrock-agentcore:ExecuteBrowserAction"
      ],
      "Resource": "*"
    }
  ]
}
```

## Configuration

### Credentials Setup

This node supports two authentication methods:

#### Option 1: AWS Credentials (Recommended)

Reuse existing AWS credentials from other n8n AWS nodes:

1. In n8n, create or select **AWS** credentials
2. Provide:
   - **AWS Access Key ID**
   - **AWS Secret Access Key**
   - **Region**: `us-east-1`

#### Option 2: AgentCore Browser API Credentials

Use custom credentials with support for VPC endpoints:

1. Create **AgentCore Browser API** credentials
2. Provide:
   - **AWS Region**: `us-east-1`
   - **Access Key ID**
   - **Secret Access Key**
   - **Session Token** (optional, for temporary credentials)
   - **Custom Endpoint** (optional, for VPC endpoints)

## Usage

### Operation 1: Agent Instructions (AI Agent Mode)

Perfect for AI agents using natural language instructions.

**Parameters:**
- **Instructions**: Natural language description of the browser task
- **Start URL**: The website to navigate to
- **URL Override**: Optional URL override
- **Timeout**: Maximum execution time in milliseconds

**Example Workflow:**

```
AI Agent → AgentCore Browser (Agent Instructions mode) → Process Results
```

**Example Instructions:**

```
Step 1: Wait for the Amazon homepage to load completely.
Step 2: Locate the search input field at the top of the page.
Step 3: Type "wireless headphones" into the search field.
Step 4: Click the search button (the magnifying glass icon).
Step 5: Wait for the search results page to load.
Step 6: Extract the names and prices of the top 3 products.
```

### Operation 2: Run Script

Execute custom Playwright scripts with full browser control.

**Parameters:**
- **Script**: JavaScript/TypeScript code (the `page` object is available)
- **Start URL**: Initial page to load
- **Screenshot Mode**: None, Final Page, or On Error Only

**Example Script:**

```javascript
// Wait for page to be fully loaded
await page.waitForLoadState('networkidle');

// Extract all product titles
const products = await page.$$eval('.product-title', elements =>
  elements.map(el => el.textContent)
);

// Return data
return {
  count: products.length,
  products
};
```

### Operation 3: Navigate and Extract

Structured data extraction using CSS selectors.

**Parameters:**
- **Start URL**: The page to navigate to
- **Selector**: CSS selector for elements to extract
- **Extract Mode**: Text Content, HTML, or Attribute
- **Actions**: Optional click, type, wait, or press key actions
- **Wait for Selector**: Optional selector to wait for before extraction

**Example Configuration:**

```
Start URL: https://example.com/products
Selector: .product-card h2
Extract Mode: Text Content
Actions:
  - Click: .load-more-button
  - Wait: 2000ms
Wait for Selector: .products-loaded
```

## AI Agent Integration

### System Prompt Template

Use this system prompt to help AI agents generate effective browser instructions:

```markdown
# AgentCore Browser Tool Instructions

You have access to an AgentCore Browser tool that can perform browser automation tasks using Playwright.

## How to Use

When you need to interact with a website:
1. Break down the task into clear, sequential steps
2. Use step-by-step numbered instructions
3. Be specific about UI elements (e.g., "search field at the top", "blue submit button")

## Instruction Guidelines

**Good Instructions:**
- Use numbered steps (Step 1, Step 2, etc.)
- Specify exact actions (click, type, wait, extract)
- Reference UI elements clearly
- Include wait steps for page loads

**Example:**
```
Step 1: Wait for the page to load completely.
Step 2: Locate the search input field with id "search-box".
Step 3: Type "laptop computers" into the search field.
Step 4: Click the search button next to the input field.
Step 5: Wait for the results page to load.
Step 6: Extract the product names from elements with class "product-title".
```

## Available Actions

- Navigate to URLs
- Fill input fields
- Click buttons and links
- Wait for page loads or specific elements
- Extract text, HTML, or attributes
- Capture screenshots

## Output

The tool returns:
- **results**: Extracted data (for search/extraction tasks)
- **url**: Final page URL
- **title**: Page title
- **sessionInfo**: Browser session details
- **screenshot**: Screenshot data (if requested)
```

### Environment Variable

Enable community nodes as tools in n8n:

```bash
export N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
```

Or in Docker:

```yaml
environment:
  - N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
```

## Examples

### Example 1: Product Search

Search Amazon and extract top products:

```
Operation: Agent Instructions
Start URL: https://amazon.com
Instructions:
  Step 1: Wait for homepage to load
  Step 2: Type "wireless mouse" in the search field
  Step 3: Click search button
  Step 4: Wait for results
  Step 5: Extract top 3 product names and prices
```

### Example 2: Form Filling

```
Operation: Navigate and Extract
Start URL: https://example.com/contact
Actions:
  - Type in #name: "John Doe"
  - Type in #email: "john@example.com"
  - Type in #message: "Hello world"
  - Click: button[type="submit"]
Wait for Selector: .success-message
Selector: .success-message
Extract Mode: Text Content
```

### Example 3: Custom Playwright Script

```javascript
// Navigate to a dynamic page
await page.goto('https://example.com/dashboard');

// Wait for AJAX content
await page.waitForSelector('.data-loaded', { timeout: 10000 });

// Extract complex data
const data = await page.evaluate(() => {
  const rows = document.querySelectorAll('.data-row');
  return Array.from(rows).map(row => ({
    id: row.dataset.id,
    name: row.querySelector('.name').textContent,
    value: row.querySelector('.value').textContent
  }));
});

return { totalRecords: data.length, data };
```

## Troubleshooting

### Common Issues

**Issue: "Browser session timeout"**
- **Solution**: Increase the timeout value in node parameters or session timeout settings

**Issue: "Selector not found"**
- **Solution**: Use browser DevTools to verify CSS selectors, add wait conditions before extraction

**Issue: "AWS credentials invalid"**
- **Solution**: Verify IAM permissions include `bedrock-agentcore:*` actions

**Issue: "Tool not available for AI Agent"**
- **Solution**: Ensure `N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true` is set

**Issue: "Page navigation timeout"**
- **Solution**: Some pages load slowly, increase the timeout parameter or use `waitUntil: 'domcontentloaded'` instead of `networkidle`

### Debug Tips

1. **Enable screenshots** to see what the browser is actually showing
2. **Use shorter timeouts** during development to fail fast
3. **Test selectors** in browser DevTools before using in workflows
4. **Check AWS CloudWatch** logs for AgentCore Browser API errors

## Node Parameters Reference

### Common Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| Authentication | Options | aws | AWS or AgentCore Browser API |
| Browser Tool ARN | String | `arn:aws:bedrock-agentcore:us-east-1:aws:browser/aws.browser.v1` | ARN of the AgentCore Browser tool |
| Start URL | String | - | URL to navigate to |
| Timeout (ms) | Number | 60000 | Maximum operation time |

### Agent Instructions Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| Instructions | String | - | Natural language browser task instructions |
| URL Override | String | - | Optional URL override |
| Session Timeout | Number | 900 | Browser session timeout in seconds |

### Run Script Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| Script | String | - | Playwright JavaScript/TypeScript code |
| Screenshot Mode | Options | none | When to capture screenshots |

### Navigate & Extract Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| Selector | String | - | CSS selector for data extraction |
| Extract Mode | Options | text | Text, HTML, or Attribute |
| Attribute Name | String | - | Attribute to extract (when mode is 'attribute') |
| Wait for Selector | String | - | Selector to wait for before extraction |
| Actions | Array | - | Actions to perform (click, type, wait, press) |
| Take Screenshot | Boolean | false | Capture screenshot after extraction |

## Development

### Building from Source

```bash
git clone https://github.com/aws-samples/sample-ai-possibilities.git
cd npm_packages/n8n-nodes-agentcore-browser
npm install
npm run build
```

### Running Tests Locally

```bash
# Build the package
npm run build

# Lint
npm run lint

# Format code
npm run format
```

### Local Docker Testing

Use the included test script:

```bash
./test-before-cfn.sh
```

This will:
1. Build a Docker image with n8n and the custom node
2. Start n8n on http://localhost:5678
3. Load the node as a custom extension

## License

MIT-0 License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `npm run lint` and `npm run format`
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/aws-samples/sample-ai-possibilities/issues)
- **Documentation**: [Amazon Bedrock AgentCore Browser Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-browser.html)
- **n8n Community**: [n8n Community Forum](https://community.n8n.io/)

## Changelog

### 0.1.0 (Initial Release)

- ✅ Agent Instructions mode with natural language support
- ✅ Run Script mode with full Playwright access
- ✅ Navigate & Extract mode with CSS selectors
- ✅ Dual authentication (AWS + custom credentials)
- ✅ AI Agent tool compatibility
- ✅ Screenshot capture support
- ✅ Amazon search example implementation

## Acknowledgments

- Built with [n8n](https://n8n.io/)
- Powered by [AWS Bedrock AgentCore](https://aws.amazon.com/bedrock/)
- Browser automation by [Playwright](https://playwright.dev/)

---

**Note**: This is a community node and is not officially supported by n8n GmbH or Amazon Web Services. Use at your own discretion.
