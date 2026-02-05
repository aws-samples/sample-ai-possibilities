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
PRIMARY_REGION = os.environ.get('PRIMARY_REGION', 'us-east-1')  # All Nova 2 models are in us-east-1
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'video-insights-rag')

# Nova 2 Model IDs (all in us-east-1)
NOVA_LITE_MODEL_ID = os.environ.get('NOVA_LITE_MODEL_ID', 'global.amazon.nova-2-lite-v1:0')  # For NER
NOVA_OMNI_MODEL_ID = os.environ.get('NOVA_OMNI_MODEL_ID', 'global.amazon.nova-2-omni-v1:0')  # For transcription & video understanding
NOVA_EMBEDDING_MODEL_ID = os.environ.get('NOVA_EMBEDDING_MODEL_ID', 'amazon.nova-2-multimodal-embeddings-v1:0')  # For embeddings
NOVA_EMBEDDING_DIMENSION = int(os.environ.get('NOVA_EMBEDDING_DIMENSION', '3072'))
NOVA_MAX_CHARS = int(os.environ.get('NOVA_MAX_CHARS', '350000'))

class BedrockClient:
    """Client for extracting brands, companies, and names using Amazon Bedrock's Nova Lite 2.0 model"""

    def __init__(self, region_name: str = PRIMARY_REGION, model_id: str = None, max_chars: int = NOVA_MAX_CHARS):
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name=region_name)
        self.model_id = model_id or NOVA_LITE_MODEL_ID
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


class NovaEmbeddingClient:
    """Client for generating embeddings using Amazon Nova 2 Multimodal Embeddings"""

    def __init__(self, region_name: str = PRIMARY_REGION):
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name=region_name)
        self.model_id = NOVA_EMBEDDING_MODEL_ID
        self.dimension = NOVA_EMBEDDING_DIMENSION
        self.logger = logging.getLogger(__name__)

    def generate_text_embeddings(self, texts: List[str], embedding_purpose: str = "GENERIC_INDEX") -> List[List[float]]:
        """
        Generate embeddings for text content using Nova 2 Multimodal Embeddings

        Args:
            texts: List of text strings to embed
            embedding_purpose: Purpose of embedding - GENERIC_INDEX, SEARCH, RETRIEVAL, CLASSIFICATION, CLUSTERING

        Returns:
            List of embedding vectors (float type)
        """
        embeddings = []
        try:
            for text in texts:
                # Nova embeddings has larger token limit but we still truncate very long texts
                truncated_text = text[:8000] if len(text) > 8000 else text

                request_body = {
                    'taskType': 'SINGLE_EMBEDDING',
                    'singleEmbeddingParams': {
                        'embeddingPurpose': embedding_purpose,
                        'embeddingDimension': self.dimension,
                        'text': {
                            'truncationMode': 'END',
                            'value': truncated_text
                        },
                    },
                }

                response = self.bedrock.invoke_model(
                    body=json.dumps(request_body),
                    modelId=self.model_id,
                    accept='application/json',
                    contentType='application/json'
                )

                response_body = json.loads(response.get('body').read())
                # Nova 2 returns embeddings array with objects containing embedding
                embeddings_data = response_body.get('embeddings', [])
                embedding = embeddings_data[0].get('embedding', []) if embeddings_data else []
                embeddings.append(embedding)

            self.logger.info(f"Generated {len(embeddings)} text embeddings with Nova (dimension: {self.dimension})")
            return embeddings

        except Exception as e:
            self.logger.error(f"Error generating Nova text embeddings: {e}")
            raise

    def generate_video_embeddings_async(self, video_s3_uri: str, output_bucket: str, segment_duration: int = 15) -> Dict[str, Any]:
        """
        Generate video embeddings using Nova 2 Multimodal Embeddings (async API for videos)

        Args:
            video_s3_uri: S3 URI of the video file
            output_bucket: S3 bucket for embedding output
            segment_duration: Duration in seconds for video segmentation

        Returns:
            Dictionary with invocation ARN and output location
        """
        try:
            invocation_id = f"nova-embed-{uuid.uuid4().hex[:8]}"
            output_s3_uri = f"s3://{output_bucket}/embeddings/{invocation_id}/"

            # Determine video format from URI
            video_format = video_s3_uri.split('.')[-1].lower()
            if video_format not in ['mp4', 'mov', 'mkv', 'webm', 'flv', 'mpeg', 'mpg', 'wmv', '3gp']:
                video_format = 'mp4'  # Default to mp4

            model_input = {
                'taskType': 'SEGMENTED_EMBEDDING',
                'segmentedEmbeddingParams': {
                    'embeddingPurpose': 'GENERIC_INDEX',
                    'embeddingDimension': self.dimension,
                    'video': {
                        'format': video_format,
                        'embeddingMode': 'AUDIO_VIDEO_COMBINED',  # Combined embedding (only valid mode)
                        'source': {
                            's3Location': {'uri': video_s3_uri}
                        },
                        'segmentationConfig': {
                            'durationSeconds': segment_duration
                        },
                    },
                },
            }

            self.logger.info(f"Starting async Nova video embedding: {video_s3_uri}")

            response = self.bedrock.start_async_invoke(
                modelId=self.model_id,
                modelInput=model_input,
                outputDataConfig={
                    's3OutputDataConfig': {
                        's3Uri': output_s3_uri
                    }
                },
            )

            return {
                'invocation_arn': response.get('invocationArn'),
                'output_s3_uri': output_s3_uri,
                'invocation_id': invocation_id
            }

        except Exception as e:
            self.logger.error(f"Error starting Nova video embedding: {e}")
            raise

    def wait_for_video_embedding(self, invocation_arn: str, max_wait_time: int = 300) -> str:
        """
        Wait for async video embedding to complete

        Args:
            invocation_arn: The invocation ARN from start_async_invoke
            max_wait_time: Maximum wait time in seconds

        Returns:
            Status of the invocation (Completed, Failed, etc.)
        """
        check_interval = 10
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            status_response = self.bedrock.get_async_invoke(invocationArn=invocation_arn)
            status = status_response['status']

            self.logger.info(f"Nova embedding status: {status}")

            if status == 'Completed':
                return status
            elif status == 'Failed':
                error_msg = status_response.get('failureMessage', 'Unknown error')
                raise Exception(f"Nova embedding failed: {error_msg}")

            time.sleep(check_interval)
            elapsed_time += check_interval

        raise Exception(f"Nova embedding timed out after {max_wait_time} seconds")

    def parse_video_embedding_results(self, output_s3_uri: str, bucket: str) -> List[Dict[str, Any]]:
        """
        Parse video embedding results from S3

        Nova 2 Multimodal Embeddings async output format:
        - segmented-embedding-result.json: Manifest with status
        - embedding-video.jsonl: JSONL file with one embedding per line

        Each JSONL line format:
        {
            "embedding": number[],
            "segmentMetadata": {
                "segmentIndex": number,
                "segmentStartSeconds": number,
                "segmentEndSeconds": number
            },
            "status": "SUCCESS" | "FAILURE"
        }

        Args:
            output_s3_uri: S3 URI where results were written
            bucket: S3 bucket name

        Returns:
            List of embedding segments with vectors and timestamps
        """
        try:
            s3_client = boto3.client('s3', region_name=PRIMARY_REGION)
            s3_prefix = output_s3_uri.replace(f"s3://{bucket}/", "")

            self.logger.info(f"Looking for embedding results at: s3://{bucket}/{s3_prefix}")
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=s3_prefix)

            if 'Contents' not in response:
                self.logger.error(f"No output files found at prefix: {s3_prefix}")
                raise Exception("No output files found from Nova embedding")

            # Log all found files for debugging
            all_files = [obj['Key'] for obj in response['Contents']]
            self.logger.info(f"Found {len(all_files)} files in embedding output: {all_files}")

            embeddings = []
            for obj in response['Contents']:
                key = obj['Key']
                self.logger.info(f"Checking file: {key}")

                # Skip manifest files
                if 'manifest' in key.lower() or 'result.json' in key.lower():
                    self.logger.info(f"Skipping manifest/result file: {key}")
                    continue

                # Handle JSONL files (Nova 2 async output format)
                if key.endswith('.jsonl'):
                    self.logger.info(f"Processing JSONL file: {key}")
                    obj_response = s3_client.get_object(Bucket=bucket, Key=key)
                    content = obj_response['Body'].read().decode('utf-8')

                    # Parse each line as separate JSON object
                    for line_num, line in enumerate(content.strip().split('\n')):
                        if not line.strip():
                            continue
                        try:
                            segment_data = json.loads(line)

                            # Check status
                            if segment_data.get('status') == 'FAILURE':
                                self.logger.warning(f"Segment {line_num} failed: {segment_data.get('failureReason', 'Unknown')}")
                                continue

                            # Extract embedding and metadata
                            embedding_vector = segment_data.get('embedding', [])
                            segment_metadata = segment_data.get('segmentMetadata', {})

                            if embedding_vector:
                                embeddings.append({
                                    'embedding': embedding_vector,
                                    'start_time': segment_metadata.get('segmentStartSeconds', 0),
                                    'end_time': segment_metadata.get('segmentEndSeconds', 0),
                                    'segment_index': segment_metadata.get('segmentIndex', line_num),
                                    'scope': 'video'
                                })
                                self.logger.info(f"Parsed segment {line_num}: {len(embedding_vector)} dim, "
                                               f"{segment_metadata.get('segmentStartSeconds', 0)}-{segment_metadata.get('segmentEndSeconds', 0)}s")
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"Failed to parse JSONL line {line_num}: {e}")

                    self.logger.info(f"Parsed {len(embeddings)} embeddings from JSONL file")

                # Handle regular JSON files (fallback for other formats)
                elif key.endswith('.json'):
                    obj_response = s3_client.get_object(Bucket=bucket, Key=key)
                    content = json.loads(obj_response['Body'].read().decode('utf-8'))

                    # Log the structure of the content for debugging
                    self.logger.info(f"JSON file {key} has keys: {list(content.keys())}")

                    # Parse Nova embedding output format - check multiple possible formats
                    if 'embeddingResults' in content:
                        # This is the result manifest - skip it but log info
                        self.logger.info(f"Found result manifest with {len(content.get('embeddingResults', []))} results")
                        for result in content.get('embeddingResults', []):
                            self.logger.info(f"  Result: type={result.get('embeddingType')}, status={result.get('status')}, output={result.get('outputFileUri')}")
                    elif 'segments' in content:
                        self.logger.info(f"Found 'segments' key with {len(content['segments'])} segments")
                        for segment in content['segments']:
                            embeddings.append({
                                'embedding': segment.get('embedding', []),
                                'start_time': segment.get('startOffsetSec', 0),
                                'end_time': segment.get('endOffsetSec', 0),
                                'scope': 'video'
                            })
                    elif 'embeddings' in content:
                        # Nova 2 synchronous format
                        self.logger.info(f"Found 'embeddings' key with {len(content['embeddings'])} items")
                        for item in content['embeddings']:
                            emb_vector = item.get('embedding', [])
                            embeddings.append({
                                'embedding': emb_vector,
                                'start_time': 0,
                                'end_time': 0,
                                'scope': 'video'
                            })
                    elif 'embedding' in content:
                        self.logger.info(f"Found single 'embedding' key")
                        embeddings.append({
                            'embedding': content['embedding'],
                            'start_time': 0,
                            'end_time': 0,
                            'scope': 'video'
                        })
                    else:
                        # Log first 500 chars of content to understand the format
                        content_preview = str(content)[:500]
                        self.logger.warning(f"Unknown JSON format in {key}: {content_preview}")

            self.logger.info(f"Parsed {len(embeddings)} video embedding segments total")
            return embeddings

        except Exception as e:
            self.logger.error(f"Error parsing Nova embedding results: {e}")
            raise

class NovaOmniTranscriptionClient:
    """Client for transcription using Amazon Nova Omni model"""

    def __init__(self, region_name: str = PRIMARY_REGION):
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.model_id = NOVA_OMNI_MODEL_ID
        self.logger = logging.getLogger(__name__)

    def extract_audio_from_video(self, s3_bucket: str, s3_key: str) -> bytes:
        """
        Download video from S3 and extract audio for transcription using ffmpeg.
        The ffmpeg binary is provided by a Lambda layer at /opt/bin/ffmpeg.
        """
        try:
            import subprocess

            # Find ffmpeg binary - check multiple locations
            # Priority: 1) Environment variable, 2) Bundled binary, 3) Lambda layer, 4) System PATH
            ffmpeg_path = None
            search_paths = [
                os.environ.get('FFMPEG_PATH', ''),  # Environment override
                '/var/task/bin/ffmpeg',              # Bundled with Lambda function
                '/opt/bin/ffmpeg',                   # Lambda layer location
            ]

            for path in search_paths:
                if path and os.path.exists(path) and os.access(path, os.X_OK):
                    ffmpeg_path = path
                    break

            if not ffmpeg_path:
                # Fallback to system PATH
                ffmpeg_path = 'ffmpeg'
                self.logger.warning("ffmpeg not found in expected locations, trying system PATH")
            else:
                self.logger.info(f"Using ffmpeg at: {ffmpeg_path}")

            # Download video from S3
            self.logger.info(f"Downloading video from s3://{s3_bucket}/{s3_key}")
            response = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            video_content = response['Body'].read()
            self.logger.info(f"Downloaded video: {len(video_content)} bytes")

            # Detect video format from extension for proper handling
            video_ext = os.path.splitext(s3_key)[1].lower() or '.mp4'

            # Write to temp file for ffmpeg processing (Lambda uses /tmp)
            video_path = f"/tmp/video_input{video_ext}"
            audio_path = "/tmp/audio_output.mp3"

            with open(video_path, 'wb') as video_file:
                video_file.write(video_content)

            self.logger.info(f"Video written to {video_path}")

            # Extract audio using ffmpeg
            # -vn: No video output
            # -acodec libmp3lame: MP3 encoding
            # -ar 16000: 16kHz sample rate (good for speech)
            # -ac 1: Mono channel
            # -b:a 64k: 64kbps bitrate (sufficient for speech)
            cmd = [
                ffmpeg_path, '-i', video_path,
                '-vn',
                '-acodec', 'libmp3lame',
                '-ar', '16000',
                '-ac', '1',
                '-b:a', '64k',
                '-y',  # Overwrite output
                audio_path
            ]

            self.logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"ffmpeg stderr: {result.stderr}")
                raise Exception(f"ffmpeg failed: {result.stderr}")

            self.logger.info(f"ffmpeg completed successfully")

            # Read audio bytes
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()

            # Cleanup temp files
            try:
                os.unlink(video_path)
                os.unlink(audio_path)
            except Exception as cleanup_error:
                self.logger.warning(f"Cleanup failed: {cleanup_error}")

            self.logger.info(f"Extracted audio: {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            self.logger.error(f"Failed to extract audio: {e}")
            raise

    def transcribe_audio(self, audio_bytes: bytes, audio_format: str = "mp3") -> Dict[str, Any]:
        """
        Transcribe audio using Nova Omni model with the 'audio' content type.

        This is the correct way to transcribe audio with Nova Omni - the 'video' content
        type only processes visual frames, not audio.

        See: https://github.com/aws-samples/sample-building-intelligent-multimodal-applications-with-Nova

        Args:
            audio_bytes: Raw audio bytes (extracted from video via ffmpeg)
            audio_format: Audio format (mp3, wav, etc.)

        Returns:
            Dictionary with transcription results including full_text, segments, and speaker_labels
        """
        try:
            self.logger.info(f"Transcribing audio: {len(audio_bytes)} bytes, format: {audio_format}")

            # Transcription prompt following AWS Nova sample format
            # Requests structured XML with speaker identification and timestamps
            transcription_prompt = """For each speaker turn segment, transcribe, assign a speaker label, start and end timestamps. You must follow the exact XML format shown in the example below:
<segment><transcription speaker="speaker_id" start="start_time" end="end_time">transcription_text</transcription></segment>

Provide a complete transcription of the entire audio with speaker identification and timestamps."""

            # Build request for Nova Omni with audio content type
            # Note: Pass raw bytes directly - boto3 handles the encoding
            request_body = {
                "modelId": self.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "audio": {
                                    "format": audio_format,
                                    "source": {
                                        "bytes": audio_bytes  # Raw bytes, not base64
                                    }
                                }
                            },
                            {
                                "text": transcription_prompt
                            }
                        ]
                    }
                ],
                "inferenceConfig": {
                    "temperature": 0.5,
                    "maxTokens": 16000  # Increased for longer audio
                }
            }

            self.logger.info("Invoking Nova Omni for audio transcription...")

            response = self.bedrock.converse(**request_body)

            # Extract response text
            response_text = response['output']['message']['content'][0]['text']
            self.logger.info(f"Nova Omni audio transcription response length: {len(response_text)} chars")

            # Log first part of response for debugging
            self.logger.info(f"Transcription response preview: {response_text[:1000]}...")

            # Log usage info if available
            if 'usage' in response:
                usage = response['usage']
                self.logger.info(f"Token usage - Input: {usage.get('inputTokens', 'N/A')}, Output: {usage.get('outputTokens', 'N/A')}")

            # Parse the XML response
            return self._parse_transcription_response(response_text)

        except Exception as e:
            self.logger.error(f"Audio transcription failed: {e}")
            self.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            raise

    def _parse_transcription_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the transcription response from Nova Omni - handles AWS workshop XML format"""
        try:
            import re

            self.logger.info(f"Raw transcription response length: {len(response_text)} chars")

            segments = []
            full_text_parts = []

            # AWS Workshop format: <segment><transcription speaker="X" start="Y" end="Z">text</transcription></segment>
            workshop_pattern = r'<segment>\s*<transcription\s+speaker=["\']([^"\']+)["\']\s+start=["\']([^"\']+)["\']\s+end=["\']([^"\']+)["\']>\s*(.*?)\s*</transcription>\s*</segment>'

            for match in re.finditer(workshop_pattern, response_text, re.DOTALL):
                speaker = match.group(1).strip()
                try:
                    start_time = float(match.group(2).strip())
                    end_time = float(match.group(3).strip())
                except ValueError:
                    start_time = 0.0
                    end_time = 0.0
                text = match.group(4).strip()

                segments.append({
                    'speaker': speaker,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text
                })
                full_text_parts.append(text)

            if segments:
                self.logger.info(f"Parsed {len(segments)} segments from AWS workshop XML format")

            # Fallback: Try alternate XML format with separate tags
            if not segments:
                alt_pattern = r'<segment>\s*<speaker>(.*?)</speaker>\s*<start>(.*?)</start>\s*<end>(.*?)</end>\s*<text>(.*?)</text>\s*</segment>'
                for match in re.finditer(alt_pattern, response_text, re.DOTALL):
                    speaker = match.group(1).strip()
                    try:
                        start_time = float(match.group(2).strip())
                        end_time = float(match.group(3).strip())
                    except ValueError:
                        start_time = 0.0
                        end_time = 0.0
                    text = match.group(4).strip()
                    segments.append({
                        'speaker': speaker,
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': text
                    })
                    full_text_parts.append(text)
                if segments:
                    self.logger.info(f"Parsed {len(segments)} segments from alternate XML format")

            # Fallback: Try "Speaker N:" plain text format
            if not segments:
                self.logger.info("Trying plain text Speaker format...")
                speaker_pattern = r'(?:Speaker\s*(\d+)|(\w+)):\s*([^\n]+(?:\n(?!(?:Speaker|[A-Z][a-z]+):)[^\n]+)*)'
                speaker_matches = list(re.finditer(speaker_pattern, response_text))

                if speaker_matches:
                    for match in speaker_matches:
                        speaker_num = match.group(1) or match.group(2)
                        speaker = f"Speaker {speaker_num}" if speaker_num and speaker_num.isdigit() else speaker_num
                        text = match.group(3).strip()
                        segments.append({
                            'speaker': speaker,
                            'start_time': 0.0,
                            'end_time': 0.0,
                            'text': text
                        })
                        full_text_parts.append(text)
                    self.logger.info(f"Parsed {len(segments)} segments from Speaker format")

            # Final fallback: Use raw text
            if not segments:
                self.logger.info("Using raw text fallback...")
                # Remove XML tags but keep the content
                full_text = re.sub(r'<[^>]+>', ' ', response_text)
                full_text = re.sub(r'\s+', ' ', full_text).strip()

                if full_text:
                    segments = [{
                        'speaker': 'Speaker 1',
                        'start_time': 0.0,
                        'end_time': 0.0,
                        'text': full_text
                    }]
                    full_text_parts = [full_text]
                self.logger.info(f"Using cleaned plain text: {len(full_text)} chars")

            # Combine all text parts into full transcription
            full_text = ' '.join(full_text_parts)

            self.logger.info(f"Final transcription length: {len(full_text)} chars")
            self.logger.info(f"Transcription preview: {full_text[:500]}...")

            # Build speaker labels from segments
            speaker_labels = []
            for seg in segments:
                speaker_labels.append({
                    'speaker': seg['speaker'],
                    'start_time': seg['start_time'],
                    'end_time': seg['end_time']
                })

            result = {
                'full_text': full_text,
                'segments': segments,
                'speaker_labels': speaker_labels
            }

            self.logger.info(f"Parsed transcription: {len(full_text)} chars, {len(segments)} segments")
            return result

        except Exception as e:
            self.logger.warning(f"Failed to parse transcription, returning raw text: {e}")
            return {
                'full_text': response_text,
                'segments': [{'speaker': 'Speaker 1', 'start_time': 0.0, 'end_time': 0.0, 'text': response_text}],
                'speaker_labels': [{'speaker': 'Speaker 1', 'start_time': 0.0, 'end_time': 0.0}]
            }

    def transcribe_from_s3(self, s3_bucket: str, s3_key: str) -> Dict[str, Any]:
        """
        Transcribe video from S3 using Nova Omni with audio extraction.

        Nova Omni's 'video' content type only processes visual frames (1 FPS), not audio.
        For transcription, we must:
        1. Download the video from S3
        2. Extract audio using ffmpeg
        3. Send audio bytes to Nova Omni using the 'audio' content type

        See: https://github.com/aws-samples/sample-building-intelligent-multimodal-applications-with-Nova

        Args:
            s3_bucket: S3 bucket containing the video
            s3_key: S3 key of the video file

        Returns:
            Dictionary with transcription results
        """
        self.logger.info(f"Starting Nova Omni transcription for s3://{s3_bucket}/{s3_key}")
        self.logger.info("Using ffmpeg to extract audio, then Nova Omni audio content type for transcription")

        try:
            # Step 1: Extract audio from video using ffmpeg
            self.logger.info("Extracting audio from video with ffmpeg...")
            audio_bytes = self.extract_audio_from_video(s3_bucket, s3_key)
            self.logger.info(f"Audio extracted: {len(audio_bytes)} bytes")

            # Step 2: Transcribe audio using Nova Omni with audio content type
            self.logger.info("Sending audio to Nova Omni for transcription...")
            result = self.transcribe_audio(audio_bytes, audio_format="mp3")

            self.logger.info(f"Transcription complete: {len(result.get('full_text', ''))} characters")
            return result

        except Exception as e:
            self.logger.error(f"Nova Omni transcription failed: {e}")
            self.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            # Return empty transcription on failure rather than blocking the pipeline
            return {
                'full_text': '',
                'segments': [],
                'speaker_labels': [],
                'error': str(e)
            }

@dataclass
class VideoProcessingConfig:
    """Configuration for video processing with Nova 2 models (all in us-east-1)"""
    nova_omni_model_id: str = "global.amazon.nova-2-omni-v1:0"  # For video understanding
    nova_embedding_model_id: str = "amazon.nova-2-multimodal-embeddings-v1:0"  # For embeddings
    region: str = "us-east-1"
    model_options: List[str] = None

    def __post_init__(self):
        if self.model_options is None:
            self.model_options = ["visual"]  # Video only, not audio (per user requirement)


class VideoInsightsClient:
    """Nova 2 based video insights client - replaces TwelveLabs Pegasus/Marengo"""

    def __init__(self, region: str = PRIMARY_REGION):
        # Single Bedrock client - all Nova 2 models are in us-east-1
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.region = region
        self.logger = logging.getLogger(__name__)
        self.nova_embedding_client = NovaEmbeddingClient(region_name=region)

    def upload_video_and_wait(self, video_url: str, s3_bucket: str, s3_key: str,
                               language: str = "en", video_id: str = None) -> str:
        """
        Process video with Nova 2 models.
        Uses provided video_id or generates one based on the S3 location.
        """
        try:
            # Use provided video_id (from InitiateVideoProcessing) or generate fallback
            if not video_id:
                import hashlib
                video_id = hashlib.md5(f"{s3_bucket}_{s3_key}".encode()).hexdigest()[:16]
                self.logger.warning(f"No video_id provided, generated fallback: {video_id}")

            self.logger.info(f"Processing video with Nova 2 - Video ID: {video_id}")
            self.logger.info(f"S3 location: s3://{s3_bucket}/{s3_key}")

            return video_id

        except Exception as e:
            self.logger.error(f"Video processing failed: {e}")
            raise
    
    
    def generate_comprehensive_insights(self, video_id: str, video_url: str, s3_bucket: str, s3_key: str) -> Dict[str, Any]:
        """Generate comprehensive insights using Nova Omni model (video only, no audio)"""
        insights = {}

        try:
            video_s3_uri = f"s3://{s3_bucket}/{s3_key}"

            # 1. SUMMARY - Comprehensive visual analysis with structured output
            summary_prompt = """You are an expert video analyst. Analyze the VISUAL content of this video (ignore audio) and provide a comprehensive analysis.

Think through each aspect systematically:

1. CONTENT OVERVIEW: What is this video about? What is the main subject or narrative?
2. VISUAL STYLE: Describe the cinematography, camera angles, lighting, color grading, and production quality.
3. KEY VISUAL ELEMENTS: What are the most prominent objects, people, locations, or graphics shown?
4. VISUAL STORYTELLING: How does the video use visual techniques to convey its message?
5. TARGET AUDIENCE: Based on visual style and content, who is this video likely intended for?
6. BRAND/MARKETING ELEMENTS: Are there visible logos, products, text overlays, or call-to-actions?
7. EMOTIONAL IMPACT: What emotions do the visuals evoke? How effective is the visual communication?

Provide a detailed, well-structured summary (300-500 words) that captures the essence of this video's visual content."""
            summary_result = self._invoke_nova_omni_video(summary_prompt, video_s3_uri)
            insights['summary'] = summary_result

            # 2. CHAPTERS - Scene-by-scene breakdown with timestamps
            chapters_prompt = """Analyze this video's visual content and divide it into logical chapters based on scene changes, topic shifts, or visual transitions.

For EACH chapter, provide:
- Approximate start time (in seconds)
- Approximate end time (in seconds)
- A concise, descriptive title (3-7 words)
- A brief summary of the visual content (1-2 sentences)

Guidelines:
- Identify natural scene transitions, location changes, or topic shifts
- Aim for 3-8 chapters depending on video length and content variety
- Chapter titles should be informative and engaging
- Base timestamps on visual cues and scene changes

Return ONLY a valid JSON array in this exact format:
[
  {"start": 0, "end": 30, "title": "Opening Scene Title", "summary": "Description of what happens visually"},
  {"start": 30, "end": 75, "title": "Next Scene Title", "summary": "Description of this segment"}
]"""
            chapters_result = self._invoke_nova_omni_video(chapters_prompt, video_s3_uri)
            insights['chapters'] = self._parse_chapters_response(chapters_result)

            # 3. HIGHLIGHTS - Key visual moments with impact analysis
            highlights_prompt = """Identify the 5-10 most visually significant and engaging moments in this video.

For each highlight, analyze:
- The approximate timestamp (start and end in seconds)
- What makes this moment visually impactful or memorable
- The type of highlight (e.g., "key reveal", "emotional peak", "visual climax", "important demonstration", "brand moment")

Focus on moments that would:
- Capture viewer attention
- Be shareable on social media
- Represent key information or emotional peaks
- Showcase the video's best visual content

Return ONLY a valid JSON array:
[
  {"start": 10, "end": 18, "highlight": "Dramatic product reveal with slow-motion close-up", "type": "key reveal"},
  {"start": 45, "end": 52, "highlight": "Emotional reaction shot showing customer satisfaction", "type": "emotional peak"}
]"""
            highlights_result = self._invoke_nova_omni_video(highlights_prompt, video_s3_uri)
            insights['highlights'] = self._parse_highlights_response(highlights_result)

            # 4. TOPICS AND THEMES - Structured topic extraction
            topics_prompt = """Analyze the visual content of this video and extract all topics, themes, and concepts.

Categorize your findings:

PRIMARY TOPICS (main subjects directly shown):
- List 2-4 main topics that are central to the video's visual content

SECONDARY TOPICS (supporting or related subjects):
- List 3-6 additional topics that appear but aren't the main focus

VISUAL THEMES (stylistic or conceptual patterns):
- List design themes, moods, or recurring visual motifs

INDUSTRY/CATEGORY:
- What industry or content category does this video belong to?

KEYWORDS:
- List 10-15 keywords that describe the visual content for search optimization

Format your response with clear headings and bullet points."""
            topics_result = self._invoke_nova_omni_video(topics_prompt, video_s3_uri)
            insights['topics'] = topics_result

            # 5. HASHTAGS - Social media optimized tags
            hashtags_prompt = """Based on the visual content of this video, generate relevant hashtags for social media optimization.

Create hashtags in these categories:

CONTENT HASHTAGS (5-8): Specific to what's shown in the video
INDUSTRY HASHTAGS (3-5): Related to the business sector or field
STYLE HASHTAGS (3-4): Describing the visual style or format
TRENDING/ENGAGEMENT HASHTAGS (3-4): Popular tags that fit the content
BRANDED HASHTAGS (1-3): If visible brands or products are shown

Guidelines:
- Use lowercase without spaces (e.g., #productreview not #Product Review)
- Mix popular and niche hashtags
- Keep hashtags relevant to visual content only

Return as a comma-separated list of hashtags, organized by category with labels."""
            hashtags_result = self._invoke_nova_omni_video(hashtags_prompt, video_s3_uri)
            insights['hashtags'] = hashtags_result

            # 6. SENTIMENT ANALYSIS - Deep visual emotion analysis
            sentiment_prompt = """Perform a detailed visual sentiment and emotional analysis of this video.

Analyze these visual elements:

1. FACIAL EXPRESSIONS & BODY LANGUAGE:
   - What emotions are people displaying?
   - How do body language cues contribute to the mood?

2. COLOR PSYCHOLOGY:
   - What colors dominate the video?
   - How do the colors affect emotional perception?
   - Is the color grading warm, cool, neutral, or dramatic?

3. VISUAL COMPOSITION & PACE:
   - Are shots calm and steady or dynamic and energetic?
   - How do camera movements contribute to emotion?
   - What is the visual rhythm and pacing?

4. SETTING & ATMOSPHERE:
   - What mood does the environment create?
   - Is the setting professional, casual, dramatic, or intimate?

OVERALL ASSESSMENT:
- Primary sentiment: [positive/negative/neutral/mixed]
- Confidence level: [high/medium/low]
- Dominant emotions evoked: [list 3-5 emotions]
- Emotional arc: Does the sentiment change throughout the video?

Provide specific visual evidence for your analysis."""
            sentiment_result = self._invoke_nova_omni_video(sentiment_prompt, video_s3_uri)
            insights['sentiment_analysis'] = sentiment_result

            # 7. CONTENT ANALYTICS - Technical visual analysis
            analytics_prompt = """Extract detailed visual content analytics from this video for content optimization.

Analyze and report on:

1. SCENE COMPOSITION:
   - Number of distinct scenes/locations
   - Primary shot types used (close-up, wide, medium, etc.)
   - Camera movement patterns (static, pan, zoom, tracking)

2. VISUAL ELEMENTS INVENTORY:
   - People: Count and describe (presenters, actors, crowds)
   - Products/Objects: List key items shown
   - Text/Graphics: Any on-screen text, titles, or overlays
   - Locations: Interior/exterior, specific settings

3. PRODUCTION QUALITY INDICATORS:
   - Estimated production level (professional, semi-pro, amateur)
   - Lighting quality and style
   - Visual effects or post-production elements

4. CONTENT STRUCTURE:
   - Video format (tutorial, advertisement, interview, etc.)
   - Presence of intro/outro sequences
   - Use of B-roll or cutaway shots
   - Pacing assessment (fast, moderate, slow)

5. ENGAGEMENT PREDICTORS:
   - Visual hooks in first 5 seconds
   - Attention-grabbing elements throughout
   - Call-to-action visibility

Provide quantitative estimates where possible."""
            analytics_result = self._invoke_nova_omni_video(analytics_prompt, video_s3_uri)
            insights['content_analytics'] = analytics_result

            # 8. VISUAL OBJECTS & ACTIONS - Additional detailed analysis
            objects_prompt = """Identify and catalog all significant visual objects and actions in this video.

OBJECTS DETECTION:
- List all clearly visible objects, products, or items
- Note any brand names, logos, or text visible on objects
- Identify any technology, tools, or equipment shown

PEOPLE ANALYSIS:
- How many people appear?
- Demographics visible (approximate age groups, professional roles)
- Attire and presentation style

ACTIONS & ACTIVITIES:
- What actions are people performing?
- What processes or demonstrations are shown?
- Any recurring actions or patterns?

LOCATION INDICATORS:
- Indoor/outdoor settings
- Geographic or cultural indicators
- Business or personal environment

Return as a structured list with clear categories."""
            objects_result = self._invoke_nova_omni_video(objects_prompt, video_s3_uri)
            insights['visual_objects'] = objects_result

        except Exception as e:
            self.logger.error(f"Insights generation failed: {e}")
            raise

        return insights
    
    def get_video_embeddings(self, video_id: str, video_url: str,
        s3_bucket: str, s3_key: str) -> List[Dict[str, Any]]:
        """Get video embeddings using Nova 2 Multimodal Embeddings"""
        try:
            video_s3_uri = f"s3://{s3_bucket}/{s3_key}"

            # Start async embedding generation
            embed_result = self.nova_embedding_client.generate_video_embeddings_async(
                video_s3_uri=video_s3_uri,
                output_bucket=s3_bucket,
                segment_duration=15
            )

            # Wait for completion
            self.nova_embedding_client.wait_for_video_embedding(
                invocation_arn=embed_result['invocation_arn'],
                max_wait_time=300
            )

            # Parse results
            embeddings = self.nova_embedding_client.parse_video_embedding_results(
                output_s3_uri=embed_result['output_s3_uri'],
                bucket=s3_bucket
            )

            return embeddings

        except Exception as e:
            self.logger.error(f"Embeddings retrieval failed: {e}")
            raise Exception(f"Failed to get video embeddings from Nova: {str(e)}")
    
    def search_video_content(self, video_id: str, transcription_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract entities from transcription using Nova Lite 2.0

        Args:
            video_id: Video ID (for compatibility)
            transcription_text: Optional transcription text for entity extraction

        Returns:
            Dictionary with extracted entities
        """
        search_results = {}

        try:
            # If transcription text is provided, extract entities using Nova Lite 2.0
            if transcription_text:
                self.logger.info("Extracting entities from transcription using Nova Lite 2.0")
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
    
    def _invoke_nova_omni_video(self, prompt: str, video_s3_uri: str) -> str:
        """Invoke Nova Omni model for video understanding (video only, no audio)"""
        try:
            # Determine video format from URI
            video_format = video_s3_uri.split('.')[-1].lower()
            if video_format not in ['mp4', 'mov', 'mkv', 'webm', 'flv', 'mpeg', 'mpg', 'wmv', '3gp']:
                video_format = 'mp4'

            request_body = {
                "modelId": NOVA_OMNI_MODEL_ID,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "video": {
                                "format": video_format,
                                "source": {
                                    "s3Location": {
                                        "uri": video_s3_uri
                                    }
                                }
                            }
                        },
                        {"text": prompt}
                    ]
                }],
                "inferenceConfig": {
                    "temperature": 0.3,
                    "topP": 0.95,
                    "maxTokens": 10000
                }
            }

            self.logger.info(f"Invoking Nova Omni for video understanding: {video_s3_uri}")

            response = self.bedrock_runtime.converse(**request_body)

            # Extract the response text
            if 'output' in response and 'message' in response['output']:
                content = response['output']['message']['content']
                if content and len(content) > 0:
                    return content[0].get('text', str(response))

            return str(response)

        except Exception as e:
            self.logger.error(f"Nova Omni model invocation failed: {e}")
            return f"Error: {str(e)}"
    
    
    def _parse_chapters_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse chapters response from Nova Omni model"""
        try:
            # Try to parse as JSON first
            import json
            import re

            # Try to extract JSON array from response (may have surrounding text)
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                chapters_data = json.loads(json_match.group())
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
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.warning(f"Failed to parse chapters JSON: {e}")

        # Fallback: create a single chapter
        return [{
            'start': 0,
            'end': 60,
            'title': 'Full Video',
            'summary': response[:300] if response else 'No chapter summary available'
        }]
    
    def _parse_highlights_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse highlights response from Nova Omni model"""
        try:
            # Try to parse as JSON first
            import json
            import re

            # Try to extract JSON array from response (may have surrounding text)
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                highlights_data = json.loads(json_match.group())
                if isinstance(highlights_data, list):
                    return [
                        {
                            'start': hl.get('start', 0),
                            'end': hl.get('end', 10),
                            'highlight': hl.get('highlight', hl.get('description', 'Highlight')),
                            'type': hl.get('type', 'moment')
                        }
                        for hl in highlights_data
                    ]
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.warning(f"Failed to parse highlights JSON: {e}")

        # Fallback: create a single highlight
        return [{
            'start': 0,
            'end': 10,
            'highlight': response[:200] if response else 'No highlights available',
            'type': 'general'
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

    # 11. Visual objects and actions (from Nova Omni analysis)
    if insights.get('visual_objects'):
        content_parts.append(f"VISUAL OBJECTS AND ACTIONS: {insights['visual_objects'][:500]}")

    return "\n\n".join(content_parts)


def get_video_insights_client() -> VideoInsightsClient:
    """Get Nova 2 based VideoInsightsClient"""
    return VideoInsightsClient()


# Lambda handler for extracting video insights using Nova 2 models
def lambda_extract_insights(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to extract insights using Nova 2 models:
    - Nova Omni for transcription and video understanding
    - Nova Lite 2.0 for NER/entity extraction
    - Nova Multimodal Embeddings for video and text embeddings
    """
    try:
        # Debug: Log the received event structure
        logger.info(f"Received event: {json.dumps(event, indent=2)}")

        # Get details from previous step
        if 'video_url' not in event:
            logger.error(f"video_url not found in event. Available keys: {list(event.keys())}")
            if 'body' in event:
                event = event['body']
                logger.info(f"Using nested body structure: {json.dumps(event, indent=2)}")
            else:
                raise KeyError("video_url not found in event and no body structure available")

        video_url = event['video_url']
        video_title = event.get('video_title', '')
        thumbnail_s3_key = event.get('thumbnail_s3_key')
        s3_bucket = event['s3_bucket']
        s3_key = event['s3_key']
        # Get video_id from InitiateVideoProcessing (ensures consistency with thumbnail)
        provided_video_id = event.get('video_id')

        # Initialize Nova 2 clients
        video_insights_client = get_video_insights_client()
        nova_embedding_client = NovaEmbeddingClient()
        transcription_client = NovaOmniTranscriptionClient()

        # Get or generate video ID (use provided one for thumbnail consistency)
        video_id = video_insights_client.upload_video_and_wait(
            video_url=video_url,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            video_id=provided_video_id
        )

        # Step 1: Transcription using Nova Omni
        logger.info("Starting Nova Omni transcription")
        transcription = transcription_client.transcribe_from_s3(s3_bucket, s3_key)
        logger.info(f"Transcription complete: {len(transcription.get('full_text', ''))} characters")

        # Step 2: Video understanding using Nova Omni (video only, no audio)
        logger.info("Generating video insights with Nova Omni")
        insights = video_insights_client.generate_comprehensive_insights(
            video_id=video_id,
            video_url=video_url,
            s3_bucket=s3_bucket,
            s3_key=s3_key
        )

        # Add transcription to insights
        insights['transcription'] = transcription

        # Step 3: Video embeddings using Nova Multimodal Embeddings
        logger.info("Generating video embeddings with Nova")
        embeddings = video_insights_client.get_video_embeddings(
            video_id=video_id,
            video_url=video_url,
            s3_bucket=s3_bucket,
            s3_key=s3_key
        )

        # Step 4: Entity extraction using Nova Lite 2.0
        logger.info("Extracting entities with Nova Lite 2.0")
        search_results = video_insights_client.search_video_content(
            video_id=video_id,
            transcription_text=transcription.get('full_text', '')
        )
        from pprint import pprint
        pprint(search_results)

        # Calculate average embedding for video_content_embedding field
        avg_embedding = None
        if embeddings:
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

        # Step 5: Generate text embedding for insights using Nova
        content_for_embedding = prepare_content_for_embedding(insights, search_results)

        logger.info("Generating text embedding with Nova Multimodal Embeddings")
        nova_text_embeddings = nova_embedding_client.generate_text_embeddings(
            texts=[content_for_embedding],
            embedding_purpose="GENERIC_INDEX"
        )

        # Get the first embedding
        text_embedding = nova_text_embeddings[0] if nova_text_embeddings else None

        # Verify embedding dimension (should be 3072 for Nova)
        if text_embedding and len(text_embedding) != NOVA_EMBEDDING_DIMENSION:
            logger.warning(f"Unexpected Nova embedding dimension: {len(text_embedding)}, expected {NOVA_EMBEDDING_DIMENSION}")
        
        # Validate all required data is present
        if not avg_embedding:
            raise ValueError("Failed to generate video content embedding from Nova - cannot proceed without real embeddings")
        
        # Validate all required data is present
        if not text_embedding:
            raise ValueError("Failed to generate Nova text embedding - cannot proceed without embeddings")

        if not insights:
            raise ValueError("No insights were generated from Nova Omni - cannot proceed")

        if not embeddings or len(embeddings) == 0:
            raise ValueError("No video embeddings were retrieved from Nova - cannot proceed without embeddings")

        # Combine all data matching OpenSearch schema
        video_data = {
            'video_id': video_id,
            'video_title': video_title,
            'nova_integration': True,  # Using Nova 2 models
            's3_bucket': s3_bucket,
            's3_key': s3_key,
            'thumbnail_s3_key': thumbnail_s3_key,
            'processing_timestamp': datetime.utcnow().isoformat(),

            # Embeddings (both from Nova Multimodal Embeddings)
            'video_content_embedding': avg_embedding,  # Nova video embedding
            'pegasus_insights_embedding': text_embedding,  # Nova text embedding (kept field name for compatibility)
            'pegasus_content_for_embedding': content_for_embedding,

            # Video insights from Nova Omni
            'pegasus_insights': insights,  # Kept field name for compatibility

            # Entity detections from Nova Lite 2.0
            'detections': search_results,

            # Embedding metadata
            'embedding_metadata': {
                'video_embedding_model': NOVA_EMBEDDING_MODEL_ID,
                'text_embedding_model': NOVA_EMBEDDING_MODEL_ID,
                'video_understanding_model': NOVA_OMNI_MODEL_ID,
                'ner_model': NOVA_LITE_MODEL_ID,
                'transcription_model': NOVA_OMNI_MODEL_ID,
                'embedding_dimension': NOVA_EMBEDDING_DIMENSION,
                'video_embedding_timestamp': datetime.utcnow().isoformat(),
                'text_embedding_timestamp': datetime.utcnow().isoformat(),
                'video_embeddings_present': len(embeddings) > 0,
                'text_embeddings_present': text_embedding is not None
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
            Bucket=s3_bucket,
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

        # Index the document using video_id as document ID
        # This ensures re-uploading the same video updates rather than duplicates
        opensearch_response = opensearch_client.index(
            index=INDEX_NAME,
            id=video_id,  # Use video_id as document ID for upsert behavior
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
                'has_text_embedding': text_embedding is not None,
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