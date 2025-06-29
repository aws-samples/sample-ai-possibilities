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
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "video-insights")

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
    
    # 3. Marketing metrics and sentiment
    if insights.get('marketing_metrics'):
        content_parts.append(f"MARKETING METRICS: {insights['marketing_metrics']}")
    
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
        "_source": ["video_id", "video_title", "video_url", "pegasus_insights.summary", 
                   "processing_timestamp", "detections.entities"]
    }
    
    try:
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=query)
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
        "_source": ["video_id", "video_title", "video_url", "pegasus_insights.summary", 
                   "processing_timestamp", "detections.entities", "pegasus_content_for_embedding"]
    }
    
    try:
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=search_query)
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

@mcp.tool(description="Get detailed information about a specific video including summary, chapters, and marketing metrics")
def get_video_details(
    video_id: str,
    include_transcript: bool = False,
    include_chapters: bool = True,
    include_marketing_metrics: bool = True
) -> Dict[str, Any]:
    """
    Get detailed information about a specific video.
    
    Args:
        video_id: The video ID
        include_transcript: Include full transcript (default: False)
        include_chapters: Include chapter information (default: True)
        include_marketing_metrics: Include marketing metrics (default: True)
    
    Returns:
        Dictionary with video details
    """
    query = {
        "query": {"term": {"video_id": video_id}}
    }
    
    try:
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            return {
                "success": False,
                "error": f"Video with ID {video_id} not found",
                "video": None
            }
        
        source = response["hits"]["hits"][0]["_source"]
        
        result = {
            "success": True,
            "video": {
                "video_id": source.get("video_id"),
                "video_title": source.get("video_title", "Untitled"),
                "video_url": source.get("video_url"),
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
        
        if include_marketing_metrics:
            result["video"]["marketing_metrics"] = source.get("pegasus_insights", {}).get("marketing_metrics")
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
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=query)
        
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
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=query)
        
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
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=query)
        
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
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=query)
        
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
        index_exists = opensearch_client.indices.exists(index=OPENSEARCH_INDEX)
        
        # Get index stats if it exists
        doc_count = 0
        if index_exists:
            stats = opensearch_client.indices.stats(index=OPENSEARCH_INDEX)
            doc_count = stats["indices"][OPENSEARCH_INDEX]["primaries"]["docs"]["count"]
        
        return {
            "opensearch_accessible": True,
            "endpoint": OPENSEARCH_ENDPOINT,
            "index": OPENSEARCH_INDEX,
            "index_exists": index_exists,
            "document_count": doc_count,
            "cluster_name": info.get("cluster_name"),
            "status": "healthy"
        }
    except Exception as e:
        return {
            "opensearch_accessible": False,
            "endpoint": OPENSEARCH_ENDPOINT,
            "index": OPENSEARCH_INDEX,
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
            "_source": ["video_id", "video_title", "video_url", "pegasus_insights.summary", 
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
            "_source": ["video_id", "video_title", "video_url", "pegasus_insights.summary", 
                       "processing_timestamp", "detections.entities"]
        }
    
    try:
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=query)
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
                "_source": ["video_id", "video_title", "video_url", "pegasus_insights.summary", 
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
                "_source": ["video_id", "video_title", "video_url", "pegasus_insights.summary", 
                           "processing_timestamp", "detections.entities"]
            }
        
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=search_query)
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
        print("  export OPENSEARCH_INDEX='video-insights'")
    else:
        print(f"✓ OpenSearch Endpoint: {OPENSEARCH_ENDPOINT}")
        print(f"✓ Index: {OPENSEARCH_INDEX}")
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
    print("  - get_video_details: Get comprehensive video information")
    print("  - search_person_in_video: Find person mentions with timestamps")
    print("  - get_video_sentiment: Get video sentiment analysis")
    print("  - get_video_summary: Get video summary and key topics")
    print("  - get_video_transcript: Get video transcript in various formats")
    print("  - test_embedding_generation: Test Cohere embedding generation")
    print("  - check_opensearch_status: Check connection and index status")
    
    print(f"\nServer will run at http://{MCP_HOST}:{MCP_PORT}/sse")
    print(f"(Using FASTMCP_PORT={MCP_PORT} environment variable)")
    
    # Run with SSE transport for Strands
    mcp.run(transport="sse")