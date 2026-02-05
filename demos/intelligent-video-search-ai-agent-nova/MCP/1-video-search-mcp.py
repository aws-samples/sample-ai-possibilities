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
PRIMARY_REGION = os.getenv("PRIMARY_REGION", "us-east-1")  # All Nova 2 models in us-east-1
AWS_REGION = PRIMARY_REGION
OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT", "")
INDEX_NAME = os.getenv("INDEX_NAME", "video-insights-rag")

# Nova 2 Model Configuration (all in us-east-1)
NOVA_EMBEDDING_MODEL_ID = os.getenv('NOVA_EMBEDDING_MODEL_ID', 'amazon.nova-2-multimodal-embeddings-v1:0')
NOVA_OMNI_MODEL_ID = os.getenv('NOVA_OMNI_MODEL_ID', 'global.amazon.nova-2-omni-v1:0')
NOVA_EMBEDDING_DIMENSION = int(os.getenv('NOVA_EMBEDDING_DIMENSION', '3072'))
VIDEO_BUCKET = os.getenv('VIDEO_BUCKET', os.getenv('S3_BUCKET'))  # Primary bucket in us-east-1

# Search Configuration
DEFAULT_SIMILARITY_THRESHOLD = float(os.getenv('DEFAULT_SIMILARITY_THRESHOLD', '0.8'))

def get_bedrock_config() -> Dict[str, str]:
    """Get Nova 2 model configuration from environment variables"""
    config = {
        'nova_embedding_model_id': NOVA_EMBEDDING_MODEL_ID,
        'nova_omni_model_id': NOVA_OMNI_MODEL_ID,
        'embedding_dimension': NOVA_EMBEDDING_DIMENSION,
        'region': PRIMARY_REGION,
        'video_bucket': VIDEO_BUCKET,
        'using_nova': True
    }

    # Validate required configuration
    if not config['video_bucket']:
        raise ValueError("VIDEO_BUCKET environment variable not set.")

    logger.info(f"Using Nova config: {config}")
    return config

# Get Nova configuration
BEDROCK_CONFIG = get_bedrock_config()

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

# Bedrock clients for cross-region TwelveLabs models
_bedrock_clients = None

def get_bedrock_clients():
    """Get or create Bedrock client instances for Nova 2 models"""
    global _bedrock_clients

    if _bedrock_clients is None:
        try:
            config = BEDROCK_CONFIG

            _bedrock_clients = {
                'bedrock_runtime': boto3.client('bedrock-runtime', region_name=config['region']),
                's3_client': boto3.client('s3'),
                'config': config
            }

            logger.info("Bedrock clients initialized successfully for Nova 2 models")

        except Exception as e:
            logger.error(f"Failed to initialize Bedrock clients: {e}")
            raise

    return _bedrock_clients

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
    """Generate embedding from text using Nova 2 Multimodal Embeddings"""
    try:
        clients = get_bedrock_clients()
        bedrock = clients['bedrock_runtime']

        # Nova has larger token limit but we still truncate very long texts
        truncated_text = text[:8000] if len(text) > 8000 else text

        # Prepare request body for Nova embedding
        request_body = {
            'taskType': 'SINGLE_EMBEDDING',
            'singleEmbeddingParams': {
                'embeddingPurpose': 'SEARCH',  # For search queries
                'embeddingDimension': NOVA_EMBEDDING_DIMENSION,
                'text': {
                    'truncationMode': 'END',
                    'value': truncated_text
                },
            },
        }

        # Invoke Nova embedding model
        response = bedrock.invoke_model(
            body=json.dumps(request_body),
            modelId=NOVA_EMBEDDING_MODEL_ID,
            accept='application/json',
            contentType='application/json'
        )

        # Parse response - Nova 2 returns embeddings array with objects
        response_body = json.loads(response.get('body').read())
        embeddings_data = response_body.get('embeddings', [])
        embedding = embeddings_data[0].get('embedding', []) if embeddings_data else []

        if embedding and len(embedding) > 0:
            return embedding
        else:
            raise ValueError("No embedding returned from Nova")

    except Exception as e:
        logger.error(f"Error generating Nova embeddings: {e}")
        # Return a dummy embedding in case of error to avoid breaking the search
        import random
        random.seed(hash(text) % 1000)
        return [random.random() for _ in range(NOVA_EMBEDDING_DIMENSION)]

def generate_video_embedding_from_s3(video_s3_uri: str, video_bucket: str) -> List[float]:
    """Generate video embedding using Nova 2 Multimodal Embeddings"""
    try:
        clients = get_bedrock_clients()
        bedrock_client = clients['bedrock_runtime']

        # Determine video format from URI
        video_format = video_s3_uri.split('.')[-1].lower()
        if video_format not in ['mp4', 'mov', 'mkv', 'webm', 'flv', 'mpeg', 'mpg', 'wmv', '3gp']:
            video_format = 'mp4'

        # Create output S3 path for embeddings
        invocation_id = f"search-{uuid.uuid4().hex[:8]}"
        output_s3_uri = f"s3://{video_bucket}/temp-embeddings/{invocation_id}/"

        logger.info(f"Starting Nova embedding generation for: {video_s3_uri}")

        # Prepare model input for Nova embeddings
        model_input = {
            'taskType': 'SEGMENTED_EMBEDDING',
            'segmentedEmbeddingParams': {
                'embeddingPurpose': 'SEARCH',
                'embeddingDimension': NOVA_EMBEDDING_DIMENSION,
                'video': {
                    'format': video_format,
                    'embeddingMode': 'AUDIO_VIDEO_COMBINED',  # Only valid mode for Nova 2
                    'source': {
                        's3Location': {'uri': video_s3_uri}
                    },
                    'segmentationConfig': {
                        'durationSeconds': 15
                    },
                },
            },
        }

        # Start async invocation
        response = bedrock_client.start_async_invoke(
            modelId=NOVA_EMBEDDING_MODEL_ID,
            modelInput=model_input,
            outputDataConfig={
                's3OutputDataConfig': {
                    's3Uri': output_s3_uri
                }
            }
        )

        invocation_arn = response['invocationArn']
        logger.info(f"Started async invocation: {invocation_arn}")

        # Wait for completion
        import time
        max_wait_time = 300  # 5 minutes
        check_interval = 5
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            status_response = bedrock_client.get_async_invoke(invocationArn=invocation_arn)
            status = status_response['status']

            if status == 'Completed':
                logger.info("Nova embedding generation completed")

                # Download and parse results
                s3_client = clients['s3_client']
                s3_prefix = output_s3_uri.replace(f"s3://{video_bucket}/", "")

                response = s3_client.list_objects_v2(Bucket=video_bucket, Prefix=s3_prefix)

                if 'Contents' in response:
                    embeddings_list = []
                    all_files = [obj['Key'] for obj in response['Contents']]
                    logger.info(f"Found {len(all_files)} files in embedding output: {all_files}")

                    for obj in response['Contents']:
                        key = obj['Key']

                        # Skip manifest/result files
                        if 'manifest' in key.lower() or 'result.json' in key.lower():
                            continue

                        # Handle JSONL files (Nova 2 async output format)
                        if key.endswith('.jsonl'):
                            logger.info(f"Processing JSONL file: {key}")
                            obj_response = s3_client.get_object(Bucket=video_bucket, Key=key)
                            content = obj_response['Body'].read().decode('utf-8')

                            # Parse each line as separate JSON object
                            for line in content.strip().split('\n'):
                                if not line.strip():
                                    continue
                                try:
                                    segment_data = json.loads(line)
                                    if segment_data.get('status') == 'FAILURE':
                                        continue
                                    embedding_vector = segment_data.get('embedding', [])
                                    if embedding_vector:
                                        embeddings_list.append(embedding_vector)
                                except json.JSONDecodeError:
                                    pass

                        # Handle regular JSON files (fallback)
                        elif key.endswith('.json'):
                            obj_response = s3_client.get_object(Bucket=video_bucket, Key=key)
                            embeddings_content = obj_response['Body'].read().decode('utf-8')
                            embeddings_data = json.loads(embeddings_content)

                            # Parse embeddings from Nova output
                            if 'segments' in embeddings_data:
                                for segment in embeddings_data['segments']:
                                    if 'embedding' in segment:
                                        embeddings_list.append(segment['embedding'])
                            elif 'embeddings' in embeddings_data:
                                for item in embeddings_data['embeddings']:
                                    if 'embedding' in item:
                                        embeddings_list.append(item['embedding'])
                            elif 'embedding' in embeddings_data:
                                embeddings_list.append(embeddings_data['embedding'])

                    logger.info(f"Parsed {len(embeddings_list)} embedding segments")

                    if embeddings_list:
                        # Return average embedding
                        avg_embedding = np.mean(embeddings_list, axis=0).tolist()

                        # Cleanup temp files
                        try:
                            for obj in response['Contents']:
                                s3_client.delete_object(Bucket=video_bucket, Key=obj['Key'])
                        except:
                            pass

                        return avg_embedding

                raise Exception("No valid embeddings found in Nova output")

            elif status == 'Failed':
                error_msg = status_response.get('failureMessage', 'Unknown error')
                raise Exception(f"Nova invocation failed: {error_msg}")

            time.sleep(check_interval)
            elapsed_time += check_interval

        raise Exception("Nova embedding generation timed out")

    except Exception as e:
        logger.error(f"Failed to generate video embeddings: {e}")
        raise

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
    Upload a video temporarily to find similar videos in the library using Bedrock models.
    
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
        clients = get_bedrock_clients()
        s3_client = clients['s3_client']
        temp_bucket = BEDROCK_CONFIG['video_bucket']
        temp_s3_key = f"temp-search/{uuid.uuid4().hex}/{video_filename}"
        
        logger.info(f"Uploading temporary video to S3: {temp_bucket}/{temp_s3_key}")
        s3_client.upload_file(temp_video_path, temp_bucket, temp_s3_key)
        
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
        
        # Generate video embedding using Nova Multimodal Embeddings
        video_s3_uri = f"s3://{temp_bucket}/{temp_s3_key}"
        logger.info("Generating video embedding with Nova Multimodal Embeddings...")
        
        try:
            video_embedding = generate_video_embedding_from_s3(video_s3_uri, temp_bucket)
            
            # Search for similar videos using the embedding
            embedding_field = "video_content_embedding" if use_visual_similarity else "pegasus_insights_embedding"
            
            search_query = {
                "size": max_results,
                "query": {
                    "knn": {
                        embedding_field: {
                            "vector": video_embedding,
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
            
            return {
                "success": True,
                "uploaded_video": {
                    "filename": video_filename,
                    "thumbnail_base64": thumbnail_base64,
                    "embedding_dimension": len(video_embedding)
                },
                "similar_videos": similar_videos,
                "total_found": len(similar_videos),
                "similarity_type": "visual" if use_visual_similarity else "text-based"
            }
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return {
                "success": False,
                "error": f"Failed to generate video embeddings: {str(e)}",
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
                clients = get_bedrock_clients()
                s3_client = clients['s3_client']
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
        print(f"✓ Using Nova 2 Models:")
        print(f"  - Nova Embeddings: {NOVA_EMBEDDING_MODEL_ID} ({NOVA_EMBEDDING_DIMENSION}D)")
        print(f"  - Nova Omni: {NOVA_OMNI_MODEL_ID}")
    
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
    print("  - search_by_video_upload: Upload video to find similar videos (Bedrock)")
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