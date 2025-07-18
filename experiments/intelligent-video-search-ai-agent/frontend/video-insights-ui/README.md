# Video Keeper - React Frontend

> **Modern React interface for intelligent video library search and discovery**

## Overview

This React application provides a user-friendly interface for Video Keeper, allowing users to search, discover, and interact with their video collections through natural conversation and advanced AI-powered search capabilities.

## Features

- **🤖 Conversational AI Interface** - Chat naturally with the Video Keeper assistant
- **🎬 Video Library Carousel** - Browse your video collection with thumbnail previews
- **🔍 Multi-Modal Search** - Text search, semantic search, and video-to-video similarity
- **📱 Real-Time Streaming** - WebSocket integration for live search results
- **🎯 Smart Suggestions** - Contextual search suggestions for different video types
- **📊 Rich Video Results** - Display video metadata, summaries, and insights
- **🔄 Session Context** - Maintains conversation history and video references

## Quick Start

### Prerequisites

- Node.js 16+ and npm
- Backend services running (MCP Server, AI Agent, Video API)

### Installation & Setup

```bash
# Navigate to frontend directory
cd frontend/video-insights-ui/

# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Edit .env with your backend URLs
# REACT_APP_API_URL=http://localhost:8080
# REACT_APP_VIDEO_API_URL=http://localhost:8091

# Start development server
npm start
```

The application will open at [http://localhost:3000](http://localhost:3000)

## Environment Configuration

Create a `.env` file with the following variables:

```bash
# Backend API URLs
REACT_APP_API_URL=http://localhost:8080
REACT_APP_VIDEO_API_URL=http://localhost:8091

# Optional: Application settings
REACT_APP_MAX_FILE_SIZE_MB=100
REACT_APP_DEBUG=false
REACT_APP_ENVIRONMENT=development
```

## Project Structure

```
src/
├── components/
│   └── VideoInsightsChat/           # Main chat interface
│       ├── index.tsx                # Main chat component
│       ├── MessageFormatter.tsx     # Markdown message rendering
│       ├── VideoCard.tsx            # Individual video display
│       ├── VideoCarousel.tsx        # Video library carousel
│       ├── VideoResults.tsx         # Search results display
│       └── VideoSimilaritySearch.tsx # Video upload for similarity search
├── types/
│   └── index.ts                     # TypeScript type definitions
├── hooks/                           # Custom React hooks (if any)
└── App.tsx                          # Main application component
```

## Key Components

### VideoInsightsChat
Main chat interface component featuring:
- Real-time WebSocket communication with AI agent
- Message history and session management
- Integration with video carousel and search results
- Support for both text and streaming responses

### VideoCarousel
Displays video library thumbnails:
- Fetches videos from Video API service
- Generates thumbnail previews
- Allows direct video selection for detailed information

### VideoSimilaritySearch
Video upload interface for finding similar content:
- Drag-and-drop video upload
- File validation and size limits
- Integration with backend similarity search API

### MessageFormatter
Renders formatted messages with:
- Markdown support for rich text
- Syntax highlighting for code blocks
- Link handling and text formatting

## API Integration

The frontend communicates with three backend services:

### 1. AI Agent API (Port 8080)
- **REST API**: `/chat` for synchronous requests
- **WebSocket**: `/ws/{session_id}` for real-time streaming
- **History**: `/history/{session_id}` for conversation management

### 2. Video API (Port 8091)
- **GET /videos**: Fetch video library for carousel
- **POST /search/video**: Upload video for similarity search
- **POST /search/similar/{video_id}**: Find similar videos

### 3. MCP Server (Port 8008)
- Connected through AI Agent
- Provides all search and analysis capabilities

## Development Scripts

```bash
# Start development server with hot reload
npm start

# Run type checking
npm run type-check

# Build for production
npm run build

# Run tests
npm test

# Lint code
npm run lint

# Format code
npm run format
```

## Search Interface Usage

### Text Search
Type natural language queries in the chat input:
- "Find videos about Python programming"
- "Show me happy family moments"
- "What videos feature presentations?"

### Video Upload Search
1. Click the "Search by Video" button
2. Upload or drag-drop a video file
3. System finds visually similar videos in your library
4. Results show similarity scores and relevant metadata

### Video Library Browse
- Use the expandable carousel to browse all videos
- Click any thumbnail to get detailed information
- System maintains context across video discussions

## Customization

### Styling
- Built with Tailwind CSS for responsive design
- Modify `tailwind.config.js` for custom themes
- Component styles are utility-first with custom CSS as needed

### Search Suggestions
Update suggestion lists in `index.tsx`:
```typescript
const suggestions: string[] = [
  "Find training videos about Python programming",
  "Show me gameplay from last month",
  // Add your custom suggestions
];
```

### UI Behavior
- WebSocket auto-reconnection with exponential backoff
- Error handling with user-friendly messages
- Responsive design for mobile and desktop

## Troubleshooting

### Common Issues

**Connection Errors**
- Verify backend services are running on correct ports
- Check CORS configuration if accessing from different domains
- Ensure WebSocket connections are not blocked by firewalls

**Video Upload Issues**
- Check file size limits in environment variables
- Verify supported video formats (MP4, MOV, AVI, MKV, WebM)
- Ensure Video API service is accessible

**Search Not Working**
- Confirm MCP server is connected and healthy
- Check OpenSearch index has video data
- Verify AI Agent can communicate with MCP server

### Debug Mode
Enable debug mode in `.env`:
```bash
REACT_APP_DEBUG=true
```

This provides additional console logging for troubleshooting.

## Production Deployment

### Build for Production
```bash
npm run build
```

### Environment Variables for Production
```bash
REACT_APP_API_URL=https://your-agent-api-domain.com
REACT_APP_VIDEO_API_URL=https://your-video-api-domain.com
REACT_APP_ENVIRONMENT=production
```

### Deployment Options
- Static hosting (Netlify, Vercel, S3 + CloudFront)
- Docker containerization
- Integration with AWS Amplify

## Technology Stack

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Lucide Icons** for UI icons
- **WebSocket** for real-time communication
- **Fetch API** for HTTP requests

## Contributing

When contributing to the frontend:
1. Follow TypeScript best practices
2. Maintain responsive design principles
3. Test WebSocket functionality thoroughly
4. Update type definitions as needed
5. Ensure accessibility standards are met