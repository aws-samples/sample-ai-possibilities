import json
import boto3
import os
import time
import requests
import numpy as np
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, helpers
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import uuid

# AWS Bedrock for TwelveLabs models (cross-region)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration from environment variables
PRIMARY_REGION = os.environ.get('PRIMARY_REGION', 'us-east-1')  # For Marengo and main resources
PEGASUS_REGION = os.environ.get('PEGASUS_REGION', 'us-west-2')  # For Pegasus model
VIDEO_BUCKET_WEST = os.environ.get('VIDEO_BUCKET_WEST')  # S3 bucket in us-west-2
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'video-insights-rag')
COHERE_MODEL_ID = os.environ.get('COHERE_MODEL_ID', 'cohere.embed-english-v3')
NOVA_MODEL_ID = os.environ.get('NOVA_MODEL_ID', 'amazon.nova-lite-v1:0')
MARENGO_MODEL_ID = os.environ.get('MARENGO_MODEL_ID', 'twelvelabs.marengo-embed-2-7-v1:0')
PEGASUS_MODEL_ID = os.environ.get('PEGASUS_MODEL_ID', 'us.twelvelabs.pegasus-1-2-v1:0')
NOVA_MAX_CHARS = int(os.environ.get('NOVA_MAX_CHARS', '350000'))

class BedrockClient:
    """Client for extracting brands, companies, and names using Amazon Bedrock's Nova model"""
    
    def __init__(self, region_name: str = PRIMARY_REGION, model_id: str = NOVA_MODEL_ID, max_chars: int = NOVA_MAX_CHARS):
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name=region_name)
        self.model_id = model_id
        self.max_chars = max_chars
        self.logger = logging.getLogger(__name__)
    
    def extract_entities_from_transcription(self, transcription_text: str) -> Dict[str, List[str]]:
        """
        Extract brands, companies, and person names from transcription text using Amazon Bedrock
        
        Args:
            transcription_text: The transcription text from AWS Transcribe (may contain typos)
            
        Returns:
            Dictionary with lists of brands, companies, and person names
        """
        try:
            self.logger.info(f"Using Bedrock model: {self.model_id} for entity extraction")
            # Truncate text if too long (different models have different input limits)
            if len(transcription_text) > self.max_chars:
                self.logger.warning(f"Transcription text too long ({len(transcription_text)} chars), truncating to {self.max_chars}")
                transcription_text = transcription_text[:self.max_chars]
            
            prompt = f"""You are an expert at extracting entities from video transcriptions. The transcription may contain typos and errors from speech-to-text conversion.

            Analyze the following transcription and extract all:
            1. Brand names (e.g., Nike, Apple, Coca-Cola)
            2. Company names (e.g., Microsoft Corporation, Amazon Web Services)
            3. Person names (e.g., John Smith, Jane Doe)

            Be thorough and include variations of the same entity. For example, if both "AWS" and "Amazon Web Services" appear, include both.

            Transcription:
            {transcription_text}

            Use the extract_entities tool to provide the structured results."""

            # Prepare the request with tool configuration
            body = json.dumps({
                "messages": [{
                    "role": "user",
                    "content": [{"text": prompt}]
                }],
                "inferenceConfig": {
                    "max_new_tokens": 2000,
                    "temperature": 0.1,  # Low temperature for consistent extraction
                    "top_p": 0.9
                },
                "toolConfig": {
                    "tools": [{
                        "toolSpec": {
                            "name": "extract_entities",
                            "description": "Extract brands, companies, and person names from transcription text",
                            "inputSchema": {
                                "json": {
                                    "type": "object",
                                    "properties": {
                                        "brands": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of brand names mentioned in the transcription"
                                        },
                                        "companies": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of company names mentioned in the transcription"
                                        },
                                        "person_names": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of person names mentioned in the transcription"
                                        }
                                    },
                                    "required": ["brands", "companies", "person_names"]
                                }
                            }
                        }
                    }],
                    "toolChoice": {"any": {}}
                }
            })
            
            # Invoke the model
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json'
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            
            # Extract the content from the tool call response format
            if 'output' in response_body and 'message' in response_body['output']:
                message = response_body['output']['message']
                
                # Look for tool use in the message content
                if 'content' in message:
                    for content_item in message['content']:
                        if content_item.get('toolUse'):
                            tool_use = content_item['toolUse']
                            if tool_use.get('name') == 'extract_entities':
                                # Extract entities from tool input
                                entities = tool_use.get('input', {})
                                
                                # Ensure all keys exist and are lists
                                return {
                                    'brands': entities.get('brands', []),
                                    'companies': entities.get('companies', []),
                                    'person_names': entities.get('person_names', [])
                                }
                
                # Fallback: try to parse as regular text response (for backwards compatibility)
                if len(message['content']) > 0 and 'text' in message['content'][0]:
                    content_text = message['content'][0]['text']
                    try:
                        entities = json.loads(content_text)
                        return {
                            'brands': entities.get('brands', []),
                            'companies': entities.get('companies', []),
                            'person_names': entities.get('person_names', [])
                        }
                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to parse LLM response as JSON: {content_text}")
                        return {'brands': [], 'companies': [], 'person_names': []}
                
                self.logger.error(f"No tool use found in response: {message}")
                return {'brands': [], 'companies': [], 'person_names': []}
            else:
                self.logger.error(f"Unexpected LLM response format: {response_body}")
                return {'brands': [], 'companies': [], 'person_names': []}
                
        except Exception as e:
            self.logger.error(f"Failed to extract entities with LLM: {e}")
            return {'brands': [], 'companies': [], 'person_names': []}


class CohereEmbeddingClient:
    """Client for generating embeddings using Amazon Bedrock's Cohere model"""
    
    def __init__(self, region_name: str = PRIMARY_REGION):
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name=region_name)
        self.model_id = COHERE_MODEL_ID
        self.logger = logging.getLogger(__name__)
    
    def generate_embeddings(self, texts: List[str], input_type: str = "search_document") -> List[float]:
        """
        Generate embeddings for video content using Cohere
        
        Args:
            texts: List of text strings to embed
            input_type: Either "search_document" for indexing or "search_query" for searching
            
        Returns:
            List of embedding vectors (float type)
        """
        try:
            # Cohere has a limit on text length, so we might need to truncate
            # Maximum is typically 512 tokens, roughly 2048 characters
            truncated_texts = [text[:2048] if len(text) > 2048 else text for text in texts]
            
            body = json.dumps({
                "texts": truncated_texts,
                "input_type": input_type,
                "embedding_types": ["float"]
            })
            
            response = self.bedrock.invoke_model(
                body=body,
                modelId=self.model_id,
                accept='*/*',
                contentType='application/json'
            )
            
            response_body = json.loads(response.get('body').read())
            embeddings = response_body.get('embeddings', {}).get('float', [])
            
            self.logger.info(f"Generated {len(embeddings)} embeddings with Cohere")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating Cohere embeddings: {e}")
            raise

class TranscribeClient:
    """Client for Amazon Transcribe operations"""
    
    def __init__(self):
        self.client = boto3.client('transcribe')
        self.s3_client = boto3.client('s3')
        self.logger = logging.getLogger(__name__)
    
    def start_transcription_job(self, video_url: str, s3_bucket: str, s3_key: str) -> str:
        """Start Amazon Transcribe job for video"""
        job_name = f"video-transcription-{uuid.uuid4().hex[:8]}"
        
        # Construct S3 URI for Transcribe (not presigned URL)
        s3_uri = f"s3://{s3_bucket}/{s3_key}"
        
        try:
            response = self.client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': s3_uri},
                MediaFormat=s3_key.split('.')[-1].lower(),  # Extract format from file extension
                LanguageCode='en-US',
                OutputBucketName=s3_bucket,
                OutputKey=f"transcriptions/{job_name}.json",
                Settings={
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 10
                }
            )
            
            self.logger.info(f"Started transcription job: {job_name}")
            return job_name
            
        except Exception as e:
            self.logger.error(f"Failed to start transcription job: {e}")
            raise
    
    def wait_for_transcription_job(self, job_name: str, max_wait_time: int = 600) -> Dict[str, Any]:
        """Wait for transcription job to complete"""
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_wait_time:
                raise TimeoutError(f"Transcription job {job_name} timed out after {max_wait_time} seconds")
            
            response = self.client.get_transcription_job(TranscriptionJobName=job_name)
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                self.logger.info(f"Transcription job {job_name} completed")
                return response['TranscriptionJob']
            elif status == 'FAILED':
                raise Exception(f"Transcription job {job_name} failed: {response['TranscriptionJob'].get('FailureReason', 'Unknown')}")
            
            self.logger.info(f"Transcription job {job_name} status: {status}")
            time.sleep(10)
    
    def parse_transcription_results(self, transcript_uri: str) -> Dict[str, Any]:
        """Parse Transcribe results from S3"""
        try:
            # Parse bucket and key from URI (handles both S3 and HTTPS formats)
            if transcript_uri.startswith('https://'):
                # Parse HTTPS URL: https://s3.region.amazonaws.com/bucket/key
                # or https://bucket.s3.region.amazonaws.com/key
                import re
                
                # Try both URL patterns
                match = re.match(r'https://s3[.-]([^.]+\.)?amazonaws\.com/([^/]+)/(.+)', transcript_uri)
                if match:
                    bucket = match.group(2)
                    key = match.group(3)
                else:
                    # Try bucket.s3.region format
                    match = re.match(r'https://([^.]+)\.s3[.-]([^.]+\.)?amazonaws\.com/(.+)', transcript_uri)
                    if match:
                        bucket = match.group(1)
                        key = match.group(3)
                    else:
                        raise ValueError(f"Unable to parse S3 URL: {transcript_uri}")
            else:
                # For S3 URIs, extract bucket and key
                parts = transcript_uri.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1]
            
            self.logger.info(f"Fetching transcript from S3: bucket={bucket}, key={key}")
            
            # Get transcript from S3 using IAM role permissions
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            transcript_data = json.loads(response['Body'].read())
            
            # Format for OpenSearch
            formatted_transcription = {
                'full_text': transcript_data['results']['transcripts'][0]['transcript'],
                'segments': [],
                'speaker_labels': []
            }
            
            # Add time-aligned segments
            for item in transcript_data['results']['items']:
                if item['type'] == 'pronunciation':
                    formatted_transcription['segments'].append({
                        'text': item['alternatives'][0]['content'],
                        'start_time': float(item.get('start_time', 0)),
                        'end_time': float(item.get('end_time', 0)),
                        'confidence': float(item['alternatives'][0].get('confidence', 0))
                    })
            
            # Add speaker labels if available
            if 'speaker_labels' in transcript_data['results']:
                speaker_segments = transcript_data['results']['speaker_labels']['segments']
                for segment in speaker_segments:
                    formatted_transcription['speaker_labels'].append({
                        'speaker': segment['speaker_label'],
                        'start_time': float(segment['start_time']),
                        'end_time': float(segment['end_time'])
                    })
            
            return formatted_transcription
            
        except Exception as e:
            self.logger.error(f"Failed to parse transcription results: {e}")
            raise

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

class VideoInsightsClient:
    """Bedrock-based replacement for TwelveLabs VideoInsightsClient"""
    
    def __init__(self, primary_region: str = PRIMARY_REGION, pegasus_region: str = PEGASUS_REGION):
        # Bedrock clients for different regions
        self.bedrock_runtime_east = boto3.client('bedrock-runtime', region_name=primary_region)
        self.bedrock_runtime_west = boto3.client('bedrock-runtime', region_name=pegasus_region)
        self.primary_region = primary_region
        self.pegasus_region = pegasus_region
        self.logger = logging.getLogger(__name__)

    def upload_video_and_wait(self, video_url: str, video_bucket_west: str, video_key_west: str, language: str = "en") -> str:
        """
        Process video using Bedrock (simulated upload)
        Since Bedrock doesn't have an upload mechanism like TwelveLabs SDK,
        we'll generate a synthetic video_id and assume the video is accessible
        """
        try:
            # Generate a synthetic video ID based on the video URL/key
            import hashlib
            video_id = hashlib.md5(f"{video_url}_{video_key_west}".encode()).hexdigest()[:16]
            
            self.logger.info(f"Processing video with Bedrock - Video ID: {video_id}")
            self.logger.info(f"Video URL: {video_url}")
            self.logger.info(f"West bucket: {video_bucket_west}, key: {video_key_west}")
            
            # Simulate processing time
            time.sleep(2)
            
            self.logger.info(f"Video processing completed for ID: {video_id}")
            return video_id
            
        except Exception as e:
            self.logger.error(f"Video upload/processing failed: {e}")
            raise
    
    
    def generate_comprehensive_insights(self, video_id: str, video_url: str, video_bucket_west: str, video_key_west: str) -> Dict[str, Any]:
        """Generate comprehensive insights using Bedrock Pegasus model"""
        insights = {}
        
        try:
            # Generate summary using Bedrock Pegasus
            summary_prompt = "Provide a comprehensive content analysis including entity visibility, emotional impact, key messages, and content themes. Give a detailed summary that captures the essence of the video content."
            summary_result = self._invoke_pegasus_model(summary_prompt, video_bucket_west, video_key_west)
            insights['summary'] = summary_result
            
            # Generate chapters using Bedrock Pegasus
            chapters_prompt = """Analyze this video and break it down into logical chapters or segments. For each chapter, provide:
            - Start time (in seconds)
            - End time (in seconds) 
            - Chapter title
            - Brief summary of what happens in this segment
            
            Return as a JSON array with format: [{"start": 0, "end": 30, "title": "Introduction", "summary": "..."}]"""
            chapters_result = self._invoke_pegasus_model(chapters_prompt, video_bucket_west, video_key_west)
            insights['chapters'] = self._parse_chapters_response(chapters_result)
            
            # Generate highlights using Bedrock Pegasus
            highlights_prompt = """Identify the most important and engaging moments in this video. For each highlight, provide:
            - Start time (in seconds)
            - End time (in seconds)
            - Description of what makes this moment significant
            
            Focus on key reveals, emotional peaks, important information, or memorable moments.
            Return as JSON array with format: [{"start": 10, "end": 20, "highlight": "Key moment description"}]"""
            highlights_result = self._invoke_pegasus_model(highlights_prompt, video_bucket_west, video_key_west)
            insights['highlights'] = self._parse_highlights_response(highlights_result)
            
            # Generate topics using Bedrock Pegasus
            topics_prompt = "List the main topics, themes, and key concepts discussed in this video. Include both primary and secondary topics."
            topics_result = self._invoke_pegasus_model(topics_prompt, video_bucket_west, video_key_west)
            insights['topics'] = topics_result
            
            # Generate hashtags using Bedrock Pegasus
            hashtags_prompt = "Generate relevant hashtags for social media based on this video content. Include hashtags for topics, themes, industry, and general engagement. Return as a comma-separated list."
            hashtags_result = self._invoke_pegasus_model(hashtags_prompt, video_bucket_west, video_key_west)
            insights['hashtags'] = hashtags_result
            
            # Generate sentiment analysis
            sentiment_prompt = """Analyze the overall sentiment and emotional tone of this video. Provide:
            - Overall sentiment (positive, negative, neutral)
            - Emotional tone descriptors
            - Percentage breakdown if applicable
            - Key emotional moments"""
            sentiment_result = self._invoke_pegasus_model(sentiment_prompt, video_bucket_west, video_key_west)
            insights['sentiment_analysis'] = sentiment_result
            
            # Extract content analytics
            analytics_prompt = """Extract key content analytics from this video:
            - Important entity mentions and their frequency
            - Topic coverage and duration
            - Engagement indicators (if visible)
            - Content structure analysis"""
            analytics_result = self._invoke_pegasus_model(analytics_prompt, video_bucket_west, video_key_west)
            insights['content_analytics'] = analytics_result
            
        except Exception as e:
            self.logger.error(f"Insights generation failed: {e}")
            raise
        
        return insights
    
    def get_video_embeddings(self, video_id: str, video_url: str,
        video_bucket_east: str, video_key_east: str) -> List[Dict[str, Any]]:
        """Get video embeddings using Bedrock Marengo model"""
        try:
            # Construct S3 URI for Marengo (uses S3 input, not base64)
            video_s3_uri = f"s3://{video_bucket_east}/{video_key_east}"
            
            # Generate embeddings using Marengo in us-east-1 with async invoke
            embeddings_result = self._invoke_marengo_model(video_s3_uri, video_bucket_east)
            
            # Return the embeddings directly without any fallback
            return embeddings_result
            
        except Exception as e:
            self.logger.error(f"Embeddings retrieval failed: {e}")
            raise Exception(f"Failed to get video embeddings from Marengo: {str(e)}")
    
    def search_video_content(self, video_id: str, transcription_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract entities from transcription using Nova Lite (maintains compatibility)
        
        Args:
            video_id: Video ID (for compatibility)
            transcription_text: Optional transcription text for entity extraction
            
        Returns:
            Dictionary with extracted entities
        """
        search_results = {}
        
        try:
            # If transcription text is provided, extract entities using Nova Lite
            if transcription_text:
                self.logger.info("Extracting entities from transcription using Amazon Bedrock Nova Lite")
                bedrock_client = BedrockClient()
                entities = bedrock_client.extract_entities_from_transcription(transcription_text)
                
                # Store entities in the same structure as before
                search_results['entities'] = {
                    'brands': entities.get('brands', []),
                    'companies': entities.get('companies', []),
                    'person_names': entities.get('person_names', [])
                }
                
                self.logger.info(f"Extracted entities - Brands: {len(entities.get('brands', []))}, "
                               f"Companies: {len(entities.get('companies', []))}, "
                               f"Names: {len(entities.get('person_names', []))}")
            else:
                self.logger.warning("No transcription text provided for entity extraction")
                search_results['entities'] = {
                    'brands': [],
                    'companies': [],
                    'person_names': []
                }
            
        except Exception as e:
            self.logger.error(f"Entity extraction error: {e}")
            # Return empty results rather than failing
            search_results['entities'] = {
                'brands': [],
                'companies': [],
                'person_names': []
            }
        
        return search_results
    
    def _get_video_base64(self, bucket: str, key: str) -> str:
        """Download video from S3 and convert to base64 for Bedrock models"""
        try:
            # Download video from S3
            s3_client = boto3.client('s3', region_name=self.pegasus_region)
            response = s3_client.get_object(Bucket=bucket, Key=key)
            video_content = response['Body'].read()
            
            # Convert to base64
            import base64
            video_base64 = base64.b64encode(video_content).decode('utf-8')
            
            self.logger.info(f"Successfully converted video to base64 (size: {len(video_base64)} chars)")
            return video_base64
            
        except Exception as e:
            self.logger.error(f"Failed to get video base64: {e}")
            raise
    
    def _invoke_pegasus_model(self, prompt: str, video_west_bucket: str, video_west_key: str) -> str:
        """Invoke Pegasus model in us-west-2 for video understanding"""
        try:

            # Get AWS account ID for bucket owner
            sts_client = boto3.client('sts', region_name=self.primary_region)
            account_id = sts_client.get_caller_identity()['Account']

            video_s3_uri = f"s3://{video_west_bucket}/{video_west_key}"
            
            request_body = {
                "inputPrompt": prompt,
                "mediaSource": {
                    "s3Location": {
                        "uri": video_s3_uri,
                        "bucketOwner": account_id
                    }
                }
            }
            
            # Invoke Pegasus model in us-west-2
            response = self.bedrock_runtime_west.invoke_model(
                modelId=PEGASUS_MODEL_ID,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            
            # Extract the response text
            if 'response' in response_body:
                return response_body['response']
            elif 'output' in response_body:
                return response_body['output']
            else:
                return str(response_body)
            
        except Exception as e:
            self.logger.error(f"Pegasus model invocation failed: {e}")
            return f"Error: {str(e)}"
    
    def _invoke_marengo_model(self, video_s3_uri: str, video_bucket_east: str) -> List[Dict[str, Any]]:
        """Invoke Marengo model in us-east-1 for video embeddings using StartAsyncInvoke"""
        try:
            import uuid
            import time
            
            # Generate unique invocation ID
            invocation_id = f"marengo-{uuid.uuid4().hex[:8]}"
            
            # Get AWS account ID for bucket owner
            sts_client = boto3.client('sts', region_name=self.primary_region)
            account_id = sts_client.get_caller_identity()['Account']
            
            # Create output S3 path for embeddings
            output_s3_uri = f"s3://{video_bucket_east}/embeddings/{invocation_id}/"
            
            # Prepare request payload for StartAsyncInvoke
            request_payload = {
                "modelId": MARENGO_MODEL_ID,
                "modelInput": {
                    "inputType": "video",
                    "mediaSource": {
                        "s3Location": {
                            "uri": video_s3_uri,
                            "bucketOwner": account_id
                        }
                    }
                },
                "outputDataConfig": {
                    "s3OutputDataConfig": {
                        "s3Uri": output_s3_uri
                    }
                }
            }
            
            self.logger.info(f"Starting async Marengo invocation with ID: {invocation_id}")
            self.logger.info(f"Input S3 URI: {video_s3_uri}")
            self.logger.info(f"Output S3 URI: {output_s3_uri}")
            
            # Start async invocation using bedrock-runtime client
            response = self.bedrock_runtime_east.start_async_invoke(
                modelId=MARENGO_MODEL_ID,
                modelInput=request_payload["modelInput"],
                outputDataConfig=request_payload["outputDataConfig"]
            )
            
            invocation_arn = response['invocationArn']
            self.logger.info(f"Started async invocation: {invocation_arn}")
            
            # Wait for completion (with timeout)
            max_wait_time = 300  # 5 minutes
            check_interval = 10  # 10 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # Check invocation status using GetAsyncInvoke
                status_response = self.bedrock_runtime_east.get_async_invoke(
                    invocationArn=invocation_arn
                )
                
                status = status_response['status']
                self.logger.info(f"Marengo invocation status: {status}")
                
                if status == 'Completed':
                    self.logger.info("Marengo embedding generation completed")
                    # Download and parse results from S3
                    return self._parse_marengo_results(output_s3_uri, video_bucket_east)
                    
                elif status == 'Failed':
                    error_msg = status_response.get('failureMessage', 'Unknown error')
                    raise Exception(f"Marengo invocation failed: {error_msg}")
                
                # Wait before next check
                time.sleep(check_interval)
                elapsed_time += check_interval
            
            # Timeout reached
            self.logger.error(f"Marengo invocation timed out after {max_wait_time} seconds")
            raise Exception(f"Marengo embedding generation timed out after {max_wait_time} seconds")
            
        except Exception as e:
            self.logger.error(f"Marengo model invocation failed: {e}")
            raise Exception(f"Failed to invoke Marengo model: {str(e)}")
    
    def _parse_marengo_results(self, output_s3_uri: str, bucket: str) -> List[Dict[str, Any]]:
        """Parse Marengo embedding results from S3"""
        try:
            # Extract bucket and prefix from S3 URI
            s3_prefix = output_s3_uri.replace(f"s3://{bucket}/", "")
            
            # List objects in the output directory
            s3_client = boto3.client('s3', region_name=self.primary_region)
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=s3_prefix
            )
            
            if 'Contents' not in response:
                self.logger.error("No output files found from Marengo")
                raise Exception("Marengo did not produce any output files")
            
            # Log all files found
            self.logger.info(f"Files found in Marengo output directory:")
            for obj in response['Contents']:
                self.logger.info(f"  - {obj['Key']} (size: {obj['Size']} bytes)")
            
            # Look for the actual embeddings file (not manifest)
            embeddings_found = False
            for obj in response['Contents']:
                key = obj['Key']
                # Skip manifest files and look for actual embeddings
                if 'manifest' in key.lower():
                    self.logger.info(f"Skipping manifest file: {key}")
                    continue
                    
                # Look for files that might contain embeddings
                if key.endswith('.json') or 'embedding' in key.lower() or 'output' in key.lower():
                    self.logger.info(f"Attempting to parse potential embeddings file: {key}")
                    
                    try:
                        # Download and parse the file
                        obj_response = s3_client.get_object(Bucket=bucket, Key=key)
                        embeddings_content = obj_response['Body'].read().decode('utf-8')
                        embeddings_data = json.loads(embeddings_content)
                        
                        self.logger.info(f"File {key} structure: {list(embeddings_data.keys())}")
                        
                        # Check if this file contains embeddings
                        if 'embeddings' in embeddings_data or 'segments' in embeddings_data or 'results' in embeddings_data or 'data' in embeddings_data:
                            self.logger.info(f"Found potential embeddings in file: {key}")
                            return self._format_marengo_embeddings(embeddings_data)
                        else:
                            self.logger.info(f"File {key} does not contain embeddings, continuing search")
                    except Exception as e:
                        self.logger.warning(f"Failed to parse file {key}: {e}")
                        continue
            
            # If we get here, no valid embeddings were found
            self.logger.error("No valid embeddings file found after checking all files in Marengo output")
            raise Exception("No valid embeddings file found in Marengo output")
            
        except Exception as e:
            self.logger.error(f"Failed to parse Marengo results: {e}")
            raise Exception(f"Failed to parse Marengo embedding results: {str(e)}")
    
    def _format_marengo_embeddings(self, embeddings_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format Marengo embeddings to match expected structure"""
        try:
            formatted_embeddings = []
            
            # Log the full structure for debugging
            self.logger.info(f"Attempting to format embeddings from data with keys: {list(embeddings_data.keys())}")
            
            # Parse embeddings based on actual Marengo output structure
            # Try different possible structures
            if 'embeddings' in embeddings_data:
                self.logger.info("Found 'embeddings' key in data")
                for segment in embeddings_data['embeddings']:
                    formatted_embeddings.append({
                        'embedding': segment.get('embedding', segment.get('vector', segment.get('values', []))),
                        'start_time': segment.get('start_time', segment.get('startTime', segment.get('start', 0))),
                        'end_time': segment.get('end_time', segment.get('endTime', segment.get('end', 30))),
                        'scope': segment.get('scope', segment.get('type', 'visual-audio'))
                    })
            elif 'segments' in embeddings_data:
                self.logger.info("Found 'segments' key in data")
                for i, segment in enumerate(embeddings_data['segments']):
                    formatted_embeddings.append({
                        'embedding': segment.get('embedding', segment.get('vector', segment.get('values', []))),
                        'start_time': segment.get('start_time', segment.get('startTime', i * 30)),
                        'end_time': segment.get('end_time', segment.get('endTime', (i + 1) * 30)),
                        'scope': 'visual-audio'
                    })
            elif 'results' in embeddings_data:
                self.logger.info("Found 'results' key in data")
                results = embeddings_data['results']
                if isinstance(results, list):
                    for i, result in enumerate(results):
                        formatted_embeddings.append({
                            'embedding': result.get('embedding', result.get('vector', result.get('values', []))),
                            'start_time': result.get('start_time', result.get('startTime', i * 30)),
                            'end_time': result.get('end_time', result.get('endTime', (i + 1) * 30)),
                            'scope': 'visual-audio'
                        })
                elif isinstance(results, dict) and 'embeddings' in results:
                    # Nested structure
                    for segment in results['embeddings']:
                        formatted_embeddings.append({
                            'embedding': segment.get('embedding', segment.get('vector', segment.get('values', []))),
                            'start_time': segment.get('start_time', segment.get('startTime', 0)),
                            'end_time': segment.get('end_time', segment.get('endTime', 30)),
                            'scope': segment.get('scope', segment.get('type', 'visual-audio'))
                        })
            elif 'data' in embeddings_data:
                self.logger.info("Found 'data' key in data")
                # Another possible structure
                data = embeddings_data['data']
                if isinstance(data, list):
                    self.logger.info(f"Data is a list with {len(data)} items")
                    for i, item in enumerate(data):
                        if i == 0:  # Log first item structure
                            self.logger.info(f"First item structure: {list(item.keys()) if isinstance(item, dict) else type(item)}")
                        
                        # Handle different possible structures within data
                        if isinstance(item, dict):
                            # Check if the item has an embedding field
                            embedding_vector = item.get('embedding', item.get('vector', item.get('values', [])))
                            if embedding_vector:
                                formatted_embeddings.append({
                                    'embedding': embedding_vector,
                                    'start_time': item.get('start_time', item.get('startTime', item.get('start', i * 30))),
                                    'end_time': item.get('end_time', item.get('endTime', item.get('end', (i + 1) * 30))),
                                    'scope': item.get('scope', item.get('type', 'visual-audio'))
                                })
                            else:
                                self.logger.warning(f"Item {i} has no embedding vector")
                        elif isinstance(item, list):
                            # If data contains raw embedding vectors
                            formatted_embeddings.append({
                                'embedding': item,
                                'start_time': i * 30,
                                'end_time': (i + 1) * 30,
                                'scope': 'visual-audio'
                            })
                elif isinstance(data, dict):
                    self.logger.info(f"Data is a dict with keys: {list(data.keys())}")
                    # Check if embeddings are nested within data
                    if 'embeddings' in data:
                        for i, segment in enumerate(data['embeddings']):
                            formatted_embeddings.append({
                                'embedding': segment.get('embedding', segment.get('vector', segment.get('values', []))),
                                'start_time': segment.get('start_time', segment.get('startTime', i * 30)),
                                'end_time': segment.get('end_time', segment.get('endTime', (i + 1) * 30)),
                                'scope': segment.get('scope', segment.get('type', 'visual-audio'))
                            })
                    elif 'vectors' in data:
                        for i, vector in enumerate(data['vectors']):
                            formatted_embeddings.append({
                                'embedding': vector,
                                'start_time': i * 30,
                                'end_time': (i + 1) * 30,
                                'scope': 'visual-audio'
                            })
                else:
                    self.logger.warning(f"Unexpected data type: {type(data)}")
            elif isinstance(embeddings_data, list):
                # The entire response might be a list of embeddings
                self.logger.info(f"Embeddings data is a list with {len(embeddings_data)} items")
                for i, item in enumerate(embeddings_data):
                    if isinstance(item, list):
                        # Raw vector
                        formatted_embeddings.append({
                            'embedding': item,
                            'start_time': i * 30,
                            'end_time': (i + 1) * 30,
                            'scope': 'visual-audio'
                        })
                    elif isinstance(item, dict):
                        formatted_embeddings.append({
                            'embedding': item.get('embedding', item.get('vector', item.get('values', []))),
                            'start_time': item.get('start_time', item.get('startTime', i * 30)),
                            'end_time': item.get('end_time', item.get('endTime', (i + 1) * 30)),
                            'scope': 'visual-audio'
                        })
            else:
                # Log unknown structure
                self.logger.warning(f"Unknown embeddings data structure. Keys: {list(embeddings_data.keys()) if isinstance(embeddings_data, dict) else 'Not a dict'}")
                self.logger.warning(f"Sample data: {json.dumps(embeddings_data, indent=2)[:1000]}...")
            
            # Validate that we actually got embeddings with non-empty vectors
            valid_embeddings = []
            for emb in formatted_embeddings:
                if emb.get('embedding') and len(emb['embedding']) > 0:
                    valid_embeddings.append(emb)
                else:
                    self.logger.warning(f"Skipping embedding with empty or missing vector")
            
            if not valid_embeddings:
                self.logger.error(f"No valid embeddings could be formatted from Marengo output. Data structure: {json.dumps(embeddings_data, indent=2)[:500]}...")
                raise Exception("Failed to format any valid embeddings from Marengo output - all embeddings were empty or missing")
            
            self.logger.info(f"Successfully formatted {len(valid_embeddings)} embeddings")
            
            # Return list directly, not dict
            return valid_embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to format Marengo embeddings: {e}")
            raise Exception(f"Failed to format Marengo embeddings: {str(e)}")
    
    def _parse_chapters_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse chapters response from Pegasus model"""
        try:
            # Try to parse as JSON first
            import json
            chapters_data = json.loads(response)
            if isinstance(chapters_data, list):
                return [
                    {
                        'start': ch.get('start', 0),
                        'end': ch.get('end', 60),
                        'title': ch.get('title', 'Chapter'),
                        'summary': ch.get('summary', '')
                    }
                    for ch in chapters_data
                ]
        except (json.JSONDecodeError, TypeError):
            # If not JSON, create a single chapter
            pass
        
        # Fallback: create a single chapter
        return [{
            'start': 0,
            'end': 60,
            'title': 'Full Video',
            'summary': response[:200] if response else 'No chapter summary available'
        }]
    
    def _parse_highlights_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse highlights response from Pegasus model"""
        try:
            # Try to parse as JSON first
            import json
            highlights_data = json.loads(response)
            if isinstance(highlights_data, list):
                return [
                    {
                        'start': hl.get('start', 0),
                        'end': hl.get('end', 10),
                        'highlight': hl.get('highlight', hl.get('description', 'Highlight'))
                    }
                    for hl in highlights_data
                ]
        except (json.JSONDecodeError, TypeError):
            # If not JSON, create a single highlight
            pass
        
        # Fallback: create a single highlight
        return [{
            'start': 0,
            'end': 10,
            'highlight': response[:100] if response else 'No highlights available'
        }]


def prepare_content_for_embedding(insights: Dict[str, Any], detections: Dict[str, Any]) -> str:
    """
    Prepare the most relevant content for Cohere embedding.
    This content will be used for semantic searches across the video library.
    """
    content_parts = []
    
    # 1. Summary - This is crucial for content searches
    if insights.get('summary'):
        content_parts.append(f"SUMMARY: {insights['summary']}")
    
    # 2. Key topics and themes
    if insights.get('topics'):
        content_parts.append(f"TOPICS: {insights['topics']}")
    
    # 3. Marketing metrics and sentiment
    if insights.get('content_analytics'):
        content_parts.append(f"CONTENT ANALYTICS: {insights['content_analytics']}")
    
    if insights.get('sentiment_analysis'):
        content_parts.append(f"SENTIMENT: {insights['sentiment_analysis']}")
    
    # 4. Hashtags for social media relevance
    if insights.get('hashtags'):
        content_parts.append(f"HASHTAGS: {insights['hashtags']}")
    
    # 5. Chapter titles and highlights (great for finding specific moments)
    if insights.get('chapters'):
        chapter_titles = [ch['title'] for ch in insights['chapters'] if ch.get('title')]
        if chapter_titles:
            content_parts.append(f"CHAPTERS: {', '.join(chapter_titles)}")
    
    if insights.get('highlights'):
        highlight_texts = [h['highlight'] for h in insights['highlights'] if h.get('highlight')]
        if highlight_texts:
            content_parts.append(f"KEY MOMENTS: {' | '.join(highlight_texts[:5])}")  # Top 5 highlights
    
    # 6. Brand/company/name mentions from transcription
    if detections.get('entities'):
        entities = detections['entities']
        
        # Brands detected from transcription
        if entities.get('brands'):
            content_parts.append(f"BRANDS MENTIONED: {', '.join(entities['brands'])}")
            
        # Companies detected from transcription
        if entities.get('companies'):
            content_parts.append(f"COMPANIES MENTIONED: {', '.join(entities['companies'])}")
            
        # Person names detected from transcription
        if entities.get('person_names'):
            content_parts.append(f"PEOPLE MENTIONED: {', '.join(entities['person_names'])}")
    
    # 7. Legacy logo detection (keeping for backward compatibility)
    if detections.get('logos'):
        unique_brands = set()
        for logo in detections['logos']:
            if logo.get('brand_name'):
                unique_brands.add(logo['brand_name'])
        if unique_brands:
            content_parts.append(f"BRANDS DETECTED VISUALLY: {', '.join(unique_brands)}")
    
    # 8. Emotional content (for sentiment-based searches)
    if detections.get('emotions'):
        emotion_types = set()
        for emotion in detections['emotions']:
            if emotion.get('type'):
                emotion_types.add(emotion['type'])
        if emotion_types:
            content_parts.append(f"EMOTIONS: {', '.join(emotion_types)}")
    
    # 9. First 500 chars of transcription (for spoken content searches)
    if insights.get('transcription', {}).get('full_text'):
        transcript_preview = insights['transcription']['full_text'][:500]
        content_parts.append(f"TRANSCRIPT PREVIEW: {transcript_preview}")
    
    # 10. Text overlays (for campaigns with specific text/graphics)
    if detections.get('text_graphics'):
        text_overlays = [tg['text'] for tg in detections['text_graphics'] if tg.get('text')]
        if text_overlays:
            content_parts.append(f"TEXT OVERLAYS: {' | '.join(text_overlays[:10])}")  # Top 10
    
    return "\n\n".join(content_parts)


def get_video_insights_client() -> VideoInsightsClient:
    """Get Bedrock-based VideoInsightsClient for cross-region TwelveLabs models"""
    return VideoInsightsClient()


# Lambda handler for extracting video insights using SDK
def lambda_extract_insights(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to extract insights using Twelve Labs SDK and generate Cohere embeddings
    """
    try:
        # Debug: Log the received event structure
        logger.info(f"Received event: {json.dumps(event, indent=2)}")
        
        # Get details from previous step (updated for Bedrock)
        # Handle case where event might be nested or flat
        if 'video_url' not in event:
            logger.error(f"video_url not found in event. Available keys: {list(event.keys())}")
            # Try alternative structures
            if 'body' in event:
                event = event['body']
                logger.info(f"Using nested body structure: {json.dumps(event, indent=2)}")
            else:
                raise KeyError("video_url not found in event and no body structure available")
        
        video_url = event['video_url']
        video_title = event.get('video_title', '')  # Optional title for better search
        thumbnail_s3_key = event.get('thumbnail_s3_key')  # Thumbnail S3 key from InitiateVideoProcessing
        
        # New Bedrock-specific parameters
        video_bucket_west = event.get('video_bucket_west')
        video_key_west = event.get('video_key_west')
        marengo_model_id = event.get('marengo_model_id')
        pegasus_model_id = event.get('pegasus_model_id')
        
        # Initialize clients
        video_insights_client = get_video_insights_client()
        cohere_client = CohereEmbeddingClient()
        transcribe_client = TranscribeClient()
        
        # Start Amazon Transcribe job in parallel with Twelve Labs upload
        logger.info("Starting Amazon Transcribe job")
        transcribe_job_name = transcribe_client.start_transcription_job(
            video_url=video_url,
            s3_bucket=event['s3_bucket'],
            s3_key=event['s3_key']
        )
        
        # Process video using Bedrock
        video_id = video_insights_client.upload_video_and_wait(
            video_url=video_url,
            video_bucket_west=video_bucket_west,
            video_key_west=video_key_west
        )
        
        # Extract all insights using Bedrock Pegasus
        insights = video_insights_client.generate_comprehensive_insights(
            video_id=video_id,
            video_url=video_url,
            video_bucket_west=video_bucket_west,
            video_key_west=video_key_west
        )
        
        # Get video embeddings using Bedrock Marengo
        embeddings = video_insights_client.get_video_embeddings(
            video_id=video_id,
            video_url=video_url,
            # use the original east-region object for Marengo
            video_bucket_east=event['s3_bucket'],
            video_key_east=event['s3_key']
        )
        
        # Wait for and get Amazon Transcribe results
        logger.info("Waiting for Amazon Transcribe job to complete")
        transcribe_job = transcribe_client.wait_for_transcription_job(transcribe_job_name)
        
        # Parse transcription results
        transcription = transcribe_client.parse_transcription_results(
            transcribe_job['Transcript']['TranscriptFileUri']
        )
        
        # Add transcription to insights
        insights['transcription'] = transcription
        logger.info(f"Transcription complete: {len(transcription['full_text'])} characters")
        
        # Now call search_video_content with the transcription text for entity extraction
        search_results = video_insights_client.search_video_content(
            video_id=video_id, 
            transcription_text=transcription.get('full_text', '')
        )
        from pprint import pprint
        pprint(search_results)
        
        # Calculate average embedding for video_content_embedding field
        avg_embedding = None
        if embeddings:
            # Check if embeddings have 'embedding' or 'vector' key
            all_embeddings = []
            for seg in embeddings:
                if 'embedding' in seg:
                    all_embeddings.append(seg['embedding'])
                elif 'vector' in seg:
                    all_embeddings.append(seg['vector'])
                else:
                    logger.warning(f"Embedding segment missing 'embedding' or 'vector' key: {seg.keys()}")
            
            if all_embeddings:
                avg_embedding = np.mean(all_embeddings, axis=0).tolist()
            else:
                logger.error("No valid embeddings found in segments")
        
        # Prepare content for Cohere embedding
        content_for_embedding = prepare_content_for_embedding(insights, search_results)
        
        # Generate Cohere embedding for video content
        logger.info("Generating Cohere embedding for video content")
        cohere_embeddings = cohere_client.generate_embeddings(
            texts=[content_for_embedding],
            input_type="search_document"  # For indexing
        )
        
        # Get the first (and only) embedding
        pegasus_embedding = cohere_embeddings[0] if cohere_embeddings else None
        
        # Verify embedding dimension (should be 1024 for Cohere)
        if pegasus_embedding and len(pegasus_embedding) != 1024:
            logger.warning(f"Unexpected Cohere embedding dimension: {len(pegasus_embedding)}")
        
        # Validate all required data is present
        if not avg_embedding:
            raise ValueError("Failed to generate video content embedding from Marengo - cannot proceed without real embeddings")
        
        if not pegasus_embedding:
            raise ValueError("Failed to generate Cohere embedding - cannot proceed without real embeddings")
        
        if not insights:
            raise ValueError("No insights were generated from Pegasus - cannot proceed")
        
        if not embeddings or len(embeddings) == 0:
            raise ValueError("No video embeddings were retrieved from Marengo - cannot proceed without real embeddings")
        
        # Combine all data matching OpenSearch schema
        video_data = {
            'video_id': video_id,
            'video_title': video_title,
            'bedrock_integration': True,  # Using Bedrock instead of TwelveLabs SDK
            's3_bucket': event['s3_bucket'],
            's3_key': event['s3_key'],
            'thumbnail_s3_key': thumbnail_s3_key,
            'processing_timestamp': datetime.utcnow().isoformat(),
            
            # Embeddings
            'video_content_embedding': avg_embedding,  # Twelve Labs visual embedding
            'pegasus_insights_embedding': pegasus_embedding,  # Cohere text embedding
            'pegasus_content_for_embedding': content_for_embedding,  # The text that was embedded
            
            # Pegasus insights
            'pegasus_insights': insights,
            
            # Detections
            'detections': search_results,
            
            # Embedding metadata
            'embedding_metadata': {
                'video_embedding_model': MARENGO_MODEL_ID,
                'pegasus_embedding_model': COHERE_MODEL_ID,
                'video_embedding_timestamp': datetime.utcnow().isoformat(),
                'pegasus_embedding_timestamp': datetime.utcnow().isoformat(),
                'video_embeddings_present': len(embeddings) > 0,
                'pegasus_embeddings_present': pegasus_embedding is not None
            },
            
            # Content metadata (if provided)
            'content_metadata': event.get('content_metadata', {})
        }
        
        # Store raw data in S3 for backup
        s3_client = boto3.client('s3')
        metadata_key = f"metadata/{video_id}_insights.json"
        
        # Include raw embeddings in S3 backup but not in OpenSearch
        backup_data = video_data.copy()
        backup_data['_raw_video_embeddings'] = embeddings
        
        s3_client.put_object(
            Bucket=event['s3_bucket'],
            Key=metadata_key,
            Body=json.dumps(backup_data, indent=2),
            ContentType='application/json'
        )
        
        # Now index to OpenSearch
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, PRIMARY_REGION, 'aoss')
        
        # Parse hostname from full OpenSearch endpoint URL
        opensearch_host = OPENSEARCH_ENDPOINT.replace('https://', '').replace('http://', '')
        
        opensearch_client = OpenSearch(
            hosts=[{'host': opensearch_host, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # Index the document (OpenSearch Serverless doesn't support custom IDs or immediate refresh)
        opensearch_response = opensearch_client.index(
            index=INDEX_NAME,
            body=video_data
        )
        
        logger.info(f"Successfully indexed video {video_id} to OpenSearch")
        
        # Log the response structure for debugging
        response = {
            'statusCode': 200,
            'body': {
                **event,
                'video_id': video_id,
                'metadata_s3_key': metadata_key,
                'insights_extracted': True,
                'has_video_embeddings': len(embeddings) > 0,
                'has_transcription': 'transcription' in insights,
                'has_cohere_embedding': pegasus_embedding is not None,
                'opensearch_indexed': opensearch_response['result'] == 'created' or opensearch_response['result'] == 'updated',
                'content_for_embedding_length': len(content_for_embedding)
            }
        }
        
        logger.info(f"Lambda response structure: {json.dumps(response, default=str)}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting insights: {str(e)}")
        # Re-raise the exception to let Step Functions handle it
        # This will trigger the Catch block and go to HandleProcessingError
        raise

# Main handler function for AWS Lambda
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler - entry point for AWS Lambda
    """
    return lambda_extract_insights(event, context)