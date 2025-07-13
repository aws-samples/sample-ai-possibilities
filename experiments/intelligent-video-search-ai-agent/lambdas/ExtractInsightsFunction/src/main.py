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
COHERE_MODEL_ID = os.environ.get('COHERE_MODEL_ID', 'cohere.embed-english-v3')
NOVA_MODEL_ID = os.environ.get('NOVA_MODEL_ID', 'amazon.nova-lite-v1:0')
MARENGO_MODEL_ID = os.environ.get('MARENGO_MODEL_ID', 'marengo2.7')
NOVA_MAX_CHARS = int(os.environ.get('NOVA_MAX_CHARS', '350000'))
REGION = os.environ.get('REGION', 'us-east-1')

class BedrockClient:
    """Client for extracting brands, companies, and names using Amazon Bedrock's Nova model"""
    
    def __init__(self, region_name: str = REGION, model_id: str = NOVA_MODEL_ID, max_chars: int = NOVA_MAX_CHARS):
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
    
    def __init__(self, region_name: str = REGION):
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
    """Configuration for video processing with SDK"""
    twelve_labs_index_id: Optional[str] = None
    marengo_model: str = "marengo2.7"
    pegasus_model: str = "pegasus1.2"
    model_options: List[str] = None
    
    def __post_init__(self):
        if self.model_options is None:
            self.model_options = ["visual", "audio"]

class VideoInsightsClient:
    """Enhanced client wrapper for Twelve Labs SDK operations"""
    
    def __init__(self, api_key: str):
        self.client = TwelveLabs(api_key=api_key)
        self.api_key = api_key  # Store for direct API calls
        self.logger = logging.getLogger(__name__)

    def upload_video_and_wait(self, index_id: str, video_url: str, language: str = "en") -> str:
        """Upload video and wait for completion using SDK task monitoring"""
        try:
            self.logger.info(f"Creating upload task for index: {index_id}, video: {video_url}")
            # Create upload task using SDK
            task = self.client.task.create(
                index_id=index_id,
                url=video_url
            )
            
            self.logger.info(f"Started upload task: {task.id}")
            
            # Define progress callback
            def log_progress(task_obj: Task):
                self.logger.info(f"Task {task_obj.id} status: {task_obj.status}")
                if hasattr(task_obj, 'process'):
                    self.logger.info(f"Progress: {task_obj.process}")
            
            # Wait for completion with SDK monitoring
            task.wait_for_done(
                sleep_interval=10,
                callback=log_progress
            )
            
            if task.status != "ready":
                raise Exception(f"Video processing failed with status: {task.status}")
            
            self.logger.info(f"Video processing completed: {task.video_id}")
            return task.video_id
            
        except twelvelabs.APIStatusError as e:
            self.logger.error(f"Video upload failed: {e}")
            self.logger.error(f"API Error details - Status: {e.status_code}, Body: {e.body}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    
    def generate_comprehensive_insights(self, video_id: str, index_id: str) -> Dict[str, Any]:
        """Generate comprehensive insights using SDK methods"""
        insights = {}
        
        try:
            
            # Generate summary using SDK
            summary_result = self.client.summarize(
                video_id=video_id,
                type="summary",
                prompt="Provide a comprehensive content analysis including entity visibility, emotional impact, key messages, and content themes"
            )
            insights['summary'] = summary_result.summary
            
            # Generate chapters using SDK
            chapters_result = self.client.summarize(
                video_id=video_id,
                type="chapter"
            )
            insights['chapters'] = [
                {
                    'start': chapter.start,
                    'end': chapter.end,
                    'title': chapter.chapter_title,
                    'summary': getattr(chapter, 'chapter_summary', '')
                }
                for chapter in chapters_result.chapters
            ]
            
            # Generate highlights using SDK
            highlights_result = self.client.summarize(
                video_id=video_id,
                type="highlight",
                prompt="Identify key moments, important reveals, emotional peaks, and significant segments"
            )
            insights['highlights'] = [
                {
                    'start': highlight.start,
                    'end': highlight.end,
                    'highlight': highlight.highlight
                }
                for highlight in highlights_result.highlights
            ]
            
            # Generate custom text insights using SDK
            topics_result = self.client.analyze(
                video_id=video_id,
                prompt="List the main topics, themes, and key concepts discussed in this video"
            )
            insights['topics'] = topics_result.data
            
            # Generate hashtags using SDK
            hashtags_result = self.client.analyze(
                video_id=video_id,
                prompt="Generate relevant hashtags for social media based on video content"
            )
            insights['hashtags'] = hashtags_result.data
            
            # Generate sentiment analysis
            sentiment_result = self.client.analyze(
                video_id=video_id,
                prompt="Analyze the overall sentiment and emotional tone of this video. Include percentage breakdowns of positive, negative, and neutral content."
            )
            insights['sentiment_analysis'] = sentiment_result.data
            
            # Extract key content analytics
            analytics_result = self.client.analyze(
                video_id=video_id,
                prompt="Extract key content analytics: entity mentions count, important moments, topic coverage duration, and engagement indicators"
            )
            insights['content_analytics'] = analytics_result.data
            
        except twelvelabs.APIStatusError as e:
            self.logger.error(f"Insights generation failed: {e}")
            raise  # Fail fast - no partial data
        except Exception as e:
            self.logger.error(f"Insights generation error: {e}")
            raise
        
        return insights
    
    def get_video_embeddings(self, index_id: str, video_id: str) -> List[Dict[str, Any]]:
        """Get video embeddings using SDK"""
        try:
            # Retrieve embeddings using SDK
            embeddings_result = self.client.index.video.retrieve(
                index_id=index_id,
                id=video_id,
                embedding_option=["visual-text", "audio"]
            )
            
            # Format embeddings for storage
            formatted_embeddings = []
            
            # Check if embeddings exist
            if embeddings_result.embedding:
                # Access segments through the correct path
                for segment in embeddings_result.embedding.video_embedding.segments:
                    formatted_embeddings.append({
                        'embedding': segment.embeddings_float,
                        'start_offset_sec': segment.start_offset_sec,
                        'end_offset_sec': segment.end_offset_sec,
                        'embedding_scope': segment.embedding_scope
                    })
            
            return formatted_embeddings
            
        except twelvelabs.APIStatusError as e:
            self.logger.error(f"Embeddings retrieval failed: {e}")
            raise  # Fail fast - embeddings are critical
        except Exception as e:
            self.logger.error(f"Embeddings error: {e}")
            raise
    
    def search_video_content(self, index_id: str, video_id: str, transcription_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for specific content within the video using SDK and extract entities from transcription
        
        Args:
            index_id: Twelve Labs index ID
            video_id: Video ID from Twelve Labs
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
                
                # Store entities in the same structure as the previous logo detection
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
    
    return VideoInsightsClient(api_key)


# Lambda handler for extracting video insights using SDK
def lambda_extract_insights(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to extract insights using Twelve Labs SDK and generate Cohere embeddings
    """
    try:
        # Get details from previous step
        index_id = event['twelve_labs_index_id']
        video_url = event['video_url']
        video_title = event.get('video_title', '')  # Optional title for better search
        thumbnail_s3_key = event.get('thumbnail_s3_key')  # Thumbnail S3 key from InitiateVideoProcessing
        
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
        
        # Upload video and wait for completion using SDK
        video_id = video_insights_client.upload_video_and_wait(index_id, video_url)
        
        # Extract all insights using SDK
        insights = video_insights_client.generate_comprehensive_insights(video_id, index_id)
        embeddings = video_insights_client.get_video_embeddings(index_id, video_id)
        
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
            index_id, 
            video_id, 
            transcription_text=transcription.get('full_text', '')
        )
        from pprint import pprint
        pprint(search_results)
        
        # Calculate average embedding for video_content_embedding field
        avg_embedding = None
        if embeddings:
            all_embeddings = [seg['embedding'] for seg in embeddings]
            avg_embedding = np.mean(all_embeddings, axis=0).tolist()
        
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
            raise ValueError("Failed to generate video content embedding - cannot proceed")
        
        if not pegasus_embedding:
            raise ValueError("Failed to generate Cohere embedding - cannot proceed")
        
        if not insights:
            raise ValueError("No insights were generated - cannot proceed")
        
        if not embeddings:
            raise ValueError("No video embeddings were retrieved - cannot proceed")
        
        # Combine all data matching OpenSearch schema
        video_data = {
            'video_id': video_id,
            'video_title': video_title,
            'twelve_labs_index_id': index_id,
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
        auth = AWSV4SignerAuth(credentials, REGION, 'aoss')
        
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