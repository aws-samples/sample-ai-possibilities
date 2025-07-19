# Video Keeper - MCP Server

> **Model Context Protocol server for intelligent video search and analysis**

A FastMCP-based server that provides AI agents with comprehensive video search capabilities across Amazon OpenSearch Serverless. Designed for use with AWS Strands SDK agents, enabling natural conversation about video content.

## Features

### Core Search Tools

1. **🔍 Keyword Search** (`search_videos_by_keywords`)
   - Multi-field search across titles, summaries, entities, and transcripts
   - Customizable field selection for targeted searches
   - Boolean query matching with relevance scoring

2. **🧠 Semantic Search** (`search_videos_by_semantic_query`)
   - Natural language understanding using Cohere embeddings
   - Vector similarity search in high-dimensional space
   - Context-aware matching beyond exact keywords

3. **🔀 Hybrid Search** (`search_videos_hybrid`)
   - Combines keyword and semantic search intelligently
   - Configurable weighting between search methods
   - Best-of-both-worlds accuracy

4. **📝 Title Search** (`search_videos_by_title`)
   - Fuzzy matching for typo tolerance
   - Exact match option for precise searches
   - Optimized for video name searches

### Video Analysis Tools

5. **📋 Video Details** (`get_video_details`)
   - Comprehensive metadata, summaries, and insights
   - Optional transcript and content analytics
   - Entity detection (people, brands, objects)

6. **👤 Person Search** (`search_person_in_video`)
   - Find specific person mentions with timestamps
   - Context-aware search with surrounding text
   - Perfect for meeting recordings and interviews

7. **💭 Sentiment Analysis** (`get_video_sentiment`)
   - Emotional tone analysis for video content
   - Useful for content categorization and filtering

8. **📄 Video Summary** (`get_video_summary`)
   - AI-generated summaries and key topics
   - Hashtag extraction and entity mentions
   - Quick content overview

9. **🎤 Transcript Access** (`get_video_transcript`)
   - Full transcript, segmented, or speaker-labeled formats
   - Timestamp-aligned text for precise navigation

### Advanced Features

10. **🎯 Video Similarity** (`find_similar_videos`)
    - Find videos similar to a reference video
    - Visual or text-based similarity matching
    - Configurable similarity thresholds

11. **📤 Video Upload Search** (`search_by_video_upload`)
    - Upload a video to find similar content in library
    - Temporary processing with automatic cleanup
    - Visual similarity matching

12. **📚 Library Management** (`get_all_videos`)
    - Retrieve entire video collection with metadata
    - Pagination support for large libraries
    - Sorted by relevance or date

## Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured with OpenSearch access
- OpenSearch Serverless collection with video data

### Installation

```bash
# Navigate to MCP directory
cd MCP/

# Install dependencies (from project root)
pip install -r ../requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
# OPENSEARCH_ENDPOINT=your-collection-id.us-east-1.aoss.amazonaws.com
# OPENSEARCH_INDEX=video-insights-rag

# Start the MCP server
python 1-video-search-mcp.py
```

Server runs at: `http://localhost:8008/sse`

## Configuration

### Required Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1

# OpenSearch Configuration  
OPENSEARCH_ENDPOINT=your-collection-id.us-east-1.aoss.amazonaws.com
OPENSEARCH_INDEX=video-insights-rag

# Twelve Labs (for video upload search)
TWELVE_LABS_API_KEY_SECRET=twelve-labs-api-key
TWELVE_LABS_INDEX_ID=your_index_id
```

### Optional Configuration

```bash
# MCP Server Settings
MCP_HOST=localhost
MCP_PORT=8008

# Search Configuration
DEFAULT_SIMILARITY_THRESHOLD=0.8
TEXT_TRUNCATE_LENGTH=2048

# AI Model Settings
COHERE_MODEL_ID=cohere.embed-english-v3
MARENGO_MODEL_ID=marengo2.7
```

## Usage with AI Agents

### Strands SDK Integration

```python
from strands.tools.mcp import MCPClient
from mcp.client.sse import sse_client

# Create MCP client
mcp_client = MCPClient(lambda: sse_client("http://localhost:8008/sse"))

# List available tools
with mcp_client:
    tools = mcp_client.list_tools_sync()
    for tool in tools:
        print(f"Tool: {tool.tool_name}")
```

### Example Tool Calls

**Semantic Search:**
```python
result = mcp_client.call_tool_sync(
    "search_1",
    "search_videos_by_semantic_query", 
    {"query": "Find videos about Python programming", "max_results": 5}
)
```

**Person Search:**
```python
result = mcp_client.call_tool_sync(
    "person_search_1",
    "search_person_in_video",
    {"video_id": "abc123", "person_name": "John Smith"}
)
```

**Video Upload Search:**
```python
import base64

with open("sample_video.mp4", "rb") as f:
    video_base64 = base64.b64encode(f.read()).decode()

result = mcp_client.call_tool_sync(
    "upload_search_1",
    "search_by_video_upload",
    {
        "video_base64": video_base64,
        "video_filename": "sample_video.mp4",
        "use_visual_similarity": True
    }
)
```

## Tool Reference

### Search Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search_videos_by_keywords` | Multi-field keyword search | `keywords`, `search_fields`, `max_results` |
| `search_videos_by_semantic_query` | Natural language search | `query`, `use_pegasus_embedding`, `max_results` |
| `search_videos_hybrid` | Combined keyword + semantic | `query`, `keywords`, `semantic_weight` |
| `search_videos_by_title` | Title-specific search | `title`, `fuzzy`, `max_results` |

### Analysis Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_video_details` | Complete video information | `video_id`, `include_transcript`, `include_chapters` |
| `search_person_in_video` | Find person mentions | `video_id`, `person_name`, `include_context` |
| `get_video_sentiment` | Sentiment analysis | `video_id` |
| `get_video_summary` | Quick summary | `video_id` |
| `get_video_transcript` | Transcript access | `video_id`, `format` |

### Advanced Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `find_similar_videos` | Find similar content | `reference_video_id`, `use_visual_similarity` |
| `search_by_video_upload` | Upload and find similar | `video_base64`, `video_filename` |
| `get_all_videos` | Library overview | `max_results` |

## Data Schema

### Video Document Structure

```json
{
  "video_id": "unique_identifier",
  "video_title": "Human-readable title",
  "thumbnail_s3_key": "s3/path/to/thumbnail.jpg",
  "s3_bucket": "video-storage-bucket",
  "s3_key": "videos/video.mp4",
  "processing_timestamp": "2024-01-01T00:00:00Z",
  
  "pegasus_insights": {
    "summary": "AI-generated summary",
    "topics": "Main topics and themes",
    "hashtags": "#tag1 #tag2",
    "sentiment_analysis": "positive/negative/neutral",
    "content_analytics": "Key metrics and insights",
    "chapters": [
      {
        "start": 0.0,
        "end": 30.0,
        "title": "Introduction",
        "summary": "Chapter summary"
      }
    ],
    "transcription": {
      "full_text": "Complete transcript",
      "segments": [
        {
          "start_time": 0.0,
          "end_time": 5.0,
          "text": "Segment text"
        }
      ]
    }
  },
  
  "detections": {
    "entities": {
      "brands": ["Brand1", "Brand2"],
      "companies": ["Company1", "Company2"], 
      "person_names": ["Person1", "Person2"]
    }
  },
  
  "video_content_embedding": [/* 1024-dim vector */],
  "pegasus_insights_embedding": [/* 1024-dim vector */]
}
```

## Error Handling

The server provides comprehensive error handling:

- **Connection Errors**: Automatic retry with exponential backoff
- **Authentication Failures**: Clear error messages with troubleshooting steps
- **Query Errors**: Validation and helpful error responses
- **Timeout Handling**: Configurable timeouts for long-running operations

Common error responses:

```json
{
  "success": false,
  "error": "Video with ID abc123 not found",
  "results": []
}
```

## Performance Optimization

### Search Performance
- Vector searches use OpenSearch's HNSW algorithm
- Configurable similarity thresholds to filter irrelevant results
- Field selection to reduce query overhead

### Memory Management
- Text truncation for large transcripts
- Streaming responses for large result sets
- Automatic cleanup of temporary resources

### Caching
- OpenSearch handles query caching automatically
- Client-side connection pooling
- Embedding cache for repeated queries

## Troubleshooting

### Common Issues

**Connection Refused**
```bash
# Check if server is running
curl http://localhost:8008/health

# Verify OpenSearch connectivity
python -c "from opensearchpy import OpenSearch; print('Connected')"
```

**No Search Results**
- Verify OpenSearch index exists and has data
- Check if embeddings are properly generated
- Validate query syntax and parameters

**Slow Performance**
- Monitor OpenSearch cluster health
- Check vector index configuration
- Consider similarity threshold adjustments

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python 1-video-search-mcp.py
```

### Health Check

The server provides a health check endpoint:
```bash
curl http://localhost:8008/health
```

Expected response:
```json
{
  "status": "healthy",
  "opensearch_connected": true,
  "tools_loaded": 12
}
```

## Development

### Adding New Tools

1. Define the tool function with proper type hints
2. Add MCP tool decorator with description
3. Implement error handling and validation
4. Update this documentation

Example:
```python
@mcp.tool(description="Search videos by custom criteria")
def search_videos_custom(criteria: str, max_results: int = 10) -> Dict[str, Any]:
    # Implementation here
    pass
```

### Testing

Run the test suite:
```bash
# Test basic functionality
python -c "
import sys; sys.path.append('.'); 
from video_insights_mcp import *; 
print('MCP server basic test passed')
"
```

## Contributing

When contributing to the MCP server:
1. Follow Python type hints and docstring conventions
2. Add comprehensive error handling
3. Update tool descriptions and documentation
4. Test with various query types and edge cases
5. Consider performance implications of new features