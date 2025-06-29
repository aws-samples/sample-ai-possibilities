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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration from environment variables
TWELVE_LABS_API_KEY_SECRET = os.environ.get('TWELVE_LABS_API_KEY_SECRET')
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'video-insights-rag')

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

# Lambda handler for initiating video processing
def lambda_initiate_processing(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to initiate video processing using Twelve Labs SDK
    Triggered by S3 upload event via Step Functions
    """
    try:
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
        index_id = twelve_labs.create_index_if_needed("marketing_videos_sdk", config)
        
        return {
            'statusCode': 200,
            'body': {
                's3_bucket': s3_bucket,
                's3_key': s3_key,
                'video_url': video_url,
                'video_title': video_title,
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