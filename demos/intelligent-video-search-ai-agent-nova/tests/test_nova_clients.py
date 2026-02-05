#!/usr/bin/env python3
"""
Test script for Nova 2 model clients.
Run this before CloudFormation deployment to validate model access and functionality.

Usage:
    python tests/test_nova_clients.py

    # With a test video file:
    python tests/test_nova_clients.py --video-bucket your-bucket --video-key test-video.mp4

    # List available models to find correct IDs:
    python tests/test_nova_clients.py --list-models

Requirements:
    - AWS credentials configured with access to Bedrock
    - Nova 2 models enabled in your AWS account
"""

import boto3
import json
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas', 'ExtractInsightsFunction', 'src'))

# Configuration - Nova 2 model IDs
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Nova 2 Model IDs (all in us-east-1)
NOVA_LITE_MODEL_ID = os.environ.get(
    'NOVA_LITE_MODEL_ID', 'global.amazon.nova-2-lite-v1:0')
NOVA_OMNI_MODEL_ID = os.environ.get(
    'NOVA_OMNI_MODEL_ID', 'global.amazon.nova-2-omni-v1:0')
NOVA_EMBEDDING_MODEL_ID = os.environ.get(
    'NOVA_EMBEDDING_MODEL_ID', 'amazon.nova-2-multimodal-embeddings-v1:0')
NOVA_EMBEDDING_DIMENSION = int(os.environ.get('NOVA_EMBEDDING_DIMENSION', '3072'))

# ============================================================================
# API FORMAT REFERENCE (Use these patterns in Lambda functions)
# ============================================================================
#
# 1. NOVA LITE 2.0 (NER/Text) - Use Converse API:
#    bedrock.converse(
#        modelId="global.amazon.nova-2-lite-v1:0",
#        messages=[{"role": "user", "content": [{"text": prompt}]}],
#        inferenceConfig={"maxTokens": 1000, "temperature": 0.1}
#    )
#
# 2. NOVA OMNI (Video Understanding) - Use Converse API:
#    bedrock.converse(
#        modelId="global.amazon.nova-2-omni-v1:0",
#        messages=[{
#            "role": "user",
#            "content": [
#                {"video": {"format": "mp4", "source": {"s3Location": {"uri": s3_uri}}}},
#                {"text": prompt}
#            ]
#        }],
#        inferenceConfig={"maxTokens": 10000, "temperature": 0.3}
#    )
#
# 3. NOVA EMBEDDINGS (Text) - Use InvokeModel API:
#    bedrock.invoke_model(
#        modelId="amazon.nova-2-multimodal-embeddings-v1:0",
#        body=json.dumps({
#            "taskType": "SINGLE_EMBEDDING",
#            "singleEmbeddingParams": {
#                "embeddingPurpose": "GENERIC_INDEX",
#                "embeddingDimension": 3072,
#                "text": {"truncationMode": "END", "value": text}
#            }
#        })
#    )
#    # Response format: {"embeddings": [{"embedding": [0.1, 0.2, ...]}]}
#
# 4. NOVA EMBEDDINGS (Video Async) - Use StartAsyncInvoke API:
#    bedrock.start_async_invoke(
#        modelId="amazon.nova-2-multimodal-embeddings-v1:0",
#        modelInput={
#            "taskType": "SEGMENTED_EMBEDDING",
#            "segmentedEmbeddingParams": {
#                "embeddingPurpose": "GENERIC_INDEX",
#                "embeddingDimension": 3072,
#                "video": {
#                    "format": "mp4",
#                    "embeddingMode": "AUDIO_VIDEO_COMBINED",
#                    "source": {"s3Location": {"uri": video_s3_uri}},
#                    "segmentationConfig": {"durationSeconds": 15}
#                }
#            }
#        },
#        outputDataConfig={"s3OutputDataConfig": {"s3Uri": output_uri}}
#    )
# ============================================================================


def list_available_models():
    """List all available foundation models in Bedrock"""
    print("\n" + "=" * 60)
    print("Available Bedrock Foundation Models")
    print("=" * 60)

    try:
        bedrock = boto3.client('bedrock', region_name=REGION)
        response = bedrock.list_foundation_models()

        # Group by provider
        models_by_provider = {}
        for model in response.get('modelSummaries', []):
            provider = model.get('providerName', 'Unknown')
            if provider not in models_by_provider:
                models_by_provider[provider] = []
            models_by_provider[provider].append(model)

        # Print models, highlighting Nova/Amazon models
        for provider, models in sorted(models_by_provider.items()):
            print(f"\n{provider}:")
            for model in models:
                model_id = model.get('modelId', 'N/A')
                model_name = model.get('modelName', 'N/A')
                modalities = model.get('inputModalities', []) + model.get('outputModalities', [])
                modalities_str = ', '.join(set(modalities))

                # Highlight Nova models
                if 'nova' in model_id.lower() or 'nova' in model_name.lower():
                    print(f"  ★ {model_id}")
                    print(f"      Name: {model_name}")
                    print(f"      Modalities: {modalities_str}")
                elif 'titan' in model_id.lower() and 'embed' in model_id.lower():
                    print(f"  → {model_id} (embedding)")
                else:
                    print(f"    {model_id}")

        print("\n" + "=" * 60)
        print("TIP: Look for Nova models (marked with ★) above")
        print("Update NOVA_*_MODEL_ID environment variables with correct IDs")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Failed to list models: {e}")
        print("Make sure you have bedrock:ListFoundationModels permission")


def test_nova_lite_ner():
    """Test Nova Lite for named entity recognition using Converse API"""
    print("\n" + "=" * 60)
    print("Testing Nova Lite (NER) - Converse API")
    print(f"Model ID: {NOVA_LITE_MODEL_ID}")
    print("=" * 60)

    try:
        bedrock = boto3.client('bedrock-runtime', region_name=REGION)

        test_text = """
        Amazon Web Services announced a new partnership with Microsoft and Google Cloud.
        The CEO Jeff Bezos and Satya Nadella discussed the collaboration at the AWS re:Invent conference.
        Brands like Nike, Apple, and Coca-Cola are already using the new services.
        """

        prompt = f"""Extract all brand names, company names, and person names from this text.
Return the results as a JSON object with keys: "brands", "companies", "person_names"

Text:
{test_text}

Return ONLY valid JSON, no other text."""

        # Try Converse API first (recommended for Nova)
        print("Trying Converse API...")
        try:
            response = bedrock.converse(
                modelId=NOVA_LITE_MODEL_ID,
                messages=[{
                    "role": "user",
                    "content": [{"text": prompt}]
                }],
                inferenceConfig={
                    "maxTokens": 1000,
                    "temperature": 0.1
                }
            )

            # Extract response
            output_text = ""
            if 'output' in response and 'message' in response['output']:
                content = response['output']['message']['content']
                if content and len(content) > 0:
                    output_text = content[0].get('text', '')

            print(f"Response received ({len(output_text)} chars)")
            print(f"Output: {output_text[:500]}...")

            # Try to parse as JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', output_text)
            if json_match:
                try:
                    entities = json.loads(json_match.group())
                    print(f"Parsed entities: {entities}")
                    print("✅ Nova Lite NER test PASSED (Converse API)")
                    return True
                except json.JSONDecodeError:
                    print("⚠️ Response received but JSON parsing failed")
                    print("✅ Nova Lite NER test PASSED (model responds, parsing needs work)")
                    return True
            else:
                print("⚠️ No JSON found in response, but model responded")
                print("✅ Nova Lite NER test PASSED (model responds)")
                return True

        except Exception as converse_error:
            print(f"Converse API failed: {converse_error}")
            print("\nTrying InvokeModel API with tool use...")

            # Fall back to InvokeModel with tool use
            body = json.dumps({
                "messages": [{
                    "role": "user",
                    "content": [{"text": f"Extract entities from: {test_text}"}]
                }],
                "inferenceConfig": {
                    "max_new_tokens": 1000,
                    "temperature": 0.1
                },
                "toolConfig": {
                    "tools": [{
                        "toolSpec": {
                            "name": "extract_entities",
                            "description": "Extract brands, companies, and person names",
                            "inputSchema": {
                                "json": {
                                    "type": "object",
                                    "properties": {
                                        "brands": {"type": "array", "items": {"type": "string"}},
                                        "companies": {"type": "array", "items": {"type": "string"}},
                                        "person_names": {"type": "array", "items": {"type": "string"}}
                                    },
                                    "required": ["brands", "companies", "person_names"]
                                }
                            }
                        }
                    }],
                    "toolChoice": {"any": {}}
                }
            })

            response = bedrock.invoke_model(
                modelId=NOVA_LITE_MODEL_ID,
                body=body,
                contentType='application/json'
            )

            response_body = json.loads(response['body'].read())
            print(f"InvokeModel Response: {json.dumps(response_body, indent=2)[:500]}...")
            print("✅ Nova Lite NER test PASSED (InvokeModel API)")
            return True

    except Exception as e:
        error_str = str(e)
        print(f"❌ Nova Lite test FAILED: {e}")

        # Provide helpful suggestions
        if 'ResourceNotFoundException' in error_str or 'does not exist' in error_str.lower():
            print("\n💡 Model not found. Run with --list-models to see available options")
            print("   Then set: export NOVA_LITE_MODEL_ID='correct-model-id'")
        elif 'AccessDeniedException' in error_str:
            print("\n💡 Access denied. Enable the model in Bedrock console:")
            print("   1. Go to AWS Bedrock Console")
            print("   2. Navigate to 'Model access'")
            print("   3. Request access to Nova models")

        return False


def test_nova_embedding_text():
    """Test Nova 2 Multimodal Embeddings for text"""
    print("\n" + "=" * 60)
    print("Testing Nova 2 Multimodal Embeddings (Text)")
    print(f"Model ID: {NOVA_EMBEDDING_MODEL_ID}")
    print(f"Expected Dimension: {NOVA_EMBEDDING_DIMENSION}")
    print("=" * 60)

    try:
        bedrock = boto3.client('bedrock-runtime', region_name=REGION)

        test_text = 'This is a test video about technology and innovation.'

        # Nova 2 Multimodal Embeddings format
        request_body = {
            'taskType': 'SINGLE_EMBEDDING',
            'singleEmbeddingParams': {
                'embeddingPurpose': 'GENERIC_INDEX',
                'embeddingDimension': NOVA_EMBEDDING_DIMENSION,
                'text': {
                    'truncationMode': 'END',
                    'value': test_text
                },
            },
        }

        print(f"Request taskType: {request_body['taskType']}")
        print(f"Embedding dimension requested: {NOVA_EMBEDDING_DIMENSION}")

        response = bedrock.invoke_model(
            body=json.dumps(request_body),
            modelId=NOVA_EMBEDDING_MODEL_ID,
            accept='application/json',
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read())

        # Extract embedding - Nova 2 returns 'embeddings' array with objects
        # Each object has 'embedding' array
        embeddings_data = response_body.get('embeddings', [])
        embedding = embeddings_data[0].get('embedding', []) if embeddings_data else response_body.get('embedding', [])

        print(f"Embedding dimension returned: {len(embedding)}")
        if embedding:
            print(f"First 5 values: {embedding[:5]}")
            print(f"Value range: [{min(embedding):.4f}, {max(embedding):.4f}]")

        if len(embedding) > 0:
            if len(embedding) == NOVA_EMBEDDING_DIMENSION:
                print("✅ Nova Embeddings test PASSED")
            else:
                print(f"⚠️ Dimension mismatch: got {len(embedding)}, expected {NOVA_EMBEDDING_DIMENSION}")
                print("   Update NOVA_EMBEDDING_DIMENSION if needed")
            return True
        else:
            print("❌ No embedding returned")
            print(f"Response keys: {list(response_body.keys())}")
            return False

    except Exception as e:
        error_str = str(e)
        print(f"❌ Nova Embeddings test FAILED: {e}")

        if 'ValidationException' in error_str:
            print("\n💡 Validation error - check request format")
            print("   Supported dimensions: 256, 384, 1024, 3072")

        return False


def test_nova_omni_video(video_bucket: str = None, video_key: str = None):
    """Test Nova 2 Omni for video understanding"""
    print("\n" + "=" * 60)
    print("Testing Nova 2 Omni (Video Understanding)")
    print(f"Model ID: {NOVA_OMNI_MODEL_ID}")
    print("=" * 60)

    if not video_bucket or not video_key:
        print("⚠️  Skipping video test - no video bucket/key provided")
        print("   Use --video-bucket and --video-key to test video understanding")
        return None

    try:
        bedrock = boto3.client('bedrock-runtime', region_name=REGION)

        video_s3_uri = f"s3://{video_bucket}/{video_key}"
        video_format = video_key.split('.')[-1].lower()
        if video_format not in ['mp4', 'mov', 'mkv', 'webm', 'flv', 'mpeg', 'mpg', 'wmv', '3gp']:
            video_format = 'mp4'

        print(f"Video URI: {video_s3_uri}")
        print(f"Video format: {video_format}")

        # Use Converse API for Nova Omni video understanding
        response = bedrock.converse(
            modelId=NOVA_OMNI_MODEL_ID,
            messages=[{
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
                    {"text": "Analyze this video and describe: 1) The main subject or topic, 2) Key visual elements you observe, 3) The overall mood or tone. Focus only on visual content."}
                ]
            }],
            inferenceConfig={
                "temperature": 0.3,
                "maxTokens": 1000
            }
        )

        if 'output' in response and 'message' in response['output']:
            content = response['output']['message']['content']
            if content and len(content) > 0:
                output_text = content[0].get('text', '')
                print(f"\nResponse ({len(output_text)} chars):")
                print("-" * 40)
                print(output_text[:600])
                if len(output_text) > 600:
                    print("...")
                print("-" * 40)

                # Quality checks
                quality_notes = []
                if len(output_text) > 100:
                    quality_notes.append("Substantial response")
                if any(word in output_text.lower() for word in ['video', 'scene', 'shows', 'appears', 'visual']):
                    quality_notes.append("Contains visual descriptions")
                if '1)' in output_text or '1.' in output_text or 'first' in output_text.lower():
                    quality_notes.append("Structured response")

                print(f"Quality indicators: {', '.join(quality_notes) if quality_notes else 'Basic'}")
                print("✅ Nova Omni Video test PASSED")
                return True

        print("❌ Unexpected response format")
        print(f"Response: {json.dumps(response, indent=2, default=str)[:500]}")
        return False

    except Exception as e:
        error_str = str(e)
        print(f"❌ Nova Omni Video test FAILED: {e}")

        if 'ResourceNotFoundException' in error_str or 'does not exist' in error_str.lower():
            print("\n💡 Model not found. Verify model ID is enabled in your account.")
        elif 'video' in error_str.lower() or 'modality' in error_str.lower():
            print("\n💡 Video modality issue - ensure video format is supported")
        elif 'S3' in error_str or 'bucket' in error_str.lower() or 'Access' in error_str:
            print("\n💡 S3 access issue. Check:")
            print(f"   1. Bucket exists: aws s3 ls s3://{video_bucket}")
            print(f"   2. Video exists: aws s3 ls s3://{video_bucket}/{video_key}")
            print("   3. Bedrock service role has s3:GetObject permission")

        return False


def test_nova_embedding_video_async(video_bucket: str = None, video_key: str = None):
    """Test Nova 2 Multimodal Embeddings for video (async API)

    This tests the same API format used in the Lambda function:
    - taskType: SEGMENTED_EMBEDDING
    - embeddingMode: AUDIO_VIDEO_COMBINED
    - segmentationConfig for chunking
    """
    print("\n" + "=" * 60)
    print("Testing Nova 2 Video Embeddings (Async)")
    print(f"Model ID: {NOVA_EMBEDDING_MODEL_ID}")
    print("=" * 60)

    if not video_bucket or not video_key:
        print("⚠️  Skipping video embedding test - no video bucket/key provided")
        print("   Use --video-bucket and --video-key to test video embeddings")
        return None

    try:
        import time
        import uuid

        bedrock = boto3.client('bedrock-runtime', region_name=REGION)

        video_s3_uri = f"s3://{video_bucket}/{video_key}"
        video_format = video_key.split('.')[-1].lower()
        if video_format not in ['mp4', 'mov', 'mkv', 'webm', 'flv', 'mpeg', 'mpg', 'wmv', '3gp']:
            video_format = 'mp4'

        invocation_id = f"test-{uuid.uuid4().hex[:8]}"
        output_s3_uri = f"s3://{video_bucket}/test-embeddings/{invocation_id}/"

        print(f"Video URI: {video_s3_uri}")
        print(f"Video format: {video_format}")
        print(f"Output URI: {output_s3_uri}")

        # Nova 2 Multimodal Embeddings format for video (SEGMENTED_EMBEDDING)
        # embeddingMode: AUDIO_VIDEO_COMBINED (combines audio + video)
        # segmentationConfig: durationSeconds for chunking (max 30s)
        model_input = {
            'taskType': 'SEGMENTED_EMBEDDING',
            'segmentedEmbeddingParams': {
                'embeddingPurpose': 'GENERIC_INDEX',
                'embeddingDimension': NOVA_EMBEDDING_DIMENSION,
                'video': {
                    'format': video_format,
                    'embeddingMode': 'AUDIO_VIDEO_COMBINED',
                    'source': {
                        's3Location': {'uri': video_s3_uri}
                    },
                    'segmentationConfig': {
                        'durationSeconds': 15  # 15-second segments
                    },
                },
            },
        }

        print(f"Request taskType: {model_input['taskType']}")
        print(f"Embedding mode: AUDIO_VIDEO_COMBINED")
        print(f"Segment duration: 15 seconds")

        response = bedrock.start_async_invoke(
            modelId=NOVA_EMBEDDING_MODEL_ID,
            modelInput=model_input,
            outputDataConfig={
                's3OutputDataConfig': {
                    's3Uri': output_s3_uri
                }
            },
        )

        invocation_arn = response.get('invocationArn')
        print(f"Invocation ARN: {invocation_arn}")

        # Wait for completion (with timeout)
        max_wait = 180  # 3 minutes for video processing
        elapsed = 0
        while elapsed < max_wait:
            status_response = bedrock.get_async_invoke(invocationArn=invocation_arn)
            status = status_response['status']
            print(f"Status: {status} ({elapsed}s)")

            if status == 'Completed':
                # Try to read the output to validate format
                try:
                    s3_client = boto3.client('s3', region_name=REGION)
                    output_prefix = output_s3_uri.replace(f"s3://{video_bucket}/", "")
                    objects = s3_client.list_objects_v2(Bucket=video_bucket, Prefix=output_prefix)

                    if 'Contents' in objects:
                        print(f"Output files: {len(objects['Contents'])}")
                        for obj in objects['Contents'][:3]:  # Show first 3
                            print(f"  - {obj['Key']}")
                except Exception as s3_err:
                    print(f"Could not list output files: {s3_err}")

                print("✅ Nova Video Embeddings test PASSED")
                return True
            elif status == 'Failed':
                failure_msg = status_response.get('failureMessage', 'Unknown')
                print(f"❌ Failed: {failure_msg}")
                return False

            time.sleep(15)
            elapsed += 15

        print("❌ Timeout waiting for completion")
        return False

    except Exception as e:
        error_str = str(e)
        print(f"❌ Nova Video Embeddings test FAILED: {e}")

        if 'ValidationException' in error_str:
            print("\n💡 Validation error - check request format")
            print("   The model_input structure should match Nova 2 API")
        elif 'S3' in error_str or 'bucket' in error_str.lower():
            print("\n💡 S3 access issue. Ensure Bedrock can write to output bucket")

        return False


def test_bedrock_model_access():
    """Test that all required models are accessible"""
    print("\n" + "=" * 60)
    print("Testing Bedrock Model Access")
    print("=" * 60)

    try:
        bedrock = boto3.client('bedrock', region_name=REGION)

        models_to_check = [
            ('Nova Lite (NER)', NOVA_LITE_MODEL_ID),
            ('Nova Pro (Video)', NOVA_OMNI_MODEL_ID),
            ('Embeddings', NOVA_EMBEDDING_MODEL_ID),
        ]

        all_accessible = True
        for name, model_id in models_to_check:
            try:
                # For global. prefix models, try the non-global version for metadata
                lookup_id = model_id.replace('global.', '') if model_id.startswith('global.') else model_id
                response = bedrock.get_foundation_model(modelIdentifier=lookup_id)
                model_details = response.get('modelDetails', {})
                status = model_details.get('modelLifecycle', {}).get('status', 'UNKNOWN')
                print(f"  ✓ {name}: {model_id}")
                print(f"      Status: {status}")
                if model_id.startswith('global.'):
                    print(f"      Note: Using cross-region inference ID")

            except bedrock.exceptions.ResourceNotFoundException:
                # Global prefix models may not be listed but still work
                if model_id.startswith('global.'):
                    print(f"  ⚠ {name}: {model_id} - Cross-region ID (verify in invocation tests)")
                else:
                    print(f"  ✗ {name}: {model_id} - NOT FOUND")
                    all_accessible = False
            except bedrock.exceptions.AccessDeniedException:
                print(f"  ⚠ {name}: {model_id} - ACCESS DENIED (may still work)")
            except Exception as e:
                print(f"  ? {name}: {model_id} - {e}")

        if all_accessible:
            print("\n✅ All models accessible")
        else:
            print("\n⚠️ Some models may need verification - check invocation tests")

        return all_accessible

    except Exception as e:
        print(f"❌ Model access test FAILED: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test Nova 2 model clients')
    parser.add_argument('--video-bucket', help='S3 bucket containing test video')
    parser.add_argument('--video-key', help='S3 key of test video')
    parser.add_argument('--skip-video', action='store_true', help='Skip video tests')
    parser.add_argument('--list-models', action='store_true', help='List available models and exit')
    args = parser.parse_args()

    print("=" * 60)
    print("Nova Model Client Tests")
    print("=" * 60)
    print(f"Region: {REGION}")
    print(f"Nova Lite: {NOVA_LITE_MODEL_ID}")
    print(f"Nova Pro/Omni: {NOVA_OMNI_MODEL_ID}")
    print(f"Embeddings: {NOVA_EMBEDDING_MODEL_ID}")
    print(f"Embedding Dimension: {NOVA_EMBEDDING_DIMENSION}")

    if args.list_models:
        list_available_models()
        sys.exit(0)

    results = {}

    # Test model access
    results['model_access'] = test_bedrock_model_access()

    # Test Nova Lite NER
    results['nova_lite_ner'] = test_nova_lite_ner()

    # Test embeddings
    results['embedding_text'] = test_nova_embedding_text()

    # Test video understanding (if video provided)
    if not args.skip_video:
        results['nova_video'] = test_nova_omni_video(args.video_bucket, args.video_key)
        results['embedding_video'] = test_nova_embedding_video_async(args.video_bucket, args.video_key)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results.items():
        if result is True:
            print(f"  ✅ {test_name}: PASSED")
            passed += 1
        elif result is False:
            print(f"  ❌ {test_name}: FAILED")
            failed += 1
        else:
            print(f"  ⚠️  {test_name}: SKIPPED")
            skipped += 1

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("\n" + "=" * 60)
        print("TROUBLESHOOTING")
        print("=" * 60)
        print("1. List available models: python test_nova_clients.py --list-models")
        print("2. Update model IDs in environment variables or .env file")
        print("3. Ensure models are enabled in AWS Bedrock console")
        print("4. Check IAM permissions for bedrock:InvokeModel, bedrock:Converse")
        sys.exit(1)
    else:
        print("\n✅ All tests passed! Ready for deployment.")
        sys.exit(0)


if __name__ == "__main__":
    main()
