# Video Keeper - AI Agent

> **Conversational AI agent powered by AWS Strands SDK for intelligent video discovery**

An AI-powered conversational agent that provides natural language access to your video library. Built with AWS Strands SDK and Claude 3.5 Sonnet, this agent serves as an intelligent interface for video search, analysis, and discovery.

## Features

### 🤖 Conversational AI Interface
- **Natural Language Processing**: Powered by Claude 3.5 Sonnet via Amazon Bedrock
- **Context Awareness**: Maintains conversation history and video references
- **Smart Responses**: Understands intent and provides relevant video suggestions
- **Multi-Turn Conversations**: Supports follow-up questions and clarifications

### 🎬 Universal Video Understanding
- **Content Agnostic**: Works with any video type (educational, personal, professional, entertainment)
- **Entity Recognition**: Finds people, brands, objects, and locations in videos
- **Sentiment Analysis**: Understands emotional tone and content mood
- **Topic Discovery**: Identifies themes and subjects across video collections

### 🔍 Advanced Search Capabilities
- **Semantic Search**: Natural language queries like "Find happy family moments"
- **Entity Search**: "Show me videos with John Smith" or "Find videos mentioning Python"
- **Visual Similarity**: Upload a video to find similar content
- **Temporal Search**: "Videos from last month" or "Recent presentations"
- **Sentiment Filtering**: "Find positive/uplifting content"

### 🔄 Real-Time Features
- **WebSocket Streaming**: Live responses with real-time tool execution updates
- **Session Management**: Persistent conversations with context tracking
- **Tool Status Updates**: See which search tools are being used in real-time
- **Progressive Loading**: Stream results as they become available

## Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured with Bedrock access
- MCP Server running (video search backend)
- OpenSearch index with video data

### Installation

```bash
# Navigate to agent directory
cd agent/

# Install dependencies (from project root)
pip install -r ../requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
# BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
# MCP_HOST=localhost
# MCP_PORT=8008

# Start the AI agent
python 1-ai-agent-video-search-strands-sdk.py
```

Agent runs at: `http://localhost:8080`

## Configuration

### Required Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1

# AI Model Configuration
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# MCP Server Connection
MCP_HOST=localhost
MCP_PORT=8008
# Alternative: MCP_SERVER_URL=http://localhost:8008/sse

# Agent API Configuration
API_HOST=localhost
API_PORT=8080
```

### Optional Configuration

```bash
# Model Behavior
MODEL_TEMPERATURE=0.3
STREAMING_ENABLED=true

# Development
DEBUG=false
ENVIRONMENT=development
RELOAD=false
LOG_LEVEL=INFO
```

## API Endpoints

### REST API

#### Health Check
```bash
GET /
# Returns agent status and availability
```

#### Synchronous Chat
```bash
POST /chat
Content-Type: application/json

{
  "message": "Find videos about Python programming",
  "session_id": "user_session_123"
}
```

#### Video Library Access
```bash
GET /videos
# Direct access to video carousel data
```

#### Session Management
```bash
# Get conversation history
GET /history/{session_id}

# Clear conversation history
DELETE /history/{session_id}

# Get session video context
GET /api/session/{session_id}/context
```

#### Search Suggestions
```bash
GET /api/search/suggestions
# Returns contextual search suggestions
```

#### Video Similarity Search
```bash
POST /search/video
Content-Type: multipart/form-data

file: video_file.mp4
use_visual_similarity: true
max_results: 10
```

### WebSocket API

#### Real-Time Streaming
```bash
WebSocket: /ws/{session_id}
```

**Message Format:**
```json
{
  "message": "Find videos about machine learning"
}
```

**Response Types:**
```json
// Status updates
{
  "type": "status",
  "message": "Searching video database..."
}

// Tool execution
{
  "type": "tool_use", 
  "tool": "search_videos_by_semantic_query",
  "status": "Performing semantic search..."
}

// Streaming content
{
  "type": "stream",
  "content": "I found several videos about machine learning...",
  "timestamp": "2024-01-01T00:00:00Z"
}

// Completion
{
  "type": "complete",
  "timestamp": "2024-01-01T00:00:00Z",
  "metadata": {"video_context": {...}}
}
```

## Agent Behavior & Capabilities

### Conversational Guidelines
The agent is designed to:
- **Stay Focused**: Only helps with video-related queries
- **Be Helpful**: Provides comprehensive search and analysis
- **Maintain Context**: References previous videos and conversations
- **Be Accurate**: Only suggests actions it can actually perform
- **Redirect Gracefully**: Politely redirects off-topic requests

### Supported Query Types

**Content Discovery:**
- "Find training videos about data science"
- "Show me family vacation videos"
- "What gaming videos do I have?"

**Entity Search:**
- "Find videos featuring Sarah Johnson"
- "Show me videos mentioning AWS"
- "What videos have Tesla in them?"

**Temporal Queries:**
- "Videos from last month"
- "Recent presentation recordings"
- "Content uploaded this year"

**Sentiment-Based:**
- "Find uplifting or positive videos"
- "Show me exciting gameplay moments"
- "What educational content do I have?"

**Analysis Requests:**
- "Summarize this video for me"
- "What's the sentiment of video ABC123?"
- "Get the transcript of my meeting recording"

### Context Management

The agent maintains:
- **Session History**: Complete conversation threads
- **Video References**: Recently mentioned or searched videos
- **User Preferences**: Learned patterns from interactions
- **Search Context**: Previous queries and results

## Integration with MCP Server

The agent connects to the MCP Server for all video operations:

### Available Tools
- **Search Tools**: Keyword, semantic, hybrid, and title search
- **Analysis Tools**: Sentiment, summary, transcript, and details
- **Discovery Tools**: Person search, entity detection, similarity matching
- **Management Tools**: Library overview, video uploads

### Tool Execution Flow
1. User asks question in natural language
2. Agent analyzes intent and selects appropriate tools
3. MCP Server executes search/analysis operations
4. Agent formats results into conversational responses
5. Results are streamed back to user in real-time

## Testing & Validation

### Automated Test Suite

```bash
# Run comprehensive agent tests
python 2-test_agent.py
```

**Tests Include:**
- ✅ Health check and basic connectivity
- ✅ Chat API endpoint functionality
- ✅ WebSocket streaming and real-time updates
- ✅ Session management and history
- ✅ Video context tracking
- ✅ Error handling and edge cases
- ✅ MCP server integration

### Manual Testing

**Basic Functionality:**
```bash
# Test health endpoint
curl http://localhost:8080/

# Test chat endpoint
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find videos about programming", "session_id": "test"}'
```

**WebSocket Testing:**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/test_session');
ws.send(JSON.stringify({
  message: "Show me all videos in my library"
}));
```

### Expected Behaviors

**On-Topic Requests:**
- Provides helpful video search and analysis
- Uses appropriate tools for the query type
- Maintains conversational context
- Offers relevant follow-up suggestions

**Off-Topic Requests:**
- Politely redirects to video-related assistance
- Explains available capabilities
- Suggests alternative video-related queries

## Error Handling

### Connection Issues
- **MCP Server Unavailable**: Graceful degradation with clear error messages
- **WebSocket Disconnection**: Automatic reconnection with exponential backoff
- **Timeout Handling**: Configurable timeouts for long operations

### Query Processing
- **Invalid Requests**: Helpful error messages with suggestions
- **No Results Found**: Suggests alternative search strategies
- **Tool Failures**: Transparent error reporting with troubleshooting steps

### Common Error Responses

```json
{
  "error": "MCP server connection failed",
  "suggestion": "Please ensure the MCP server is running on port 8008",
  "fallback": "You can try basic video library browsing instead"
}
```

## Performance Optimization

### Response Speed
- **Streaming Responses**: Start showing results immediately
- **Tool Caching**: Cache frequently used search results
- **Connection Pooling**: Efficient MCP server communication

### Memory Management
- **Session Cleanup**: Automatic cleanup of old sessions
- **Context Limits**: Reasonable limits on conversation history
- **Resource Monitoring**: Track memory usage and connections

## Development

### Adding New Capabilities

1. **Extend System Prompt**: Add new instruction patterns
2. **Tool Integration**: Connect new MCP tools to agent
3. **Response Formatting**: Update message formatting for new data types
4. **Testing**: Add test cases for new functionality

### Custom Personalities

Modify the system prompt in `1-ai-agent-video-search-strands-sdk.py`:

```python
SYSTEM_PROMPT = """You are the Video Keeper Assistant, a [your customization here]..."""
```

### Debug Mode

Enable detailed logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python 1-ai-agent-video-search-strands-sdk.py
```

## Production Deployment

### Environment Setup
```bash
# Production environment variables
ENVIRONMENT=production
DEBUG=false
RELOAD=false
API_HOST=0.0.0.0
API_PORT=8080
```

### Security Considerations
- Enable authentication for production use
- Implement rate limiting for API endpoints
- Secure WebSocket connections with WSS
- Monitor for unusual usage patterns

### Scaling Options
- **Horizontal Scaling**: Run multiple agent instances behind load balancer
- **Vertical Scaling**: Increase memory/CPU for high-throughput scenarios
- **Regional Deployment**: Deploy closer to users for reduced latency

## Troubleshooting

### Common Issues

**Agent Won't Start:**
- Check if port 8080 is available
- Verify AWS credentials and Bedrock access
- Ensure MCP server is running and accessible

**No Search Results:**
- Verify MCP server connection
- Check OpenSearch index has data
- Validate video processing pipeline

**Slow Responses:**
- Monitor MCP server performance
- Check OpenSearch cluster health
- Review network connectivity

### Monitoring

**Health Checks:**
```bash
# Basic health
curl http://localhost:8080/

# Detailed status (if implemented)
curl http://localhost:8080/health/detailed
```

**Logs Analysis:**
```bash
# View real-time logs
tail -f agent.log

# Search for errors
grep "ERROR" agent.log
```

## Contributing

When contributing to the agent:
1. Follow the existing system prompt patterns
2. Test both REST and WebSocket interfaces
3. Ensure graceful error handling
4. Update test suite for new features
5. Document any new configuration options
6. Consider conversation flow and user experience