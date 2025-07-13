#!/usr/bin/env python3
"""
Standalone Video API for thumbnail carousel
Direct OpenSearch access for fast video library browsing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
from dotenv import load_dotenv
import os
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT")
INDEX_NAME = os.getenv("INDEX_NAME", "video-insights-rag")

# Validate required environment variables
if not OPENSEARCH_ENDPOINT:
    raise ValueError("OPENSEARCH_ENDPOINT environment variable is required")

# Initialize FastAPI
app = FastAPI(
    title="Video Library API",
    description="Standalone API for video thumbnails and library management",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "*"  # Allow all origins during development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize OpenSearch client
def get_opensearch_client():
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, AWS_REGION, 'aoss')
    
    # Parse hostname from full OpenSearch endpoint URL
    opensearch_host = OPENSEARCH_ENDPOINT.replace('https://', '').replace('http://', '')
    
    return OpenSearch(
        hosts=[{'host': opensearch_host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Video Library API",
        "version": "1.0.0",
        "endpoints": {
            "videos": "/videos - Get all videos for carousel",
            "health": "/health - Health check with OpenSearch status"
        }
    }

@app.get("/health")
async def health_check():
    """Health check with OpenSearch connectivity"""
    try:
        client = get_opensearch_client()
        
        # Test connection with a simple query
        response = client.search(
            index=INDEX_NAME,
            body={"query": {"match_all": {}}, "size": 0}
        )
        
        total_videos = response['hits']['total']['value']
        
        return {
            "status": "healthy",
            "opensearch_connected": True,
            "total_videos": total_videos,
            "index": INDEX_NAME,
            "endpoint": OPENSEARCH_ENDPOINT
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "opensearch_connected": False,
            "error": str(e),
            "index": INDEX_NAME,
            "endpoint": OPENSEARCH_ENDPOINT
        }

@app.get("/videos")
async def get_all_videos(limit: int = 20):
    """
    Get all videos with thumbnails for carousel display
    
    Args:
        limit: Maximum number of videos to return (default: 20)
    
    Returns:
        List of videos with thumbnail URLs and metadata
    """
    try:
        client = get_opensearch_client()
        
        # Query for all videos, sorted by newest first
        query = {
            "size": limit,
            "query": {
                "match_all": {}
            },
            "sort": [{"processing_timestamp": {"order": "desc"}}],
            "_source": [
                "video_id", 
                "video_title", 
                "thumbnail_s3_key", 
                "pegasus_insights.summary",
                "processing_timestamp", 
                "detections.entities.brands",
                "detections.entities.companies", 
                "detections.entities.person_names",
                "s3_bucket",
                "s3_key"
            ]
        }
        
        response = client.search(index=INDEX_NAME, body=query)
        videos = []
        
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            
            # Generate presigned URL for video if needed
            video_url = None
            if source.get("s3_bucket") and source.get("s3_key"):
                try:
                    s3_client = boto3.client('s3')
                    video_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': source["s3_bucket"], 'Key': source["s3_key"]},
                        ExpiresIn=3600  # 1 hour
                    )
                except Exception as e:
                    logger.warning(f"Could not generate presigned URL for video {source.get('video_id')}: {e}")
            
            # Generate presigned URL for thumbnail if available
            thumbnail_url = None
            if source.get("s3_bucket") and source.get("thumbnail_s3_key"):
                try:
                    s3_client = boto3.client('s3')
                    thumbnail_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': source["s3_bucket"], 'Key': source["thumbnail_s3_key"]},
                        ExpiresIn=3600  # 1 hour
                    )
                except Exception as e:
                    logger.warning(f"Could not generate presigned URL for thumbnail {source.get('video_id')}: {e}")
            
            # Format video object
            video = {
                "video_id": source.get("video_id"),
                "video_title": source.get("video_title", "Untitled"),
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "summary": source.get("pegasus_insights", {}).get("summary", "No summary available"),
                "processing_date": source.get("processing_timestamp"),
                "brands_mentioned": source.get("detections", {}).get("entities", {}).get("brands", []),
                "companies_mentioned": source.get("detections", {}).get("entities", {}).get("companies", []),
                "people_mentioned": source.get("detections", {}).get("entities", {}).get("person_names", [])
            }
            
            videos.append(video)
        
        return {
            "success": True,
            "videos": videos,
            "total": len(videos),
            "total_in_database": response["hits"]["total"]["value"]
        }
        
    except Exception as e:
        logger.error(f"Error fetching videos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch videos: {str(e)}"
        )

@app.get("/videos/{video_id}")
async def get_video_details(video_id: str):
    """
    Get detailed information for a specific video
    
    Args:
        video_id: The video ID to get details for
    
    Returns:
        Detailed video information
    """
    try:
        client = get_opensearch_client()
        
        query = {
            "query": {"term": {"video_id": video_id}},
            "_source": ["*"]  # Get all fields for detailed view
        }
        
        response = client.search(index=INDEX_NAME, body=query)
        
        if response["hits"]["total"]["value"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Video with ID {video_id} not found"
            )
        
        source = response["hits"]["hits"][0]["_source"]
        
        return {
            "success": True,
            "video": source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching video {video_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch video details: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    # Configuration
    host = os.getenv("API_HOST", "localhost")
    port = int(os.getenv("API_PORT", "8091"))
    
    print(f"🎬 Starting Video Library API...")
    print(f"📡 Server: http://{host}:{port}")
    print(f"🗄️  OpenSearch: {OPENSEARCH_ENDPOINT}")
    print(f"📊 Index: {INDEX_NAME}")
    print(f"🌍 Region: {AWS_REGION}")
    
    uvicorn.run(
        "1-video-api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )