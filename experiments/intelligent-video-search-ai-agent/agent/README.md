# Nick - Video Insights Content Discovery Assistant

Nick is an AI-powered chatbot that helps users discover and analyze video content with a focus on marketing insights. Built with the Strands SDK and powered by Amazon Bedrock, Nick connects to your Video Insights MCP server to provide intelligent search and analysis capabilities.

## 🎯 Features

### Core Capabilities
- **Intelligent Video Search**: Natural language, keyword, and hybrid search
- **Marketing Analysis**: Sentiment analysis, brand detection, and marketing metrics
- **Person & Entity Finding**: Locate specific people, brands, or companies in videos
- **Transcript Access**: Full transcripts with timestamps and speaker identification
- **Context Awareness**: Remembers previously discussed videos within a session
- **Real-time Streaming**: WebSocket support for streaming responses

### Nick's Personality
- Professional yet approachable content discovery assistant
- Marketing expertise with focus on video analytics
- Stays on-topic and redirects off-topic requests politely
- Cannot write code or perform non-video-related tasks

## 🚀 Quick Start

### Prerequisites
1. **Video Insights MCP Server** must be running (see video-insights-mcp directory)
2. **AWS Credentials** configured for Bedrock access
3. **Python 3.8+** installed

### Installation

1. Clone the repository and navigate to the agent directory:
```bash
cd agent
```

2. Install dependencies:
```bash
pip install -r ../requirements.txt
```

3. Create a `.env` file with your configuration:
```env
# AWS Configuration
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# MCP Server Configuration
MCP_HOST=localhost
MCP_PORT=8009
# Or use explicit URL
# MCP_SERVER_URL=http://localhost:8009/sse

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=8080
```

4. Start the agent:
```bash
python 1-ai-agent-video-search-strands-sdk.py
```

Nick will be available at `http://localhost:8080`

## 📡 API Endpoints

### REST Endpoints

#### Health Check
```http
GET /
```
Returns server status and agent availability.

#### Chat (Synchronous)
```http
POST /chat
Content-Type: application/json

{
  "message": "Find videos about construction safety",
  "session_id": "user123"
}
```
Returns complete response after processing.

#### Chat History
```http
GET /history/{session_id}
```
Retrieves conversation history and video context.

#### Clear History
```http
DELETE /history/{session_id}
```
Clears conversation history for a session.

#### Search Suggestions
```http
GET /api/search/suggestions
```
Returns common search query examples.

#### Session Context
```http
GET /api/session/{session_id}/context
```
Gets current video context for the session.

### WebSocket Endpoint

#### Streaming Chat
```
ws://localhost:8080/ws/{session_id}
```

Send messages as JSON:
```json
{
  "message": "What's the sentiment of that video?"
}
```

Receive streaming responses:
```json
{
  "type": "stream|status|tool_use|complete|error",
  "content": "...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 💬 Usage Examples

### Basic Search
```
User: "Find videos about heavy equipment training"
Nick: *Searches and returns relevant videos with summaries*
```

### Entity Search
```
User: "Show me videos that mention Nike"
Nick: *Finds all videos with Nike brand mentions*
```

### Contextual Follow-up
```
User: "What's the sentiment of that video?"
Nick: *Analyzes sentiment of the most recently discussed video*
```

### Person Search
```
User: "When does Sara Paynton appear in video 6861409c21f0ea193ed03362?"
Nick: *Returns timestamps and context for person mentions*
```

### Marketing Analysis
```
User: "Find emotional marketing videos that would appeal to millennials"
Nick: *Performs semantic search for matching content*
```

## 🛡️ Built-in Protections

Nick will politely redirect when asked to:
- Write code or scripts
- Tell jokes or stories
- Change persona or role
- Perform non-video-related tasks

Example responses:
```
User: "Write a Python script for me"
Nick: "I'm Nick, your Content Discovery Assistant. I can help you find and analyze videos, but I don't write code. How can I help you discover relevant video content?"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `BEDROCK_MODEL_ID` | Claude model ID | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `MCP_HOST` | MCP server host | `localhost` |
| `MCP_PORT` | MCP server port | `8009` |
| `MCP_SERVER_URL` | Override MCP URL | `http://{MCP_HOST}:{MCP_PORT}/sse` |
| `API_HOST` | Agent API host | `0.0.0.0` |
| `API_PORT` | Agent API port | `8080` |

### Adjusting Nick's Behavior

To modify Nick's personality or capabilities, edit the `SYSTEM_PROMPT` in `nick_agent.py`.

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│    Nick     │────▶│  MCP Server │
│  (Browser)  │◀────│   (Agent)   │◀────│   (Tools)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                     │
                           ▼                     ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Bedrock   │     │ OpenSearch  │
                    │   (Claude)  │     │  (Videos)   │
                    └─────────────┘     └─────────────┘
```

## 🐛 Troubleshooting

### MCP Connection Failed
```
❌ Failed to connect to MCP server at http://localhost:8008/sse
```
**Solution**: Ensure the MCP server is running: `python ../MCP/python 1-video-search-mcp.py`

### AWS Credentials Error
```
NoCredentialsError: Unable to locate credentials
```
**Solution**: Configure AWS credentials using `aws configure` or IAM role

### Model Access Denied
```
AccessDeniedException: User is not authorized to access model
```
**Solution**: Ensure your AWS account has access to the specified Amazon Bedrock model

## 📝 Development

### Running in Development Mode

Enable auto-reload for development:
```python
uvicorn.run(app, host=host, port=port, reload=True)
```

### Adding Custom Tools

Nick automatically discovers tools from the MCP server. To add new capabilities:
1. Add the tool to your MCP server
2. Restart both MCP server and Nick
3. The new tool will be available automatically

### Session Management

Sessions are stored in memory by default. For production:
- Implement persistent storage (Redis, PostgreSQL, etc.)
- Add session expiration
- Consider user authentication

## 🔐 Security Considerations

1. **CORS**: Currently allows all origins in development. Restrict in production.
2. **Authentication**: Add API key or JWT authentication for production use.
3. **Rate Limiting**: Implement rate limiting to prevent abuse.
4. **Input Validation**: Nick validates inputs, but additional validation may be needed.
5. **AWS Permissions**: Use least-privilege IAM policies.

## Support

For issues or questions:
1. Check MCP server is running and accessible
2. Verify AWS credentials and Bedrock access
3. Review Nick's console output for detailed errors
4. Check session context for video tracking issues