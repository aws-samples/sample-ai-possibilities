# Video Keeper - Video API Service

> **Fast video metadata API for thumbnail carousel and library browsing**

A lightweight FastAPI service that provides direct access to video metadata and thumbnails from OpenSearch, optimized for rapid library browsing and carousel displays.

## Features

### 🚀 High-Performance Video Access
- **Direct OpenSearch Queries**: Bypasses agent layer for speed
- **Thumbnail Management**: Presigned URL generation for video thumbnails
- **Metadata Retrieval**: Fast access to video titles, summaries, and insights
- **CORS Enabled**: Ready for frontend integration

### 📊 Video Library Management
- **Collection Overview**: Get all videos with pagination support
- **Rich Metadata**: Includes processing timestamps, summaries, and entity data
- **Efficient Queries**: Optimized for frontend carousel requirements
- **Error Handling**: Comprehensive error responses with debugging info

## Quick Start

### Prerequisites
- Python 3.11+
- OpenSearch Serverless collection with video data
- AWS credentials configured

### Installation

```bash
# Navigate to video-api directory
cd video-api/

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your OpenSearch endpoint
# OPENSEARCH_ENDPOINT=your-collection-id.us-east-1.aoss.amazonaws.com
# INDEX_NAME=video-insights-rag

# Start the Video API service
python main.py
```

Service runs at: `http://localhost:8091`

## Configuration

### Required Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1

# OpenSearch Configuration
OPENSEARCH_ENDPOINT=your-collection-id.us-east-1.aoss.amazonaws.com
INDEX_NAME=video-insights-rag

# API Configuration
API_HOST=localhost
API_PORT=8091
```

### Optional Configuration

```bash
# Development settings
DEBUG=false
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## API Endpoints

### Video Library

#### Get All Videos
```bash
GET /videos
```

**Response:**
```json
{
  "success": true,
  "total": 25,
  "videos": [
    {
      "video_id": "abc123def456",
      "video_title": "Python Tutorial - Getting Started",
      "thumbnail_url": "https://s3.amazonaws.com/bucket/thumbnail.jpg",
      "summary": "Comprehensive introduction to Python programming...",
      "score": 1.0,
      "processing_date": "2024-01-01T12:00:00Z",
      "brands_mentioned": ["Python", "VS Code"],
      "companies_mentioned": ["Microsoft"],
      "people_mentioned": ["Guido van Rossum"]
    }
  ]
}
```

**Query Parameters:**
- `limit` (optional): Maximum number of videos to return (default: 20)
- `offset` (optional): Number of videos to skip for pagination
- `sort` (optional): Sort order - "newest", "oldest", "relevance" (default: "newest")

#### Example Usage
```bash
# Get first 10 videos
curl "http://localhost:8091/videos?limit=10"

# Get next 10 videos (pagination)
curl "http://localhost:8091/videos?limit=10&offset=10"

# Get oldest videos first
curl "http://localhost:8091/videos?sort=oldest"
```

### Health Check

#### Service Status
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Video API",
  "version": "1.0.0",
  "opensearch": {
    "connected": true,
    "endpoint": "your-collection.us-east-1.aoss.amazonaws.com",
    "index": "video-insights-rag",
    "document_count": 25
  }
}
```

## Data Processing

### Thumbnail Generation
The service automatically generates presigned URLs for video thumbnails:

- **S3 Integration**: Uses stored `thumbnail_s3_key` from video metadata
- **Secure Access**: Generates temporary URLs with 1-hour expiration
- **Error Handling**: Graceful fallback when thumbnails are unavailable
- **Performance**: URLs generated on-demand for security

### Video Metadata Structure

```json
{
  "video_id": "unique_identifier",
  "video_title": "Human-readable title",
  "thumbnail_url": "presigned_s3_url",
  "summary": "AI-generated summary",
  "score": 1.0,
  "processing_date": "ISO_timestamp",
  "brands_mentioned": ["Brand1", "Brand2"],
  "companies_mentioned": ["Company1", "Company2"],
  "people_mentioned": ["Person1", "Person2"]
}
```

## Frontend Integration

### React Component Example

```typescript
const VideoCarousel: React.FC = () => {
  const [videos, setVideos] = useState<VideoResult[]>([]);
  
  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const response = await fetch('http://localhost:8091/videos');
        const data = await response.json();
        
        if (data.success) {
          setVideos(data.videos);
        }
      } catch (error) {
        console.error('Failed to fetch videos:', error);
      }
    };
    
    fetchVideos();
  }, []);
  
  return (
    <div className="video-carousel">
      {videos.map(video => (
        <VideoThumbnail key={video.video_id} video={video} />
      ))}
    </div>
  );
};
```

### JavaScript Fetch Example

```javascript
// Fetch video library
fetch('http://localhost:8091/videos?limit=20')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log(`Found ${data.total} videos`);
      data.videos.forEach(video => {
        console.log(`${video.video_title}: ${video.summary}`);
      });
    }
  })
  .catch(error => console.error('Error:', error));
```

## Performance Considerations

### Query Optimization
- **Source Field Selection**: Only fetches required fields from OpenSearch
- **Efficient Sorting**: Uses OpenSearch native sorting capabilities
- **Connection Pooling**: Reuses OpenSearch connections for efficiency

### Caching Strategy
- **Presigned URLs**: Generated on-demand with appropriate expiration
- **Response Caching**: Consider implementing Redis for frequently accessed data
- **ETL Patterns**: Optimized for read-heavy workloads

### Scaling Options
- **Horizontal Scaling**: Run multiple instances behind load balancer
- **Database Optimization**: Consider OpenSearch cluster optimization
- **CDN Integration**: Use CloudFront for static thumbnail serving

## Error Handling

### Common Error Responses

**OpenSearch Connection Failed:**
```json
{
  "success": false,
  "error": "Failed to connect to OpenSearch",
  "details": "Connection timeout after 30 seconds",
  "suggestion": "Check OPENSEARCH_ENDPOINT configuration"
}
```

**No Videos Found:**
```json
{
  "success": true,
  "total": 0,
  "videos": [],
  "message": "No videos found in the collection"
}
```

**Invalid Parameters:**
```json
{
  "success": false,
  "error": "Invalid limit parameter",
  "details": "Limit must be between 1 and 100"
}
```

## Development

### Running in Development Mode

```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with auto-reload
python main.py --reload
```

### Testing the API

```bash
# Test health endpoint
curl http://localhost:8091/health

# Test video retrieval
curl http://localhost:8091/videos | jq .

# Test with parameters
curl "http://localhost:8091/videos?limit=5&sort=oldest" | jq .
```

### Adding New Endpoints

1. **Define Route**: Add new FastAPI route with proper type hints
2. **OpenSearch Query**: Implement efficient query patterns
3. **Error Handling**: Add comprehensive error responses
4. **Documentation**: Update this README with new endpoint details

Example:
```python
@app.get("/videos/search")
async def search_videos(q: str, limit: int = 10):
    # Implementation here
    pass
```

## Production Deployment

### Environment Setup
```bash
# Production configuration
ENVIRONMENT=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8091
```

### Security Considerations
- **CORS Configuration**: Restrict origins in production
- **Rate Limiting**: Implement request rate limiting
- **Authentication**: Add API key authentication if needed
- **Input Validation**: Strict parameter validation

### Monitoring
- **Health Checks**: Regular endpoint monitoring
- **OpenSearch Metrics**: Monitor cluster health and query performance
- **Error Tracking**: Log and track API errors
- **Performance Metrics**: Monitor response times and throughput

## Troubleshooting

### Common Issues

**Service Won't Start:**
- Check if port 8091 is available
- Verify OpenSearch endpoint configuration
- Ensure AWS credentials are properly configured

**No Videos Returned:**
- Verify OpenSearch index exists and contains data
- Check if video processing pipeline has run
- Validate index name matches configuration

**Slow Response Times:**
- Monitor OpenSearch cluster performance
- Check network connectivity to OpenSearch
- Consider query optimization or caching

### Debug Commands

```bash
# Check OpenSearch connectivity
python -c "
from opensearchpy import OpenSearch
import os
client = OpenSearch([{'host': os.getenv('OPENSEARCH_ENDPOINT'), 'port': 443}])
print(client.info())
"

# Test video count
curl "http://localhost:8091/health" | jq .opensearch.document_count

# View detailed logs
tail -f video-api.log
```

## Contributing

When contributing to the Video API:
1. Follow FastAPI best practices and type hints
2. Ensure efficient OpenSearch query patterns
3. Add comprehensive error handling
4. Test with various data scenarios
5. Update documentation for new endpoints
6. Consider performance implications of changes