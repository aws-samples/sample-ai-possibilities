# Recipe Genie Frontend

React-based frontend for the Recipe Genie demo application.

## Overview

This is the web interface for Recipe Genie, featuring:
- Real-time chat interface with WebSocket support
- Streaming AI responses with visual feedback
- Mobile-responsive design using Tailwind CSS
- Automatic reconnection and error handling

## Quick Start
Follow the demo instructions presented [here](../README.md).

## Configuration

Set the backend API URL in your environment:

```bash
# .env
REACT_APP_API_URL=http://localhost:8080
```

## Available Scripts

- `npm start` - Runs the app in development mode (http://localhost:3000)
- `npm test` - Launches the test runner
- `npm run build` - Builds the app for production
- `npm run eject` - Ejects from Create React App (one-way operation)

## Key Components

- `RecipeGenieChat.js` - Main chat interface component
  - WebSocket connection management
  - Message streaming and formatting
  - Suggestion chips for quick interactions

## Technologies Used

- React 19
- Tailwind CSS for styling
- Lucide React for icons
- WebSocket for real-time communication

## Notes

This frontend is part of the Recipe Genie demo showcasing Amazon Bedrock, Strands Agents SDK with MCP integration. See the main [README.md](../README.md) for complete setup instructions.