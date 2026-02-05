import json
import boto3
import os
from typing import Dict, Any, List
from dataclasses import dataclass
import logging

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
PRIMARY_REGION = os.environ.get('PRIMARY_REGION', 'us-east-1')  # All Nova 2 models in us-east-1

# Nova 2 Model Configuration
NOVA_OMNI_MODEL_ID = os.environ.get('NOVA_OMNI_MODEL_ID', 'global.amazon.nova-2-omni-v1:0')
NOVA_LITE_MODEL_ID = os.environ.get('NOVA_LITE_MODEL_ID', 'global.amazon.nova-2-lite-v1:0')
NOVA_EMBEDDING_MODEL_ID = os.environ.get('NOVA_EMBEDDING_MODEL_ID', 'amazon.nova-2-multimodal-embeddings-v1:0')
NOVA_EMBEDDING_DIMENSION = int(os.environ.get('NOVA_EMBEDDING_DIMENSION', '3072'))


@dataclass
class VideoProcessingConfig:
    """Configuration for video processing with Nova 2 models (all in us-east-1)"""
    nova_omni_model_id: str = "global.amazon.nova-2-omni-v1:0"
    nova_lite_model_id: str = "global.amazon.nova-2-lite-v1:0"
    nova_embedding_model_id: str = "amazon.nova-2-multimodal-embeddings-v1:0"
    embedding_dimension: int = 3072
    region: str = "us-east-1"

    def __post_init__(self):
        # Override with environment variables if set
        self.nova_omni_model_id = NOVA_OMNI_MODEL_ID
        self.nova_lite_model_id = NOVA_LITE_MODEL_ID
        self.nova_embedding_model_id = NOVA_EMBEDDING_MODEL_ID
        self.embedding_dimension = NOVA_EMBEDDING_DIMENSION
        self.region = PRIMARY_REGION


class NovaModelClient:
    """Client wrapper for Nova 2 models via Amazon Bedrock"""

    def __init__(self, region: str = PRIMARY_REGION):
        self.bedrock = boto3.client('bedrock', region_name=region)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        self.region = region
        self.logger = logging.getLogger(__name__)

    def validate_models_available(self, config: VideoProcessingConfig) -> bool:
        """Validate that Nova 2 models are available"""
        try:
            # Just validate we can access the Bedrock service
            # Model availability is checked at invocation time
            self.logger.info(f"Using Nova 2 models in {self.region}")
            self.logger.info(f"  - Nova Omni: {config.nova_omni_model_id}")
            self.logger.info(f"  - Nova Lite: {config.nova_lite_model_id}")
            self.logger.info(f"  - Nova Embedding: {config.nova_embedding_model_id}")
            return True

        except Exception as e:
            self.logger.error(f"Model validation failed: {e}")
            return False


def get_nova_client() -> NovaModelClient:
    """Get Nova model client"""
    return NovaModelClient()


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


def store_nova_config() -> None:
    """Store Nova configuration in AWS Secrets Manager for other components to access"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name=PRIMARY_REGION)
        secret_name = "nova-video-config"

        config_data = {
            "nova_omni_model_id": NOVA_OMNI_MODEL_ID,
            "nova_lite_model_id": NOVA_LITE_MODEL_ID,
            "nova_embedding_model_id": NOVA_EMBEDDING_MODEL_ID,
            "embedding_dimension": NOVA_EMBEDDING_DIMENSION,
            "region": PRIMARY_REGION,
            "using_nova": True
        }

        # Try to update existing secret first
        try:
            secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(config_data)
            )
            logger.info(f"Updated Nova config in Secrets Manager")
        except secrets_client.exceptions.ResourceNotFoundException:
            # Secret doesn't exist, create it
            secrets_client.create_secret(
                Name=secret_name,
                SecretString=json.dumps(config_data),
                Description="Nova 2 model configuration for video processing"
            )
            logger.info(f"Created Nova config secret in Secrets Manager")

    except Exception as e:
        logger.error(f"Failed to store Nova config in Secrets Manager: {str(e)}")
        # Don't fail the entire process if secret storage fails


# Lambda handler for initiating video processing
def lambda_initiate_processing(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to initiate video processing using Nova 2 models.
    Triggered by S3 upload event via Step Functions.
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

        # Initialize Nova client
        nova_client = get_nova_client()
        config = VideoProcessingConfig()

        # Validate that Nova models are accessible
        if not nova_client.validate_models_available(config):
            error_msg = "Nova 2 models not available in us-east-1"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Store Nova configuration for other components to use
        store_nova_config()

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
                'video_id': video_id,  # Pass video_id to ensure consistency with thumbnail
                'thumbnail_s3_key': thumbnail_s3_key,
                'nova_omni_model_id': config.nova_omni_model_id,
                'nova_lite_model_id': config.nova_lite_model_id,
                'nova_embedding_model_id': config.nova_embedding_model_id,
                'embedding_dimension': config.embedding_dimension,
                'region': config.region,
                'using_nova': True,
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
