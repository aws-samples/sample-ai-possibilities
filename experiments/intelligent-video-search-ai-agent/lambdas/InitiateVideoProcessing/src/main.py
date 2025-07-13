import json
import boto3
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

# Import Twelve Labs SDK
from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task
import twelvelabs

# Import OpenSearch
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Import thumbnail generator
try:
    from generate_thumbnail import ThumbnailGenerator
except ImportError:
    # For local testing without the module
    ThumbnailGenerator = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration from environment variables
TWELVE_LABS_API_KEY_SECRET = os.environ.get('TWELVE_LABS_API_KEY_SECRET')
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'video-insights-rag')
REGION = os.environ.get('REGION', 'us-east-1')

@dataclass
class VideoProcessingConfig:
    """Configuration for video processing with SDK"""
    twelve_labs_index_id: Optional[str] = None
    marengo_model: str = "marengo2.7"
    pegasus_model: str = "pegasus1.2"
    model_options: List[str] = None
    
    def __post_init__(self):
        if self.model_options is None:
            self.model_options = ["visual", "audio"]

class TwelveLabsSDKClient:
    """Enhanced client wrapper for Twelve Labs SDK operations"""
    
    def __init__(self, api_key: str):
        self.client = TwelveLabs(api_key=api_key)
        self.logger = logging.getLogger(__name__)
    
    def create_index_if_needed(self, index_name: str, config: VideoProcessingConfig) -> str:
        """Create or get existing Twelve Labs index using SDK"""
        try:
            # Check existing indexes using SDK
            indexes = self.client.index.list()
            for index in indexes:
                if index.name == index_name:
                    self.logger.info(f"Found existing index: {index.id}")
                    return index.id
            
            # Create new index using SDK
            index = self.client.index.create(
                name=index_name,
                models=[
                    {
                        "name": config.marengo_model,
                        "options": config.model_options
                    },
                    {
                        "name": config.pegasus_model,
                        "options": config.model_options
                    }
                ]
            )
            
            self.logger.info(f"Created new index: {index.id}")
            return index.id
            
        except twelvelabs.APIStatusError as e:
            self.logger.error(f"Index creation failed: {e}")
            raise

def get_twelve_labs_client() -> TwelveLabsSDKClient:
    """Get authenticated Twelve Labs SDK client"""
    if TWELVE_LABS_API_KEY_SECRET:
        secrets_client = boto3.client('secretsmanager')
        secret = secrets_client.get_secret_value(SecretId=TWELVE_LABS_API_KEY_SECRET)
        secret_data = json.loads(secret['SecretString'])
        api_key = secret_data['api_key']
    else:
        api_key = os.environ.get('TL_API_KEY')
    
    if not api_key:
        raise ValueError("Twelve Labs API key not found")
    
    return TwelveLabsSDKClient(api_key)

def check_opensearch_index() -> bool:
    """Check if OpenSearch index exists and is accessible"""
    try:
        if not OPENSEARCH_ENDPOINT:
            raise ValueError("OpenSearch endpoint not configured")
        
        # Get AWS credentials for authentication
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, REGION, 'aoss')
        
        # Parse hostname from full OpenSearch endpoint URL
        opensearch_host = OPENSEARCH_ENDPOINT.replace('https://', '').replace('http://', '')
        
        # Create OpenSearch client
        opensearch_client = OpenSearch(
            hosts=[{'host': opensearch_host, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # Check if index exists
        if opensearch_client.indices.exists(index=INDEX_NAME):
            logger.info(f"OpenSearch index '{INDEX_NAME}' exists and is accessible")
            return True
        else:
            logger.error(f"OpenSearch index '{INDEX_NAME}' does not exist")
            return False
            
    except Exception as e:
        logger.error(f"Failed to check OpenSearch index: {str(e)}")
        return False

def store_twelve_labs_index_id(index_id: str) -> None:
    """Store the Twelve Labs index ID in AWS Secrets Manager for other components to access"""
    try:
        secrets_client = boto3.client('secretsmanager')
        secret_name = "twelve-labs-index-id"
        
        # Try to update existing secret first
        try:
            secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps({"index_id": index_id})
            )
            logger.info(f"Updated Twelve Labs index ID in Secrets Manager: {index_id}")
        except secrets_client.exceptions.ResourceNotFoundException:
            # Secret doesn't exist, create it
            secrets_client.create_secret(
                Name=secret_name,
                SecretString=json.dumps({"index_id": index_id}),
                Description="Twelve Labs index ID for video processing"
            )
            logger.info(f"Created Twelve Labs index ID secret in Secrets Manager: {index_id}")
            
    except Exception as e:
        logger.error(f"Failed to store Twelve Labs index ID in Secrets Manager: {str(e)}")
        # Don't fail the entire process if secret storage fails
        # The processing can continue, but other components might need manual configuration

# Lambda handler for initiating video processing
def lambda_initiate_processing(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to initiate video processing using Twelve Labs SDK
    Triggered by S3 upload event via Step Functions
    """
    try:
        # Check OpenSearch index exists before proceeding
        if not check_opensearch_index():
            error_msg = f"OpenSearch index '{INDEX_NAME}' does not exist or is not accessible. Please create the index before processing videos."
            logger.error(error_msg)
            return {
                'statusCode': 400,
                'body': {
                    'error': error_msg,
                    'status': 'failed',
                    'reason': 'opensearch_index_missing'
                }
            }
        
        # Extract S3 details from event
        s3_bucket = event['detail']['bucket']['name']
        s3_key = event['detail']['object']['key']
        
        # Derive video title from filename
        filename = os.path.splitext(os.path.basename(s3_key))[0]
        video_title = filename.replace('_', ' ').replace('-', ' ').title()
        
        # Generate signed URL for video access
        s3_client = boto3.client('s3')
        video_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_bucket, 'Key': s3_key},
            ExpiresIn=3600 * 6  # 6 hours
        )
        
        # Initialize Twelve Labs SDK client
        twelve_labs = get_twelve_labs_client()
        config = VideoProcessingConfig()
        
        # Create or get Twelve Labs index using SDK
        # Get index name from environment or use a default
        index_name = os.getenv('DEFAULT_INDEX_NAME', 'video_library_index')
        index_id = twelve_labs.create_index_if_needed(index_name, config)
        
        # Store the index ID in AWS Secrets Manager for other components to use
        store_twelve_labs_index_id(index_id)
        
        # Generate thumbnail if ThumbnailGenerator is available
        thumbnail_s3_key = None
        if ThumbnailGenerator:
            try:
                # Generate a simple video ID for thumbnail naming
                video_id = f"video_{hash(s3_key) % 1000000:06d}"
                
                thumbnail_gen = ThumbnailGenerator(s3_bucket)
                thumbnail_s3_key = thumbnail_gen.generate_thumbnail_from_s3(
                    s3_key=s3_key,
                    video_id=video_id,
                    timestamp=10.0  # Capture at 10 seconds
                )
                
                if thumbnail_s3_key:
                    logger.info(f"Generated thumbnail S3 key: {thumbnail_s3_key}")
                else:
                    logger.error("Failed to generate thumbnail - this will cause the process to fail")
                    raise RuntimeError("Thumbnail generation failed")
                    
            except Exception as e:
                logger.error(f"Thumbnail generation error: {str(e)}")
                # Fail the process since thumbnails are required for the application
                raise RuntimeError(f"Thumbnail generation failed: {str(e)}")
        else:
            logger.error("ThumbnailGenerator not available")
            raise RuntimeError("ThumbnailGenerator module not available")
        
        return {
            'statusCode': 200,
            'body': {
                's3_bucket': s3_bucket,
                's3_key': s3_key,
                'video_url': video_url,
                'video_title': video_title,
                'thumbnail_s3_key': thumbnail_s3_key,
                'twelve_labs_index_id': index_id,
                'status': 'processing_initiated'
            }
        }
        
    except Exception as e:
        logger.error(f"Error initiating processing: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'status': 'failed'
            }
        }

# Main handler function for AWS Lambda
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler - entry point for AWS Lambda
    """
    return lambda_initiate_processing(event, context)