# Publishing and Verification Guide

This guide walks you through publishing the AgentCore Browser node to npm and submitting it for n8n verification.

## Overview

To make this node available on N8N Cloud, you need to:
1. ✅ Build and test locally
2. 📦 Publish to npm
3. 🔍 Submit to n8n for verification
4. ⏳ Wait for n8n review (can take several weeks)
5. 🎉 Once verified, users can install directly from N8N Cloud

Reference: [n8n Community Nodes Documentation](https://docs.n8n.io/integrations/community-nodes/build-community-nodes/#submit-your-node-for-verification-by-n8n)

## Pre-Publishing Checklist

Before publishing, ensure:

### Code Quality
- [ ] All TypeScript compiles without errors: `npm run build`
- [ ] No linting errors: `npm run lint`
- [ ] Code is formatted: `npm run format`
- [ ] No console.log statements in production code
- [ ] Error handling is comprehensive

### Testing
- [ ] Tested on local N8N instance
- [ ] Both operations work (Run Script and Navigate & Extract)
- [ ] AWS connection works
- [ ] Screenshots work
- [ ] Error cases handled gracefully
- [ ] Session cleanup works on success and failure

### Documentation
- [ ] README.md is complete and accurate
- [ ] QUICK_START.md has working examples
- [ ] All example workflows tested
- [ ] API reference is accurate
- [ ] Troubleshooting section is helpful

### Package Configuration
- [ ] package.json has correct name: `n8n-nodes-agentcore-browser`
- [ ] Version follows semver (start with 0.1.0)
- [ ] Keywords include: `n8n-community-node-package`
- [ ] Author info is correct
- [ ] Repository URL is correct
- [ ] License is specified (MIT)
- [ ] Main entry point is correct
- [ ] Files array includes only dist/ folder

### Legal
- [ ] You have rights to publish this code
- [ ] LICENSE file exists
- [ ] No copyrighted code without attribution
- [ ] Dependencies have compatible licenses

## Step 1: Update Package Info

Update `package.json` with your information:

```json
{
  "name": "n8n-nodes-agentcore-browser",
  "version": "0.1.0",
  "author": {
    "name": "Your Name",
    "email": "your.email@example.com"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/YOUR-USERNAME/n8n-nodes-agentcore-browser.git"
  },
  "homepage": "https://github.com/YOUR-USERNAME/n8n-nodes-agentcore-browser"
}
```

## Step 2: Create GitHub Repository

1. **Create repository on GitHub:**
   - Name: `n8n-nodes-agentcore-browser`
   - Description: "N8N community node for AWS AgentCore Browser automation"
   - Public repository (required for verification)
   - Add README and LICENSE

2. **Push your code:**
```bash
cd /Users/edsilva/Downloads/git/agentcore_browser_extension
git init
git add .
git commit -m "Initial commit: AgentCore Browser N8N node"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/n8n-nodes-agentcore-browser.git
git push -u origin main
```

## Step 3: Publish to npm

### First Time Setup

1. **Create npm account** (if you don't have one):
   - Go to https://www.npmjs.com/signup
   - Verify your email

2. **Login to npm:**
```bash
npm login
# Enter your npm username, password, and email
```

3. **Verify login:**
```bash
npm whoami
```

### Publishing

1. **Final build:**
```bash
npm install
npm run build
```

2. **Test the package locally:**
```bash
# Check what will be published
npm pack --dry-run

# This shows which files will be included
```

3. **Publish to npm:**
```bash
# For first release (0.1.0)
npm publish

# For subsequent releases, update version first:
# npm version patch  # 0.1.0 -> 0.1.1
# npm version minor  # 0.1.0 -> 0.2.0
# npm version major  # 0.1.0 -> 1.0.0
# Then: npm publish
```

4. **Verify publication:**
   - Go to: https://www.npmjs.com/package/n8n-nodes-agentcore-browser
   - Check that package appears and has correct info

## Step 4: Test Installation from npm

Test that others can install your package:

1. **On a different machine or fresh N8N:**
```bash
npm install n8n-nodes-agentcore-browser
```

2. **Restart N8N and verify:**
   - Node appears in palette
   - All operations work
   - Credentials save correctly

## Step 5: Submit for n8n Verification

### Verification Requirements

According to [n8n documentation](https://docs.n8n.io/integrations/community-nodes/build-community-nodes/#submit-your-node-for-verification-by-n8n), your node must:

✅ **Package Requirements:**
- Published to npm with keyword `n8n-community-node-package`
- Version 1.0.0 or higher for verification
- Public GitHub repository
- Follows n8n node conventions

✅ **Code Quality:**
- Well-documented code
- Comprehensive error handling
- No security vulnerabilities
- Follows TypeScript best practices

✅ **User Experience:**
- Clear parameter descriptions
- Helpful placeholder text
- Intuitive operation names
- Good default values

### Submission Process

1. **Prepare your node for 1.0.0:**
```bash
# After thorough testing, update to 1.0.0
npm version major
# This updates package.json to 1.0.0
git push && git push --tags
npm publish
```

2. **Submit to n8n:**
   - Go to: https://www.n8n.io/community-node-submission (check current URL)
   - Or email: community@n8n.io
   - Include:
     - npm package link
     - GitHub repository link
     - Brief description
     - Why users would benefit from this node

3. **Example submission email:**
```
Subject: Community Node Submission: n8n-nodes-agentcore-browser

Hi n8n team,

I'd like to submit my community node for verification:

Package: https://www.npmjs.com/package/n8n-nodes-agentcore-browser
GitHub: https://github.com/YOUR-USERNAME/n8n-nodes-agentcore-browser
Version: 1.0.0

Description:
This node enables N8N users to automate browser tasks using AWS AgentCore
Browser and Playwright. It provides two operation modes:
1. Simple point-and-click data extraction (no coding required)
2. Advanced Playwright scripting for complex automation

Use cases:
- Web scraping and data extraction
- Automated testing
- Form submission automation
- Price monitoring
- Competitive analysis

The node is fully tested, documented, and includes example workflows.

Thank you for considering this node for verification!

Best regards,
[Your Name]
```

## Step 6: Wait for Review

- n8n team will review your submission (can take several weeks)
- They may request changes or improvements
- Once approved, your node will be marked as "verified"
- Verified nodes can be installed directly from N8N Cloud

## Maintaining Your Package

### Versioning

Follow [Semantic Versioning](https://semver.org/):
- **Patch** (0.1.0 → 0.1.1): Bug fixes
- **Minor** (0.1.0 → 0.2.0): New features, backward compatible
- **Major** (0.1.0 → 1.0.0): Breaking changes

### Update Process

1. **Make changes to code**
2. **Update CHANGELOG.md**
3. **Build and test:**
```bash
npm run build
npm run lint
# Test in N8N
```
4. **Update version:**
```bash
npm version patch  # or minor/major
```
5. **Commit and tag:**
```bash
git push && git push --tags
```
6. **Publish:**
```bash
npm publish
```

### Responding to Issues

- Monitor GitHub issues
- Respond to user questions
- Fix reported bugs promptly
- Add requested features when appropriate
- Keep dependencies updated

## Best Practices

### Documentation
- Keep README updated with new features
- Add examples for common use cases
- Document breaking changes clearly
- Maintain a CHANGELOG.md

### Code Quality
- Write clean, readable code
- Add comments for complex logic
- Follow TypeScript best practices
- Keep dependencies minimal and updated

### User Experience
- Provide helpful error messages
- Use sensible defaults
- Add parameter validation
- Include tooltips and descriptions

### Security
- Never log credentials
- Validate all user input
- Keep dependencies updated
- Fix security vulnerabilities quickly

## Resources

- [n8n Community Nodes Documentation](https://docs.n8n.io/integrations/community-nodes/)
- [n8n Node Development Guide](https://docs.n8n.io/integrations/creating-nodes/)
- [npm Publishing Documentation](https://docs.npmjs.com/packages-and-modules/contributing-packages-to-the-registry)
- [Semantic Versioning](https://semver.org/)

## Troubleshooting

**"Package name already taken":**
- Choose a different name: `n8n-nodes-agentcore-browser-automation`
- Add your username: `n8n-nodes-yourname-agentcore-browser`

**"No permission to publish":**
- Make sure you're logged in: `npm whoami`
- Check package name isn't taken: `npm info n8n-nodes-agentcore-browser`

**"n8n doesn't respond to submission":**
- Check submission went to correct email/form
- Follow up after 2-3 weeks if no response
- Join n8n community forum for support

**"Verification rejected":**
- Review feedback carefully
- Make requested changes
- Resubmit with improvements

## Timeline Expectations

- **npm publication:** Immediate
- **Initial testing:** 1-2 days
- **Verification submission:** Once ready
- **n8n review:** 2-6 weeks (varies)
- **Verification approval:** When requirements met

## After Verification

Once verified:
1. Update README to mention "Verified by n8n"
2. Announce on n8n community forum
3. Share on social media
4. Write blog post about your node
5. Continue maintaining and improving

## Questions?

- n8n Community Forum: https://community.n8n.io/
- n8n Discord: https://discord.gg/n8n
- GitHub Issues: Your repository issues page
- Email n8n: community@n8n.io
