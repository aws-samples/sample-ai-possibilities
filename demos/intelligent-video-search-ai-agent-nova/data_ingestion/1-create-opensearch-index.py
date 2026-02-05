# opensearch_setup.py
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3
import json
from typing import Dict, Any, List, Optional

class VideoInsightsIndexManager:
    """Manages OpenSearch index for video insights with flexible schema"""
    
    def __init__(self, collection_endpoint: str, region: str = 'us-east-1'):
        self.region = region
        self.service = 'aoss'
        # Clean the endpoint - remove https:// if present
        self.endpoint = collection_endpoint.replace('https://', '').replace('http://', '')
        self.client = self._create_client()
        
    def _create_client(self) -> OpenSearch:
        """Create authenticated OpenSearch client"""
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, self.region, self.service)
        
        return OpenSearch(
            hosts=[{'host': self.endpoint, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
            timeout=300
        )
    
    def create_video_insights_index(self, index_name: str = 'video-insights-rag') -> Dict[str, Any]:
        """Create index with dual embedding fields for video and Pegasus insights"""
        
        # Dynamic schema with two embedding fields
        index_mapping = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100,
                    "number_of_replicas": 1,
                }
            },
            "mappings": {
                "dynamic_templates": [
                    {
                        "embeddings": {
                            "match": "*_embedding",
                            "mapping": {
                                "type": "knn_vector",
                                "dimension": 3072,  # Nova 2 multimodal embeddings dimensions
                                "method": {
                                    "name": "hnsw",
                                    "space_type": "cosinesimil",
                                    "engine": "nmslib",
                                    "parameters": {
                                        "ef_construction": 128,
                                        "m": 16
                                    }
                                }
                            }
                        }
                    },
                    {
                        "timestamps": {
                            "match": "*_timestamp",
                            "mapping": {"type": "date"}
                        }
                    },
                    {
                        "scores": {
                            "match": "*_score",
                            "mapping": {"type": "float"}
                        }
                    },
                    {
                        "counts": {
                            "match": "*_count",
                            "mapping": {"type": "integer"}
                        }
                    }
                ],
                "properties": {
                    # Core video metadata
                    "video_id": {"type": "keyword"},
                    "video_title": {"type": "text", "analyzer": "standard"},
                    "thumbnail_s3_key": {"type": "keyword"},
                    "s3_bucket": {"type": "keyword"},
                    "s3_key": {"type": "keyword"},
                    "duration_seconds": {"type": "float"},
                    "upload_timestamp": {"type": "date"},
                    "processing_timestamp": {"type": "date"},
                    
                    # First embedding field - for video content (Nova multimodal embeddings)
                    "video_content_embedding": {
                        "type": "knn_vector",
                        "dimension": 3072,  # Nova 2 multimodal embeddings dimension
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16
                            }
                        }
                    },

                    # Second embedding field - for text/insights (Nova multimodal embeddings)
                    "pegasus_insights_embedding": {
                        "type": "knn_vector",
                        "dimension": 3072,  # Nova 2 multimodal embeddings dimension
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16
                            }
                        }
                    },
                    
                    # Text field for Pegasus content that will be embedded
                    "pegasus_content_for_embedding": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    
                    # Flexible Pegasus insights storage
                    "pegasus_insights": {
                        "type": "object",
                        "dynamic": True,  # Allow any Pegasus output
                        "properties": {
                            "summary": {"type": "text"},
                            "topics": {"type": "text"},
                            "hashtags": {"type": "text"},
                            "sentiment_analysis": {"type": "text"},
                            "content_analytics": {"type": "text"},
                            "chapters": {
                                "type": "nested",
                                "properties": {
                                    "start_time": {"type": "float"},
                                    "end_time": {"type": "float"},
                                    "start": {"type": "float"},
                                    "end": {"type": "float"},
                                    "title": {"type": "text"},
                                    "description": {"type": "text"},
                                    "summary": {"type": "text"}
                                }
                            },
                            "transcription": {
                                "type": "object",
                                "properties": {
                                    "full_text": {"type": "text"},
                                    "segments": {
                                        "type": "nested",
                                        "dynamic": True
                                    },
                                    "speaker_labels": {
                                        "type": "nested",
                                        "dynamic": True
                                    }
                                }
                            },
                            "highlights": {
                                "type": "nested",
                                "properties": {
                                    "start": {"type": "float"},
                                    "end": {"type": "float"},
                                    "highlight": {"type": "text"}
                                }
                            }
                        }
                    },
                    
                    # Flexible detection arrays
                    "detections": {
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "object",
                                "properties": {
                                    "brands": {
                                        "type": "text",
                                        "analyzer": "standard",
                                        "fields": {
                                            "keyword": {"type": "keyword"}
                                        }
                                    },
                                    "companies": {
                                        "type": "text",
                                        "analyzer": "standard",
                                        "fields": {
                                            "keyword": {"type": "keyword"}
                                        }
                                    },
                                    "person_names": {
                                        "type": "text",
                                        "analyzer": "standard",
                                        "fields": {
                                            "keyword": {"type": "keyword"}
                                        }
                                    }
                                }
                            }
                        }
                    },              
                    # Audio insights
                    "audio_insights": {
                        "type": "object",
                        "dynamic": True,
                        "properties": {
                            "background_music": {
                                "type": "nested",
                                "dynamic": True
                            },
                            "sound_effects": {"type": "keyword"},
                            "speech_analysis": {
                                "type": "object",
                                "dynamic": True
                            }
                        }
                    },
                    
                    # Scene analysis
                    "scenes": {
                        "type": "nested",
                        "dynamic": True,
                        "properties": {
                            "description": {"type": "text"},
                            "tags": {"type": "keyword"},
                            "timestamp_range": {"type": "object", "dynamic": True}
                        }
                    },
                    
                    # Key moments
                    "key_moments": {
                        "type": "nested",
                        "dynamic": True,
                        "properties": {
                            "type": {"type": "keyword"},
                            "description": {"type": "text"},
                            "timestamp": {"type": "float"},
                            "importance": {"type": "float"}
                        }
                    },
                    
                    # Content metadata for categorization and organization
                    "content_metadata": {
                        "type": "object",
                        "dynamic": True,
                        "properties": {
                            "category": {"type": "keyword"},
                            "tags": {"type": "keyword"},
                            "content_type": {"type": "keyword"},
                            "source": {"type": "keyword"},
                            "custom_fields": {"type": "object", "dynamic": True}
                        }
                    },
                    
                    # Embedding metadata for tracking
                    "embedding_metadata": {
                        "type": "object",
                        "properties": {
                            "video_embedding_model": {"type": "keyword"},
                            "pegasus_embedding_model": {"type": "keyword"},
                            "pegasus_embedding_timestamp": {"type": "date"},
                            "video_embedding_timestamp": {"type": "date"}
                        }
                    }
                }
            }
        }
        
        # Create index
        if self.client.indices.exists(index=index_name):
            print(f"Index {index_name} already exists")
            return {"acknowledged": True, "index": index_name}
            
        response = self.client.indices.create(
            index=index_name,
            body=index_mapping
        )
        print(f"Created index: {index_name}")
        return response

def main():
    """
    Main function with command line argument support
    Usage: python 1-create-opensearch-index.py --endpoint your-endpoint
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create OpenSearch index for video insights RAG pipeline'
    )
    parser.add_argument(
        '--endpoint',
        required=True,
        help='OpenSearch collection endpoint (e.g., abc123.us-east-1.aoss.amazonaws.com)'
    )
    parser.add_argument(
        '--index-name',
        default='video-insights-rag',
        help='Name of the index to create (default: video-insights-rag)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    print(f"Creating OpenSearch index: {args.index_name}")
    print(f"Endpoint: {args.endpoint}")
    print(f"Region: {args.region}")
    
    try:
        manager = VideoInsightsIndexManager(
            collection_endpoint=args.endpoint,
            region=args.region
        )
        
        result = manager.create_video_insights_index(args.index_name)
        
        if result.get('acknowledged'):
            print("✅ Index creation successful!")
            print(f"Index '{args.index_name}' is ready for video ingestion.")
        else:
            print("❌ Index creation failed.")
            print(json.dumps(result, indent=2))
            import sys
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)

# Usage example when run directly
if __name__ == "__main__":
    main()