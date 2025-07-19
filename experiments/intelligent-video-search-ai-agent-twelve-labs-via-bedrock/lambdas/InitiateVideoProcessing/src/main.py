import json
import boto3
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

# Import AWS Bedrock for TwelveLabs models
import boto3

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
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'video-insights-rag')
PRIMARY_REGION = os.environ.get('PRIMARY_REGION', 'us-east-1')  # For Marengo and main resources
PEGASUS_REGION = os.environ.get('PEGASUS_REGION', 'us-west-2')  # For Pegasus model
MAREGO_MODEL_ID = os.environ.get('MARENGO_MODEL_ID', 'twelvelabs.marengo-embed-2-7-v1:0')
PEGASUS_MODEL_ID = os.environ.get('PEGASUS_MODEL_ID', 'us.twelvelabs.pegasus-1-2-v1:0')
VIDEO_BUCKET_WEST = os.environ.get('VIDEO_BUCKET_WEST')  # S3 bucket in us-west-2

@dataclass
class VideoProcessingConfig:
    """Configuration for video processing with Bedrock (cross-region)"""
    marengo_model_id: str = "twelvelabs.marengo-embed-2-7-v1:0"  # us-east-1 only
    pegasus_model_id: str = "us.twelvelabs.pegasus-1-2-v1:0"      # us-west-2 only
    marengo_region: str = "us-east-1"
    pegasus_region: str = "us-west-2"
    model_options: List[str] = None
    
    def __post_init__(self):
        if self.model_options is None:
            self.model_options = ["visual", "audio"]

class BedrockTwelveLabsClient:
    """Client wrapper for TwelveLabs models via Amazon Bedrock (cross-region)"""
    
    def __init__(self, primary_region: str = PRIMARY_REGION, pegasus_region: str = PEGASUS_REGION):
        # Bedrock clients for different regions
        self.bedrock_east = boto3.client('bedrock', region_name=primary_region)
        self.bedrock_west = boto3.client('bedrock', region_name=pegasus_region)
        self.bedrock_runtime_east = boto3.client('bedrock-runtime', region_name=primary_region)
        self.bedrock_runtime_west = boto3.client('bedrock-runtime', region_name=pegasus_region)
        self.primary_region = primary_region
        self.pegasus_region = pegasus_region
        self.logger = logging.getLogger(__name__)
    
    def validate_models_available(self, config: VideoProcessingConfig) -> bool:
        """Validate that TwelveLabs models are available in their respective regions"""
        try:
            # Check Marengo availability in us-east-1
            response_east = self.bedrock_east.list_foundation_models(
                byProvider='TwelveLabs'
            )
            east_model_ids = [model['modelId'] for model in response_east.get('modelSummaries', [])]
            # Strip 'us.' prefix for cross-region models when checking availability
            marengo_check_id = config.marengo_model_id.replace('us.', '') if config.marengo_model_id.startswith('us.') else config.marengo_model_id
            marengo_available = marengo_check_id in east_model_ids
            
            # Check Pegasus availability in us-west-2  
            response_west = self.bedrock_west.list_foundation_models(
                byProvider='TwelveLabs'
            )
            west_model_ids = [model['modelId'] for model in response_west.get('modelSummaries', [])]
            # Strip 'us.' prefix for cross-region models when checking availability
            pegasus_check_id = config.pegasus_model_id.replace('us.', '') if config.pegasus_model_id.startswith('us.') else config.pegasus_model_id
            pegasus_available = pegasus_check_id in west_model_ids
            
            if not marengo_available:
                self.logger.error(f"Marengo model {config.marengo_model_id} not available in {self.primary_region}")
            if not pegasus_available:
                self.logger.error(f"Pegasus model {config.pegasus_model_id} not available in {self.pegasus_region}")
            
            return marengo_available and pegasus_available
            
        except Exception as e:
            self.logger.error(f"Cross-region model validation failed: {e}")
            return False
    
    def copy_video_to_west_region(self, source_bucket: str, source_key: str, dest_bucket: str) -> str:
        """Copy video from primary region to us-west-2 for Pegasus processing"""
        try:
            if not dest_bucket:
                raise ValueError("Destination bucket for us-west-2 not configured")
            
            # Use the same key structure
            dest_key = source_key
            
            # Copy object across regions
            s3_west = boto3.client('s3', region_name=self.pegasus_region)
            copy_source = {'Bucket': source_bucket, 'Key': source_key}
            
            s3_west.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key
            )
            
            self.logger.info(f"Copied video from {source_bucket}/{source_key} to {dest_bucket}/{dest_key}")
            return dest_key
            
        except Exception as e:
            self.logger.error(f"Failed to copy video to us-west-2: {e}")
            raise

def get_bedrock_client() -> BedrockTwelveLabsClient:
    """Get Bedrock client for cross-region TwelveLabs models"""
    return BedrockTwelveLabsClient()

def check_opensearch_index() -> bool:
    """Check if OpenSearch index exists and is accessible"""
    try:
        if not OPENSEARCH_ENDPOINT:
            raise ValueError("OpenSearch endpoint not configured")
        
        # Get AWS credentials for authentication
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, PRIMARY_REGION, 'aoss')
        
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

def store_bedrock_config() -> None:
    """Store Bedrock configuration in AWS Secrets Manager for other components to access"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name=PRIMARY_REGION)
        secret_name = "bedrock-twelvelabs-config"
        
        config_data = {
            "marengo_model_id": MAREGO_MODEL_ID,
            "pegasus_model_id": PEGASUS_MODEL_ID,
            "marengo_region": PRIMARY_REGION,
            "pegasus_region": PEGASUS_REGION,
            "video_bucket_west": VIDEO_BUCKET_WEST,
            "using_bedrock": True
        }
        
        # Try to update existing secret first
        try:
            secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(config_data)
            )
            logger.info(f"Updated Bedrock TwelveLabs config in Secrets Manager")
        except secrets_client.exceptions.ResourceNotFoundException:
            # Secret doesn't exist, create it
            secrets_client.create_secret(
                Name=secret_name,
                SecretString=json.dumps(config_data),
                Description="Bedrock TwelveLabs cross-region configuration for video processing"
            )
            logger.info(f"Created Bedrock TwelveLabs config secret in Secrets Manager")
            
    except Exception as e:
        logger.error(f"Failed to store Bedrock config in Secrets Manager: {str(e)}")
        # Don't fail the entire process if secret storage fails

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
            raise RuntimeError(error_msg)
        
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
        
        # Initialize Bedrock client for cross-region TwelveLabs models
        bedrock_client = get_bedrock_client()
        config = VideoProcessingConfig()
        
        # Validate that TwelveLabs models are available in their respective regions
        if not bedrock_client.validate_models_available(config):
            error_msg = "TwelveLabs models not available in required regions (Marengo: us-east-1, Pegasus: us-west-2)"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Copy video to us-west-2 for Pegasus processing
        video_key_west = None
        if VIDEO_BUCKET_WEST:
            try:
                video_key_west = bedrock_client.copy_video_to_west_region(
                    source_bucket=s3_bucket,
                    source_key=s3_key,
                    dest_bucket=VIDEO_BUCKET_WEST
                )
            except Exception as e:
                logger.error(f"Failed to copy video to us-west-2: {e}")
                return {
                    'statusCode': 500,
                    'body': {
                        'error': f"Failed to copy video to us-west-2: {str(e)}",
                        'status': 'failed'
                    }
                }
        else:
            logger.error("VIDEO_BUCKET_WEST not configured")
            return {
                'statusCode': 400,
                'body': {
                    'error': "VIDEO_BUCKET_WEST not configured for cross-region deployment",
                    'status': 'failed',
                    'reason': 'missing_west_bucket'
                }
            }
        
        # Store Bedrock configuration for other components to use
        store_bedrock_config()
        
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
                'marengo_model_id': config.marengo_model_id,
                'pegasus_model_id': config.pegasus_model_id,
                'marengo_region': config.marengo_region,
                'pegasus_region': config.pegasus_region,
                'video_key_west': video_key_west,
                'video_bucket_west': VIDEO_BUCKET_WEST,
                'using_bedrock': True,
                'status': 'processing_initiated'
            }
        }
        
    except Exception as e:
        logger.error(f"Error initiating processing: {str(e)}")
        # Re-raise the exception so Step Functions can catch it and trigger error handling
        raise

# Main handler function for AWS Lambda
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler - entry point for AWS Lambda
    """
    return lambda_initiate_processing(event, context)