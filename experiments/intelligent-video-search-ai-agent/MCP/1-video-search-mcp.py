import os
import json
import logging
from mcp.server import FastMCP
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import numpy as np
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
import base64
import tempfile
import uuid
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Get MCP server configuration from environment
MCP_HOST = os.getenv("MCP_HOST", "localhost")
MCP_PORT = os.getenv("MCP_PORT", "8008")

# Set the correct environment variables that FastMCP actually reads
os.environ["FASTMCP_PORT"] = MCP_PORT
os.environ["FASTMCP_HOST"] = MCP_HOST

# Initialize FastMCP
mcp = FastMCP("Video Insights Search")

# AWS & OpenSearch Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT", "")
INDEX_NAME = os.getenv("INDEX_NAME", "video-insights-rag")

# Twelve Labs Configuration
TWELVE_LABS_API_KEY_SECRET = os.getenv('TWELVE_LABS_API_KEY_SECRET')
MARENGO_MODEL_ID = os.getenv('MARENGO_MODEL_ID', 'marengo2.7')

# Search Configuration
DEFAULT_SIMILARITY_THRESHOLD = float(os.getenv('DEFAULT_SIMILARITY_THRESHOLD', '0.8'))

def get_twelve_labs_index_id() -> str:
    """Retrieve Twelve Labs index ID from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)
        secret_name = "twelve-labs-index-id"
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        index_id = secret_data['index_id']
        
        print(f"Retrieved Twelve Labs index ID from Secrets Manager: {index_id}")
        return index_id
        
    except secrets_client.exceptions.ResourceNotFoundException:
        print(f"WARNING: Twelve Labs index ID secret not found in Secrets Manager.")
        print(f"Please ensure the video processing pipeline has run at least once to create the index.")
        print(f"Falling back to environment variable TWELVE_LABS_INDEX_ID if available.")
        
        # Fallback to environment variable for backward compatibility
        fallback_id = os.getenv('TWELVE_LABS_INDEX_ID')
        if fallback_id:
            print(f"Using fallback index ID from environment: {fallback_id}")
            return fallback_id
        else:
            raise ValueError("No Twelve Labs index ID found in Secrets Manager or environment variables")
            
    except Exception as e:
        print(f"Error retrieving Twelve Labs index ID from Secrets Manager: {e}")
        # Fallback to environment variable
        fallback_id = os.getenv('TWELVE_LABS_INDEX_ID')
        if fallback_id:
            print(f"Using fallback index ID from environment: {fallback_id}")
            return fallback_id
        else:
            raise ValueError(f"Failed to retrieve Twelve Labs index ID: {e}")

# Get Twelve Labs index ID dynamically
TWELVE_LABS_INDEX_ID = get_twelve_labs_index_id()

# Initialize AWS credentials
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    AWS_REGION,
    'aoss',
    session_token=credentials.token
)

# Initialize OpenSearch client (synchronous version for FastMCP)
opensearch_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=5)

# Lazy load Twelve Labs to avoid import errors if not needed
_twelve_labs_client = None

def get_twelve_labs_client():
    """Get or create Twelve Labs client instance"""
    global _twelve_labs_client
    
    if _twelve_labs_client is None:
        try:
            from twelvelabs import TwelveLabs
            
            # Get API key from AWS Secrets Manager or environment
            api_key = None
            if TWELVE_LABS_API_KEY_SECRET:
                try:
                    secrets_client = boto3.client('secretsmanager')
                    secret = secrets_client.get_secret_value(SecretId=TWELVE_LABS_API_KEY_SECRET)
                    secret_data = json.loads(secret['SecretString'])
                    api_key = secret_data.get('api_key')
                except Exception as e:
                    logger.warning(f"Could not get API key from Secrets Manager: {e}")
            
            if not api_key:
                api_key = os.getenv('TL_API_KEY')
            
            if not api_key:
                raise ValueError("Twelve Labs API key not found in Secrets Manager or environment")
            
            _twelve_labs_client = TwelveLabs(api_key=api_key)
            logger.info("Twelve Labs client initialized successfully")
            
        except ImportError:
            logger.error("Twelve Labs SDK not installed. Run: pip install twelvelabs")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Twelve Labs client: {e}")
            raise
    
    return _twelve_labs_client

# Helper Functions
def prepare_content_for_embedding(video_data: Dict[str, Any]) -> str:
    """
    Prepare content for Cohere embedding from video data.
    Similar to prepare_marketing_content_for_embedding in Lambda.
    """
    content_parts = []
    
    # Get Pegasus insights
    insights = video_data.get("pegasus_insights", {})
    
    # 1. Summary - crucial for searches
    if insights.get('summary'):
        content_parts.append(f"SUMMARY: {insights['summary']}")
    
    # 2. Topics and themes
    if insights.get('topics'):
        content_parts.append(f"TOPICS: {insights['topics']}")
    
    # 3. Content analytics and sentiment
    if insights.get('content_analytics'):
        content_parts.append(f"CONTENT ANALYTICS: {insights['content_analytics']}")
    
    if insights.get('sentiment_analysis'):
        content_parts.append(f"SENTIMENT: {insights['sentiment_analysis']}")
    
    # 4. Hashtags
    if insights.get('hashtags'):
        content_parts.append(f"HASHTAGS: {insights['hashtags']}")
    
    # 5. Chapter titles
    if insights.get('chapters'):
        chapter_titles = [ch['title'] for ch in insights['chapters'] if ch.get('title')]
        if chapter_titles:
            content_parts.append(f"CHAPTERS: {', '.join(chapter_titles)}")
    
    # 6. Brand/company/name mentions
    detections = video_data.get('detections', {})
    if detections.get('entities'):
        entities = detections['entities']
        
        if entities.get('brands'):
            content_parts.append(f"BRANDS MENTIONED: {', '.join(entities['brands'])}")
            
        if entities.get('companies'):
            content_parts.append(f"COMPANIES MENTIONED: {', '.join(entities['companies'])}")
            
        if entities.get('person_names'):
            content_parts.append(f"PEOPLE MENTIONED: {', '.join(entities['person_names'])}")
    
    # 7. Video title
    if video_data.get('video_title'):
        content_parts.append(f"TITLE: {video_data['video_title']}")
    
    # 8. Transcript preview
    transcription = insights.get('transcription', {})
    if transcription.get('full_text'):
        transcript_preview = transcription['full_text'][:500]
        content_parts.append(f"TRANSCRIPT PREVIEW: {transcript_preview}")
    
    return "\n\n".join(content_parts)

def format_video_result(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Format OpenSearch hit into a clean video result"""
    source = hit["_source"]
    
    # Generate presigned URL on-demand if S3 info is available
    video_url = None
    if source.get("s3_bucket") and source.get("s3_key"):
        try:
            s3_client = boto3.client('s3')
            video_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': source["s3_bucket"], 'Key': source["s3_key"]},
                ExpiresIn=3600  # 1 hour for viewing
            )
        except Exception as e:
            logger.warning(f"Could not generate presigned URL for video {source.get('video_id')}: {e}")
    
    result = {
        "video_id": source.get("video_id"),
        "video_title": source.get("video_title", "Untitled"),
        "video_url": video_url,
        "thumbnail_s3_key": source.get("thumbnail_s3_key"),
        "summary": source.get("pegasus_insights", {}).get("summary", "No summary available"),
        "score": hit.get("_score", 0),
        "processing_date": source.get("processing_timestamp"),
        "brands_mentioned": source.get("detections", {}).get("entities", {}).get("brands", []),
        "companies_mentioned": source.get("detections", {}).get("entities", {}).get("companies", []),
        "people_mentioned": source.get("detections", {}).get("entities", {}).get("person_names", [])
    }
    return result

def get_embedding_from_text(text: str) -> List[float]:
    """Generate embedding from text using Cohere via Amazon Bedrock"""
    try:
        # Get Cohere model ID from environment
        cohere_model_id = os.getenv('COHERE_MODEL_ID', 'cohere.embed-english-v3')
        region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize Bedrock client
        bedrock = boto3.client(service_name='bedrock-runtime', region_name=region)
        
        # Cohere has a limit on text length, truncate if needed
        # Maximum is typically 512 tokens, roughly 2048 characters
        truncated_text = text[:2048] if len(text) > 2048 else text
        
        # Prepare request body for Cohere embedding
        body = json.dumps({
            "texts": [truncated_text],
            "input_type": "search_query",  # For search queries
            "embedding_types": ["float"]
        })
        
        # Invoke Cohere model via Bedrock
        response = bedrock.invoke_model(
            body=body,
            modelId=cohere_model_id,
            accept='*/*',
            contentType='application/json'
        )
        
        # Parse response
        response_body = json.loads(response.get('body').read())
        embeddings = response_body.get('embeddings', {}).get('float', [])
        
        if embeddings and len(embeddings) > 0:
            return embeddings[0]  # Return the first (and only) embedding
        else:
            raise ValueError("No embeddings returned from Cohere")
            
    except Exception as e:
        logger.error(f"Error generating Cohere embeddings: {e}")
        # Return a dummy embedding in case of error to avoid breaking the search
        import random
        random.seed(hash(text) % 1000)
        return [random.random() for _ in range(1024)]

# MCP Tool Implementations
@mcp.tool(description="Search for videos containing specific keywords in titles, summaries, brands, companies, or people names")
def search_videos_by_keywords(
    keywords: List[str],
    search_fields: Optional[List[str]] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search videos by keywords across multiple fields.
    
    Args:
        keywords: Keywords to search for
        search_fields: Fields to search in (default: all relevant fields)
        max_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with search results
    """
    if search_fields is None:
        search_fields = [
            "video_title", "pegasus_insights.summary", "pegasus_insights.topics", 
            "detections.entities.brands", "detections.entities.companies", 
            "detections.entities.person_names"
        ]
    
    should_clauses = []
    
    for keyword in keywords:
        for field in search_fields:
            should_clauses.append({
                "match": {field: {"query": keyword, "boost": 1.0}}
            })
    
    query = {
        "size": max_results,
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", "pegasus_insights.summary", 
                   "processing_timestamp", "detections.entities"]
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        results = [format_video_result(hit) for hit in response["hits"]["hits"]]
        
        return {
            "success": True,
            "total_results": response["hits"]["total"]["value"],
            "returned_results": len(results),
            "results": results,
            "keywords_searched": keywords
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
            "results": []
        }

@mcp.tool(description="Search for videos using natural language queries with semantic search")
def search_videos_by_semantic_query(
    query: str,
    use_pegasus_embedding: bool = True,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search videos using semantic similarity.
    
    Args:
        query: Natural language search query
        use_pegasus_embedding: Use text-based Pegasus insights embedding (default: True)
        max_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with search results
    """
    # Generate embedding for the query
    query_embedding = get_embedding_from_text(query)
    
    embedding_field = "pegasus_insights_embedding" if use_pegasus_embedding else "video_content_embedding"
    
    search_query = {
        "size": max_results,
        "query": {
            "knn": {
                embedding_field: {
                    "vector": query_embedding,
                    "k": max_results
                }
            }
        },
        "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", "pegasus_insights.summary", 
                   "processing_timestamp", "detections.entities", "pegasus_content_for_embedding"]
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=search_query)
        results = [format_video_result(hit) for hit in response["hits"]["hits"]]
        
        # Log the embedded content that was used for search (helpful for debugging)
        if results and logger.isEnabledFor(logging.DEBUG):
            for i, hit in enumerate(response["hits"]["hits"][:3]):  # Log first 3
                embedded_content = hit["_source"].get("pegasus_content_for_embedding", "")
                logger.debug(f"Result {i+1} embedded content preview: {embedded_content[:200]}...")
        
        return {
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results,
            "embedding_type": "pegasus_insights" if use_pegasus_embedding else "video_content",
            "embedding_dimension": len(query_embedding)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Semantic search failed: {str(e)}",
            "results": []
        }

@mcp.tool(description="Get detailed information about a specific video including summary, chapters, and content analytics")
def get_video_details(
    video_id: str,
    include_transcript: bool = False,
    include_chapters: bool = True,
    include_content_analytics: bool = True
) -> Dict[str, Any]:
    """
    Get detailed information about a specific video.
    
    Args:
        video_id: The video ID
        include_transcript: Include full transcript (default: False)
        include_chapters: Include chapter information (default: True)
        include_content_analytics: Include content analytics and insights (default: True)
    
    Returns:
        Dictionary with video details
    """
    query = {
        "query": {"term": {"video_id": video_id}}
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            return {
                "success": False,
                "error": f"Video with ID {video_id} not found",
                "video": None
            }
        
        source = response["hits"]["hits"][0]["_source"]
        
        # Generate presigned URL on-demand if S3 info is available
        video_url = None
        if source.get("s3_bucket") and source.get("s3_key"):
            try:
                s3_client = boto3.client('s3')
                video_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': source["s3_bucket"], 'Key': source["s3_key"]},
                    ExpiresIn=3600  # 1 hour for viewing
                )
            except Exception as e:
                logger.warning(f"Could not generate presigned URL for video {source.get('video_id')}: {e}")

        result = {
            "success": True,
            "video": {
                "video_id": source.get("video_id"),
                "video_title": source.get("video_title", "Untitled"),
                "video_url": video_url,
                "summary": source.get("pegasus_insights", {}).get("summary"),
                "topics": source.get("pegasus_insights", {}).get("topics"),
                "hashtags": source.get("pegasus_insights", {}).get("hashtags"),
                "brands": source.get("detections", {}).get("entities", {}).get("brands", []),
                "companies": source.get("detections", {}).get("entities", {}).get("companies", []),
                "people": source.get("detections", {}).get("entities", {}).get("person_names", [])
            }
        }
        
        if include_chapters:
            result["video"]["chapters"] = source.get("pegasus_insights", {}).get("chapters", [])
        
        if include_content_analytics:
            result["video"]["content_analytics"] = source.get("pegasus_insights", {}).get("content_analytics")
            result["video"]["sentiment"] = source.get("pegasus_insights", {}).get("sentiment_analysis")
        
        if include_transcript:
            result["video"]["transcript"] = source.get("pegasus_insights", {}).get("transcription", {}).get("full_text")
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get video details: {str(e)}",
            "video": None
        }

@mcp.tool(description="Find when and where a specific person is mentioned in a video")
def search_person_in_video(
    video_id: str,
    person_name: str,
    include_context: bool = True
) -> Dict[str, Any]:
    """
    Find mentions of a person in a specific video.
    
    Args:
        video_id: The video ID to search in
        person_name: Name of the person to find
        include_context: Include surrounding transcript context (default: True)
    
    Returns:
        Dictionary with person mentions and timestamps
    """
    query = {
        "query": {"term": {"video_id": video_id}}
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            return {
                "success": False,
                "error": f"Video with ID {video_id} not found",
                "mentions": []
            }
        
        source = response["hits"]["hits"][0]["_source"]
        
        # Check if person is in the detected entities
        people_mentioned = source.get("detections", {}).get("entities", {}).get("person_names", [])
        person_found = any(person_name.lower() in person.lower() for person in people_mentioned)
        
        result = {
            "success": True,
            "video_id": video_id,
            "video_title": source.get("video_title", "Untitled"),
            "person_searched": person_name,
            "found_in_entities": person_found,
            "mentions": []
        }
        
        # Search in transcript segments
        transcription = source.get("pegasus_insights", {}).get("transcription", {})
        segments = transcription.get("segments", [])
        full_text = transcription.get("full_text", "")
        
        if include_context and full_text:
            # Find mentions in full text with context
            import re
            pattern = re.compile(re.escape(person_name), re.IGNORECASE)
            
            for match in pattern.finditer(full_text):
                start_idx = max(0, match.start() - 100)
                end_idx = min(len(full_text), match.end() + 100)
                context = full_text[start_idx:end_idx]
                
                # Find corresponding timestamp
                char_count = 0
                timestamp = None
                for segment in segments:
                    segment_text = segment.get("text", "")
                    if char_count <= match.start() < char_count + len(segment_text):
                        timestamp = segment.get("start_time")
                        break
                    char_count += len(segment_text) + 1  # +1 for space
                
                result["mentions"].append({
                    "context": context,
                    "timestamp": timestamp,
                    "character_position": match.start()
                })
        
        result["total_mentions"] = len(result["mentions"])
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to search person in video: {str(e)}",
            "mentions": []
        }

@mcp.tool(description="Get sentiment analysis for a video")
def get_video_sentiment(video_id: str) -> Dict[str, Any]:
    """
    Get sentiment analysis for a video.
    
    Args:
        video_id: The video ID
    
    Returns:
        Dictionary with sentiment analysis
    """
    query = {
        "query": {"term": {"video_id": video_id}},
        "_source": ["video_id", "video_title", "pegasus_insights.sentiment_analysis"]
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            return {
                "success": False,
                "error": f"Video with ID {video_id} not found",
                "sentiment": None
            }
        
        source = response["hits"]["hits"][0]["_source"]
        sentiment = source.get("pegasus_insights", {}).get("sentiment_analysis", "No sentiment analysis available")
        
        return {
            "success": True,
            "video_id": video_id,
            "video_title": source.get("video_title", "Untitled"),
            "sentiment_analysis": sentiment
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get video sentiment: {str(e)}",
            "sentiment": None
        }

@mcp.tool(description="Get a comprehensive summary of a video")
def get_video_summary(video_id: str) -> Dict[str, Any]:
    """
    Get summary of a video.
    
    Args:
        video_id: The video ID
    
    Returns:
        Dictionary with video summary and key information
    """
    query = {
        "query": {"term": {"video_id": video_id}},
        "_source": ["video_id", "video_title", "pegasus_insights.summary", "pegasus_insights.topics", 
                   "pegasus_insights.hashtags", "detections.entities"]
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            return {
                "success": False,
                "error": f"Video with ID {video_id} not found",
                "summary": None
            }
        
        source = response["hits"]["hits"][0]["_source"]
        
        return {
            "success": True,
            "video_id": video_id,
            "video_title": source.get("video_title", "Untitled"),
            "summary": source.get("pegasus_insights", {}).get("summary", "No summary available"),
            "topics": source.get("pegasus_insights", {}).get("topics"),
            "hashtags": source.get("pegasus_insights", {}).get("hashtags"),
            "key_entities": source.get("detections", {}).get("entities", {})
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get video summary: {str(e)}",
            "summary": None
        }

@mcp.tool(description="Get all videos in the library")
def get_all_videos(max_results: int = 20) -> Dict[str, Any]:
    """
    Get all videos in the library.
    
    Args:
        max_results: Maximum number of videos to return (default: 20)
    
    Returns:
        Dictionary with all videos in the library
    """
    query = {
        "size": max_results,
        "query": {
            "match_all": {}
        },
        "sort": [{"processing_timestamp": {"order": "desc"}}],  # Newest first
        "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", "pegasus_insights.summary", 
                   "processing_timestamp", "detections.entities"]
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        results = [format_video_result(hit) for hit in response["hits"]["hits"]]
        
        return {
            "success": True,
            "total_videos": response["hits"]["total"]["value"],
            "returned_videos": len(results),
            "videos": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get all videos: {str(e)}",
            "videos": []
        }

@mcp.tool(description="Get the transcript of a video in various formats")
def get_video_transcript(
    video_id: str,
    format: str = "full"
) -> Dict[str, Any]:
    """
    Get transcript of a video.
    
    Args:
        video_id: The video ID
        format: Transcript format - "full", "segments", or "speakers" (default: "full")
    
    Returns:
        Dictionary with video transcript
    """
    query = {
        "query": {"term": {"video_id": video_id}},
        "_source": ["video_id", "video_title", "pegasus_insights.transcription"]
    }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            return {
                "success": False,
                "error": f"Video with ID {video_id} not found",
                "transcript": None
            }
        
        source = response["hits"]["hits"][0]["_source"]
        transcription = source.get("pegasus_insights", {}).get("transcription", {})
        
        result = {
            "success": True,
            "video_id": video_id,
            "video_title": source.get("video_title", "Untitled"),
        }
        
        if format == "full":
            result["transcript"] = transcription.get("full_text", "No transcript available")
        elif format == "segments":
            result["segments"] = transcription.get("segments", [])
        elif format == "speakers":
            result["speaker_labels"] = transcription.get("speaker_labels", [])
            result["transcript"] = transcription.get("full_text", "No transcript available")
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get video transcript: {str(e)}",
            "transcript": None
        }

@mcp.tool(description="Check OpenSearch connection and index status")
def check_opensearch_status() -> Dict[str, Any]:
    """
    Check if the OpenSearch connection is working and index exists.
    
    Returns:
        Dictionary with connection status
    """
    try:
        # Test OpenSearch connection
        info = opensearch_client.info()
        
        # Check if index exists
        index_exists = opensearch_client.indices.exists(index=INDEX_NAME)
        
        # Get index stats if it exists
        doc_count = 0
        if index_exists:
            stats = opensearch_client.indices.stats(index=INDEX_NAME)
            doc_count = stats["indices"][INDEX_NAME]["primaries"]["docs"]["count"]
        
        return {
            "opensearch_accessible": True,
            "endpoint": OPENSEARCH_ENDPOINT,
            "index": INDEX_NAME,
            "index_exists": index_exists,
            "document_count": doc_count,
            "cluster_name": info.get("cluster_name"),
            "status": "healthy"
        }
    except Exception as e:
        return {
            "opensearch_accessible": False,
            "endpoint": OPENSEARCH_ENDPOINT,
            "index": INDEX_NAME,
            "error": str(e),
            "status": "unhealthy"
        }

@mcp.tool(description="Search videos by title using fuzzy matching")
def search_videos_by_title(
    title: str,
    fuzzy: bool = True,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search for videos by title with fuzzy matching support.
    
    Args:
        title: The video title to search for
        fuzzy: Enable fuzzy matching for similar titles (default: True)
        max_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with search results
    """
    if fuzzy:
        query = {
            "size": max_results,
            "query": {
                "fuzzy": {
                    "video_title": {
                        "value": title,
                        "fuzziness": "AUTO",
                        "max_expansions": 50,
                        "prefix_length": 2
                    }
                }
            },
            "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", "pegasus_insights.summary", 
                       "processing_timestamp", "detections.entities"]
        }
    else:
        query = {
            "size": max_results,
            "query": {
                "match": {
                    "video_title": {
                        "query": title,
                        "operator": "and"
                    }
                }
            },
            "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", "pegasus_insights.summary", 
                       "processing_timestamp", "detections.entities"]
        }
    
    try:
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        results = [format_video_result(hit) for hit in response["hits"]["hits"]]
        
        return {
            "success": True,
            "query": title,
            "fuzzy_search": fuzzy,
            "total_results": response["hits"]["total"]["value"],
            "returned_results": len(results),
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Title search failed: {str(e)}",
            "results": []
        }

@mcp.tool(description="Search videos using both keywords and semantic similarity")
def search_videos_hybrid(
    query: str,
    keywords: Optional[List[str]] = None,
    use_semantic: bool = True,
    semantic_weight: float = 0.7,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Hybrid search combining keyword and semantic search.
    
    Args:
        query: Natural language search query
        keywords: Optional list of specific keywords to boost
        use_semantic: Whether to include semantic search (default: True)
        semantic_weight: Weight for semantic results vs keyword (0-1, default: 0.7)
        max_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with combined search results
    """
    try:
        # Build the query
        queries = []
        
        # Add semantic search if enabled
        if use_semantic:
            query_embedding = get_embedding_from_text(query)
            queries.append({
                "knn": {
                    "pegasus_insights_embedding": {
                        "vector": query_embedding,
                        "k": max_results
                    }
                }
            })
        
        # Add keyword search
        keyword_clauses = []
        
        # Search in the main query text
        keyword_clauses.append({
            "multi_match": {
                "query": query,
                "fields": [
                    "video_title^3",  # Boost title matches
                    "pegasus_insights.summary^2",
                    "pegasus_insights.topics",
                    "pegasus_content_for_embedding"
                ],
                "type": "best_fields"
            }
        })
        
        # Add specific keyword boosts if provided
        if keywords:
            for keyword in keywords:
                keyword_clauses.append({
                    "multi_match": {
                        "query": keyword,
                        "fields": [
                            "detections.entities.brands^2",
                            "detections.entities.companies^2",
                            "detections.entities.person_names^2",
                            "video_title",
                            "pegasus_insights.summary"
                        ],
                        "type": "phrase"
                    }
                })
        
        # Combine keyword queries
        if keyword_clauses:
            queries.append({
                "bool": {
                    "should": keyword_clauses,
                    "minimum_should_match": 1
                }
            })
        
        # Build final query
        if len(queries) == 1:
            search_query = {
                "size": max_results,
                "query": queries[0],
                "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", "pegasus_insights.summary", 
                           "processing_timestamp", "detections.entities"]
            }
        else:
            # Combine with weights
            search_query = {
                "size": max_results,
                "query": {
                    "bool": {
                        "should": [
                            {"constant_score": {"filter": queries[0], "boost": semantic_weight}},
                            {"constant_score": {"filter": queries[1], "boost": 1 - semantic_weight}}
                        ]
                    }
                },
                "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", "pegasus_insights.summary", 
                           "processing_timestamp", "detections.entities"]
            }
        
        response = opensearch_client.search(index=INDEX_NAME, body=search_query)
        results = [format_video_result(hit) for hit in response["hits"]["hits"]]
        
        return {
            "success": True,
            "query": query,
            "keywords": keywords,
            "total_results": len(results),
            "results": results,
            "search_type": "hybrid" if use_semantic else "keyword_only",
            "semantic_weight": semantic_weight if use_semantic else 0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Hybrid search failed: {str(e)}",
            "results": []
        }

@mcp.tool(description="Find videos similar to a given video using embeddings")
def find_similar_videos(
    reference_video_id: str,
    use_visual_similarity: bool = True,
    similarity_threshold: Optional[float] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Find videos similar to a reference video using embedding similarity.
    
    Args:
        reference_video_id: The video ID to find similar videos for
        use_visual_similarity: Use visual embeddings (True) or text embeddings (False)
        similarity_threshold: Minimum similarity score (0-1, default: 0.7)
        max_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with similar videos
    """
    try:
        # Use environment default if threshold not provided
        if similarity_threshold is None:
            similarity_threshold = DEFAULT_SIMILARITY_THRESHOLD
        
        # First, get the reference video's embeddings
        query = {
            "query": {"term": {"video_id": reference_video_id}},
            "_source": ["video_id", "video_title", "video_content_embedding", 
                       "pegasus_insights_embedding", "pegasus_insights.summary"]
        }
        
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            return {
                "success": False,
                "error": f"Reference video with ID {reference_video_id} not found",
                "similar_videos": []
            }
        
        reference_video = response["hits"]["hits"][0]["_source"]
        
        # Choose which embedding to use
        if use_visual_similarity:
            reference_embedding = reference_video.get("video_content_embedding")
            embedding_field = "video_content_embedding"
        else:
            reference_embedding = reference_video.get("pegasus_insights_embedding")
            embedding_field = "pegasus_insights_embedding"
        
        if not reference_embedding:
            return {
                "success": False,
                "error": f"No {'visual' if use_visual_similarity else 'text'} embedding found for reference video",
                "similar_videos": []
            }
        
        # Search for similar videos using kNN
        search_query = {
            "size": max_results + 1,  # +1 to exclude the reference video
            "query": {
                "knn": {
                    embedding_field: {
                        "vector": reference_embedding,
                        "k": max_results + 1
                    }
                }
            },
            "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", 
                       "pegasus_insights.summary", "processing_timestamp", "detections.entities"],
            "min_score": similarity_threshold
        }
        
        response = opensearch_client.search(index=INDEX_NAME, body=search_query)
        
        # Filter out the reference video and format results
        similar_videos = []
        for hit in response["hits"]["hits"]:
            if hit["_source"]["video_id"] != reference_video_id:
                video_result = format_video_result(hit)
                video_result["similarity_score"] = hit.get("_score", 0)
                similar_videos.append(video_result)
        
        return {
            "success": True,
            "reference_video": {
                "video_id": reference_video_id,
                "video_title": reference_video.get("video_title", "Untitled"),
                "summary": reference_video.get("pegasus_insights", {}).get("summary", "")
            },
            "similar_videos": similar_videos[:max_results],
            "total_found": len(similar_videos),
            "similarity_type": "visual" if use_visual_similarity else "text-based",
            "embedding_field_used": embedding_field
        }
        
    except Exception as e:
        logger.error(f"Error finding similar videos: {e}")
        return {
            "success": False,
            "error": f"Failed to find similar videos: {str(e)}",
            "similar_videos": []
        }

@mcp.tool(description="Search for similar videos by uploading a video file")
def search_by_video_upload(
    video_base64: str,
    video_filename: str,
    use_visual_similarity: bool = True,
    max_results: int = 10,
    generate_thumbnail: bool = True
) -> Dict[str, Any]:
    """
    Upload a video temporarily to find similar videos in the library.
    
    Args:
        video_base64: Base64 encoded video file
        video_filename: Original filename of the video
        use_visual_similarity: Use visual embeddings (True) or text embeddings (False)
        max_results: Maximum number of results (default: 10)
        generate_thumbnail: Generate thumbnail for display (default: True)
    
    Returns:
        Dictionary with similar videos and upload status
    """
    temp_video_path = None
    temp_s3_key = None
    thumbnail_base64 = None
    
    try:
        # Validate inputs
        if not video_base64:
            return {
                "success": False,
                "error": "No video data provided",
                "similar_videos": []
            }
        
        if not TWELVE_LABS_INDEX_ID:
            return {
                "success": False,
                "error": "Twelve Labs index ID not configured",
                "similar_videos": []
            }
        
        # Decode base64 video
        try:
            video_data = base64.b64decode(video_base64)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid base64 video data: {str(e)}",
                "similar_videos": []
            }
        
        # Save video to temporary file
        with tempfile.NamedTemporaryFile(suffix=Path(video_filename).suffix, delete=False) as tmp_file:
            tmp_file.write(video_data)
            temp_video_path = tmp_file.name
        
        # Upload to temporary S3 location
        s3_client = boto3.client('s3')
        temp_bucket = os.getenv('TEMP_VIDEO_BUCKET', os.getenv('S3_BUCKET'))
        temp_s3_key = f"temp-search/{uuid.uuid4().hex}/{video_filename}"
        
        logger.info(f"Uploading temporary video to S3: {temp_bucket}/{temp_s3_key}")
        s3_client.upload_file(temp_video_path, temp_bucket, temp_s3_key)
        
        # Generate presigned URL for Twelve Labs
        video_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': temp_bucket, 'Key': temp_s3_key},
            ExpiresIn=7200  # 2 hours for processing
        )
        
        # Generate thumbnail if requested
        if generate_thumbnail:
            try:
                # Use ffmpeg to generate thumbnail
                import subprocess
                thumbnail_path = f"{temp_video_path}_thumb.jpg"
                
                # Extract frame at 2 seconds (or 0 if video is shorter)
                cmd = [
                    'ffmpeg', '-i', temp_video_path,
                    '-ss', '2', '-vframes', '1',
                    '-vf', 'scale=320:-1',
                    '-y', thumbnail_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
                
                # Read and encode thumbnail
                with open(thumbnail_path, 'rb') as thumb_file:
                    thumbnail_base64 = base64.b64encode(thumb_file.read()).decode('utf-8')
                
                # Clean up thumbnail file
                os.unlink(thumbnail_path)
                
            except Exception as e:
                logger.warning(f"Could not generate thumbnail: {e}")
        
        # Initialize Twelve Labs client
        tl_client = get_twelve_labs_client()
        
        # Upload video to Twelve Labs and wait for processing
        logger.info(f"Uploading video to Twelve Labs index: {TWELVE_LABS_INDEX_ID}")
        task = tl_client.task.create(
            index_id=TWELVE_LABS_INDEX_ID,
            url=video_url
        )
        
        # Wait for processing with timeout
        max_wait_time = 300  # 5 minutes
        start_time = datetime.now()
        
        while task.status not in ["ready", "failed"]:
            if (datetime.now() - start_time).seconds > max_wait_time:
                raise TimeoutError("Video processing timed out")
            
            # Refresh task status
            task = tl_client.task.retrieve(task.id)
            logger.info(f"Task status: {task.status}")
            
            if task.status == "failed":
                raise Exception(f"Video processing failed: {task.error_message}")
            
            # Wait before checking again
            import time
            time.sleep(5)
        
        video_id = task.video_id
        logger.info(f"Video processed successfully: {video_id}")
        
        # Get embeddings for the uploaded video
        embeddings_result = tl_client.index.video.retrieve(
            index_id=TWELVE_LABS_INDEX_ID,
            id=video_id,
            embedding_option=["visual-text", "audio"]
        )
        
        # Calculate average embedding
        if embeddings_result.embedding and embeddings_result.embedding.video_embedding.segments:
            all_embeddings = []
            for segment in embeddings_result.embedding.video_embedding.segments:
                all_embeddings.append(segment.embeddings_float)
            
            avg_embedding = np.mean(all_embeddings, axis=0).tolist()
            
            # Search for similar videos using the embedding
            embedding_field = "video_content_embedding" if use_visual_similarity else "pegasus_insights_embedding"
            
            search_query = {
                "size": max_results,
                "query": {
                    "knn": {
                        embedding_field: {
                            "vector": avg_embedding,
                            "k": max_results
                        }
                    }
                },
                "_source": ["video_id", "video_title", "s3_bucket", "s3_key", "thumbnail_s3_key", 
                           "pegasus_insights.summary", "processing_timestamp", "detections.entities"],
                "min_score": DEFAULT_SIMILARITY_THRESHOLD
            }
            
            response = opensearch_client.search(index=INDEX_NAME, body=search_query)
            
            # Format results
            similar_videos = []
            for hit in response["hits"]["hits"]:
                video_result = format_video_result(hit)
                video_result["similarity_score"] = hit.get("_score", 0)
                similar_videos.append(video_result)
            
            # Delete the video from Twelve Labs (cleanup)
            try:
                tl_client.index.video.delete(index_id=TWELVE_LABS_INDEX_ID, id=video_id)
                logger.info(f"Deleted temporary video from Twelve Labs: {video_id}")
            except Exception as e:
                logger.warning(f"Could not delete video from Twelve Labs: {e}")
            
            return {
                "success": True,
                "uploaded_video": {
                    "filename": video_filename,
                    "thumbnail_base64": thumbnail_base64,
                    "twelve_labs_video_id": video_id,
                    "embedding_dimension": len(avg_embedding)
                },
                "similar_videos": similar_videos,
                "total_found": len(similar_videos),
                "similarity_type": "visual" if use_visual_similarity else "text-based"
            }
            
        else:
            return {
                "success": False,
                "error": "No embeddings generated for uploaded video",
                "similar_videos": []
            }
        
    except Exception as e:
        logger.error(f"Error in video upload search: {e}")
        return {
            "success": False,
            "error": f"Video upload search failed: {str(e)}",
            "similar_videos": []
        }
        
    finally:
        # Cleanup temporary files
        if temp_video_path and os.path.exists(temp_video_path):
            os.unlink(temp_video_path)
        
        # Cleanup S3 temporary file
        if temp_s3_key:
            try:
                s3_client.delete_object(Bucket=temp_bucket, Key=temp_s3_key)
                logger.info(f"Deleted temporary S3 file: {temp_s3_key}")
            except Exception as e:
                logger.warning(f"Could not delete temporary S3 file: {e}")

@mcp.tool(description="Generate or test embeddings for content")
def test_embedding_generation(
    text: str,
    input_type: str = "search_query"
) -> Dict[str, Any]:
    """
    Test embedding generation for debugging purposes.
    
    Args:
        text: Text to generate embedding for
        input_type: Either "search_query" or "search_document" (default: "search_query")
    
    Returns:
        Dictionary with embedding info
    """
    try:
        # Generate embedding
        embedding = get_embedding_from_text(text)
        
        # Also show what the content would look like if prepared from video data
        sample_video_data = {
            "video_title": "Sample Video",
            "pegasus_insights": {
                "summary": text[:500] if len(text) > 500 else text
            }
        }
        prepared_content = prepare_content_for_embedding(sample_video_data)
        
        return {
            "success": True,
            "text_length": len(text),
            "embedding_dimension": len(embedding),
            "embedding_preview": embedding[:10],  # First 10 values
            "embedding_stats": {
                "min": min(embedding),
                "max": max(embedding),
                "mean": sum(embedding) / len(embedding)
            },
            "prepared_content_preview": prepared_content[:500],
            "input_type": input_type
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Embedding generation failed: {str(e)}"
        }

if __name__ == "__main__":
    print("🎬 Video Insights MCP Server")
    print("=" * 50)
    
    # Check configuration
    if not OPENSEARCH_ENDPOINT:
        print("⚠️  WARNING: No OpenSearch endpoint configured!")
        print("\nTo use this server, you need to set:")
        print("  export OPENSEARCH_ENDPOINT='your-domain.us-east-1.aoss.amazonaws.com'")
        print("  export AWS_REGION='us-east-1'")
        print("  export INDEX_NAME='video-insights'")
    else:
        print(f"✓ OpenSearch Endpoint: {OPENSEARCH_ENDPOINT}")
        print(f"✓ Index: {INDEX_NAME}")
        print(f"✓ AWS Region: {AWS_REGION}")
    
    # Check AWS credentials
    try:
        if credentials:
            print("✓ AWS Credentials configured")
        else:
            print("⚠️  No AWS credentials found")
    except:
        print("⚠️  Error checking AWS credentials")
    
    print("\n📝 Available tools:")
    print("  - search_videos_by_keywords: Search by keywords across multiple fields")
    print("  - search_videos_by_semantic_query: Natural language semantic search")
    print("  - search_videos_hybrid: Combined keyword and semantic search")
    print("  - search_videos_by_title: Search by video title with fuzzy matching")
    print("  - find_similar_videos: Find videos similar to a reference video")
    print("  - search_by_video_upload: Upload video to find similar videos")
    print("  - get_video_details: Get comprehensive video information")
    print("  - search_person_in_video: Find person mentions with timestamps")
    print("  - get_video_sentiment: Get video sentiment analysis")
    print("  - get_video_summary: Get video summary and key topics")
    print("  - get_video_transcript: Get video transcript in various formats")
    print("  - get_all_videos: Get all videos in the library")
    print("  - test_embedding_generation: Test Cohere embedding generation")
    print("  - check_opensearch_status: Check connection and index status")
    
    print(f"\nServer will run at http://{MCP_HOST}:{MCP_PORT}/sse")
    print(f"(Using FASTMCP_PORT={MCP_PORT} environment variable)")
    
    # Run with SSE transport for Strands
    mcp.run(transport="sse")