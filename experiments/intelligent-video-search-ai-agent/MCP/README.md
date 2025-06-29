# MCP Video Insights Server

A Model Context Protocol (MCP) server built with FastMCP for searching and analyzing video insights stored in Amazon OpenSearch Serverless. This server is designed to work with AI agents built using the Strands SDK, providing intelligent search capabilities across video content, transcripts, and marketing insights.

## Features

### Search Capabilities

1. **Keyword Search** (`search_videos_by_keywords`)
   - Search across video titles, summaries, brands, companies, and people names
   - Multi-field search with customizable field selection
   - Returns relevant videos with metadata

2. **Semantic Search** (`search_videos_by_semantic_query`)
   - Natural language queries using embeddings
   - Supports both video content and text-based Pegasus insights embeddings
   - Returns semantically similar videos

3. **Video Details** (`get_video_details`)
   - Comprehensive video information including summary, chapters, and entities
   - Optional transcript and marketing metrics inclusion
   - Flexible response based on requirements

4. **Person Search in Video** (`search_person_in_video`)
   - Find specific person mentions within a video
   - Returns timestamps and context
   - Useful for finding when someone was mentioned

5. **Sentiment Analysis** (`get_video_sentiment`)
   - Get sentiment breakdown for a video
   - Returns positive/neutral/negative percentages

6. **Video Summary** (`get_video_summary`)
   - Quick access to video summary and key topics
   - Includes hashtags and key entities

7. **Transcript Access** (`get_video_transcript`)
   - Multiple formats: full text, segments, or speaker-labeled
   - Timestamps included for segments

## Installation

1. Clone the repository and install dependencies:

```bash
pip install -r ../requirements.txt
```

2. Set up environment variables (see Configuration section)

3. Run the server:

```bash
python 1-video-search-mcp.py
```

## Configuration

### Required Environment Variables

- `AWS_REGION`: AWS region for OpenSearch (e.g., `us-east-1`)
- `OPENSEARCH_ENDPOINT`: Your OpenSearch Serverless endpoint (without https://)
- `OPENSEARCH_INDEX`: Index name (default: `video-insights`)

### Optional Environment Variables

- `MCP_HOST`: Host for the MCP server (default: `localhost`)
- `MCP_PORT`: Port for the MCP server (default: `8009`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Example `.env` file

```env
AWS_REGION=us-east-1
OPENSEARCH_ENDPOINT=your-domain.us-east-1.aoss.amazonaws.com
OPENSEARCH_INDEX=video-insights
COHERE_API_KEY=your-cohere-api-key
```

## Usage

### Starting the Server

```bash
# Basic usage
python video_insights_mcp.py

# The server will run with SSE transport at http://localhost:8008/sse

# To use different host/port, set environment variables:
export MCP_HOST=0.0.0.0
export MCP_PORT=8080
python video_insights_mcp.py
```

### MCP Protocol with Strands SDK

The server uses SSE (Server-Sent Events) transport, which is compatible with Strands SDK. The server automatically runs when the module is executed.

### Example Tool Calls

The server provides the following tools that can be called by your Strands agent:

```python
# Search by keywords
result = agent.call_tool("search_videos_by_keywords", {
    "keywords": ["Nike", "marketing"],
    "max_results": 5
})

# Semantic search
result = agent.call_tool("search_videos_by_semantic_query", {
    "query": "videos about construction safety training",
    "use_pegasus_embedding": True
})

# Get video details
result = agent.call_tool("get_video_details", {
    "video_id": "6861409c21f0ea193ed03362",
    "include_transcript": True
})

# Search for person mentions
result = agent.call_tool("search_person_in_video", {
    "video_id": "6861409c21f0ea193ed03362",
    "person_name": "Anderson Cooper"
})
```

## Integration with Strands SDK

This MCP server is designed to work seamlessly with AI agents built using Strands SDK. The LLM-friendly responses ensure that your agent can:

1. Understand search results with clear summaries
2. Access video IDs for follow-up queries
3. Get contextual information for better responses
4. Handle various user query patterns

### Example Agent Queries

- "What videos talk about Nike?"
- "When was Anderson Cooper mentioned in video X?"
- "What's the sentiment of video 6861409c21f0ea193ed03362?"
- "Give me a summary of the latest marketing videos"
- "Find videos about construction training"

## Development

### Adding New Search Functions

1. Define the Pydantic model in the server code
2. Add the tool definition to the `TOOLS` list
3. Implement the search function
4. Add the handler mapping in `handle_call_tool`

### Implementing Embedding Generation

The server includes a placeholder for embedding generation. To implement:

1. Install your preferred embedding provider (Cohere, OpenAI, etc.)
2. Update the `get_embedding_from_text` function
3. Ensure embedding dimensions match your index (1024 for both fields)

### Error Handling

The server includes comprehensive error handling:
- Invalid tool names return appropriate errors
- OpenSearch connection failures are caught and reported
- Missing videos return informative messages
- All errors follow MCP protocol format

## Troubleshooting

### Connection Issues

1. Verify AWS credentials are configured:
   ```bash
   aws configure list
   ```

2. Test OpenSearch connection:
   ```bash
   python run_mcp_server.py --test
   ```

3. Check OpenSearch endpoint format (no https:// prefix)

### Search Issues

1. Verify index exists and has data
2. Check field names match your index mapping
3. Ensure embeddings are properly generated

### Performance

1. Adjust `max_results` for large result sets
2. Use specific search fields instead of searching all
3. Consider caching for frequently accessed videos

## Security Considerations

1. AWS credentials are loaded securely via boto3
2. No credentials are logged or exposed in responses
3. Input validation prevents injection attacks
4. Rate limiting should be implemented for production use

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review server logs for detailed error messages
3. Ensure all environment variables are correctly set