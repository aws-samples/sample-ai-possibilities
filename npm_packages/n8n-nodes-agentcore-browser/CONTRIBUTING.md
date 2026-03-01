# Contributing to AgentCore Browser N8N Node

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Node.js 18+ and npm
- N8N instance (local or cloud) for testing
- AWS account with AgentCore Browser access

### Setup Steps

1. Fork and clone the repository:
```bash
git clone https://github.com/yourusername/n8n-nodes-agentcore-browser.git
cd n8n-nodes-agentcore-browser
```

2. Install dependencies:
```bash
npm install
```

3. Build the project:
```bash
npm run build
```

4. Link for local development:
```bash
npm link
```

5. In your N8N installation directory:
```bash
npm link n8n-nodes-agentcore-browser
```

6. Restart N8N to load the node.

## Development Workflow

### File Structure
```
.
├── credentials/           # Credential types
│   └── AgentcoreBrowserApi.credentials.ts
├── nodes/                # Node implementations
│   └── AgentcoreBrowser/
│       ├── AgentcoreBrowser.node.ts
│       └── agentcore.svg
├── utils/                # Utility modules
│   └── AgentcoreBrowserSession.ts
├── examples/             # Example workflows
└── package.json
```

### Making Changes

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes following our coding standards (see below)

3. Test your changes:
```bash
npm run build
npm run lint
```

4. Test in N8N by creating a workflow using your modified node

### Coding Standards

- Use TypeScript for all code
- Follow existing code style (enforced by ESLint and Prettier)
- Add JSDoc comments for public methods
- Use meaningful variable and function names
- Keep functions small and focused

### Running Linters

```bash
# Check for lint errors
npm run lint

# Fix auto-fixable lint errors
npm run lintfix

# Format code
npm run format
```

## Testing

### Manual Testing

1. Build the node:
```bash
npm run build
```

2. Create test workflows in N8N covering:
   - Both operations (Run Script and Navigate & Extract)
   - Error cases
   - Different parameter combinations
   - Screenshots

3. Test with both AWS credential types:
   - Access Key
   - Temporary Credentials

### Test Checklist

Before submitting a PR, verify:
- [ ] Node appears in N8N node palette
- [ ] Credentials configuration works
- [ ] Navigate & Extract operation works
- [ ] Run Script operation works
- [ ] Screenshots are captured correctly
- [ ] Error handling works properly
- [ ] Session cleanup happens on both success and failure
- [ ] Documentation is updated

## Pull Request Process

1. Update README.md with details of changes if needed
2. Update CHANGELOG.md with your changes
3. Ensure all tests pass and linting is clean
4. Create a pull request with a clear title and description
5. Link any related issues

### PR Title Format
Use conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Build process or auxiliary tool changes

Example: `feat: add support for custom browser configurations`

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Changelog updated
```

## Adding New Features

### Adding a New Operation

1. Add operation definition in `AgentcoreBrowser.node.ts`:
```typescript
{
  name: 'Your Operation',
  value: 'yourOperation',
  description: 'Description of operation',
  action: 'Action description',
}
```

2. Add operation parameters using `displayOptions`

3. Implement the operation handler:
```typescript
private async executeYourOperation(
  session: AgentcoreBrowserSession,
  page: Page,
  itemIndex: number,
): Promise<any> {
  // Implementation
}
```

4. Call handler in the `execute()` method

5. Update documentation and add example workflow

### Adding New Parameters

1. Define parameter in the `properties` array
2. Use appropriate type and validation
3. Add helpful description and placeholder
4. Use `displayOptions` to show/hide based on other parameters
5. Document in README.md

## Reporting Bugs

Use GitHub Issues with the following information:
- N8N version
- Node version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages and logs
- AWS region being used

## Suggesting Enhancements

Open a GitHub Issue with:
- Clear description of the enhancement
- Use cases and benefits
- Potential implementation approach
- Examples if applicable

## Code Review Process

1. Maintainers will review PRs within 1-2 weeks
2. Address review comments by pushing new commits
3. Once approved, maintainers will merge

## Release Process

Maintainers will:
1. Update version in package.json
2. Update CHANGELOG.md
3. Create git tag
4. Publish to npm
5. Create GitHub release

## Questions?

Open a GitHub Discussion or Issue for questions about:
- Development setup
- Architecture decisions
- Feature planning
- AWS AgentCore integration

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
