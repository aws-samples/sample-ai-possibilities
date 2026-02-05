#!/usr/bin/env python3
"""
Comprehensive Nova 2 Model Performance and Quality Validation Script.

This script tests:
1. Each Nova 2 model's input/output formats
2. Response quality and structure
3. Performance (latency, token usage)
4. Optimized vs current approach comparison

Usage:
    # Basic tests (no video required)
    python tests/test_nova_performance.py

    # Full tests with video
    python tests/test_nova_performance.py --video-bucket your-bucket --video-key test.mp4

    # Compare optimization approaches
    python tests/test_nova_performance.py --video-bucket bucket --video-key video.mp4 --compare
"""

import boto3
import json
import argparse
import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import re

# Configuration - Nova 2 Model IDs (all in us-east-1)
REGION = os.environ.get('AWS_REGION', 'us-east-1')
NOVA_LITE_MODEL_ID = os.environ.get('NOVA_LITE_MODEL_ID', 'global.amazon.nova-2-lite-v1:0')
NOVA_OMNI_MODEL_ID = os.environ.get('NOVA_OMNI_MODEL_ID', 'global.amazon.nova-2-omni-v1:0')
NOVA_EMBEDDING_MODEL_ID = os.environ.get('NOVA_EMBEDDING_MODEL_ID', 'amazon.nova-2-multimodal-embeddings-v1:0')
NOVA_EMBEDDING_DIMENSION = int(os.environ.get('NOVA_EMBEDDING_DIMENSION', '3072'))


@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    model_id: str
    success: bool
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    error: str = ""
    output_sample: str = ""
    quality_score: float = 0.0  # 0-1 scale
    notes: List[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


class NovaModelValidator:
    """Validates Nova 2 model functionality and performance"""

    def __init__(self, region: str = REGION):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.region = region
        self.results: List[TestResult] = []

    def _measure_time(self, func):
        """Decorator to measure execution time"""
        start = time.time()
        result = func()
        elapsed_ms = (time.time() - start) * 1000
        return result, elapsed_ms

    # =========================================================================
    # NOVA LITE 2.0 TESTS (NER / Entity Extraction)
    # =========================================================================

    def test_nova_lite_basic(self) -> TestResult:
        """Test Nova Lite basic text generation"""
        print("\n" + "=" * 60)
        print("TEST: Nova Lite 2.0 - Basic Text Generation")
        print("=" * 60)

        try:
            start = time.time()

            body = json.dumps({
                "messages": [{
                    "role": "user",
                    "content": [{"text": "List 3 benefits of cloud computing in bullet points."}]
                }],
                "inferenceConfig": {
                    "max_new_tokens": 500,
                    "temperature": 0.3
                }
            })

            response = self.bedrock.invoke_model(
                modelId=NOVA_LITE_MODEL_ID,
                body=body,
                contentType='application/json'
            )

            latency_ms = (time.time() - start) * 1000
            response_body = json.loads(response['body'].read())

            # Extract response
            output_text = ""
            if 'output' in response_body and 'message' in response_body['output']:
                content = response_body['output']['message']['content']
                if content:
                    output_text = content[0].get('text', '')

            # Quality check
            quality_score = 0.0
            notes = []

            if output_text:
                # Check for bullet points
                if '-' in output_text or '•' in output_text or '1.' in output_text:
                    quality_score += 0.5
                    notes.append("Contains bullet points")
                # Check for reasonable length
                if 100 < len(output_text) < 2000:
                    quality_score += 0.3
                    notes.append("Reasonable length")
                # Check for cloud-related terms
                cloud_terms = ['cloud', 'scalab', 'cost', 'flexib', 'access']
                if any(term in output_text.lower() for term in cloud_terms):
                    quality_score += 0.2
                    notes.append("Relevant content")

            result = TestResult(
                test_name="Nova Lite Basic",
                model_id=NOVA_LITE_MODEL_ID,
                success=True,
                latency_ms=latency_ms,
                output_sample=output_text[:300],
                quality_score=quality_score,
                notes=notes
            )
            print(f"✅ PASSED - Latency: {latency_ms:.0f}ms, Quality: {quality_score:.1f}")
            print(f"   Output: {output_text[:150]}...")

        except Exception as e:
            result = TestResult(
                test_name="Nova Lite Basic",
                model_id=NOVA_LITE_MODEL_ID,
                success=False,
                latency_ms=0,
                error=str(e)
            )
            print(f"❌ FAILED: {e}")

        self.results.append(result)
        return result

    def test_nova_lite_tool_use_ner(self) -> TestResult:
        """Test Nova Lite with tool use for NER - the approach we use for entity extraction"""
        print("\n" + "=" * 60)
        print("TEST: Nova Lite 2.0 - Tool Use NER (Entity Extraction)")
        print("=" * 60)

        test_text = """
        Amazon Web Services announced a new partnership with Microsoft and Google Cloud.
        The CEO Andy Jassy and Satya Nadella discussed the collaboration at AWS re:Invent.
        Brands like Nike, Apple, and Coca-Cola are already using the new AI services.
        Dr. Sarah Johnson from Stanford University presented the research findings.
        """

        try:
            start = time.time()

            body = json.dumps({
                "messages": [{
                    "role": "user",
                    "content": [{"text": f"""Extract all brand names, company names, and person names from this text:

{test_text}

Use the extract_entities tool to provide the structured results."""}]
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

            response = self.bedrock.invoke_model(
                modelId=NOVA_LITE_MODEL_ID,
                body=body,
                contentType='application/json'
            )

            latency_ms = (time.time() - start) * 1000
            response_body = json.loads(response['body'].read())

            # Parse tool use response
            entities = {'brands': [], 'companies': [], 'person_names': []}
            quality_score = 0.0
            notes = []

            if 'output' in response_body and 'message' in response_body['output']:
                message = response_body['output']['message']
                if 'content' in message:
                    for content_item in message['content']:
                        if content_item.get('toolUse'):
                            tool_use = content_item['toolUse']
                            if tool_use.get('name') == 'extract_entities':
                                entities = tool_use.get('input', {})
                                notes.append("Tool use response received")

            # Quality validation
            expected_brands = ['Nike', 'Apple', 'Coca-Cola']
            expected_companies = ['Amazon', 'AWS', 'Microsoft', 'Google', 'Stanford']
            expected_people = ['Andy Jassy', 'Satya Nadella', 'Sarah Johnson']

            found_brands = entities.get('brands', [])
            found_companies = entities.get('companies', [])
            found_people = entities.get('person_names', [])

            # Score based on recall
            brand_score = len([b for b in expected_brands if any(b.lower() in fb.lower() for fb in found_brands)]) / len(expected_brands)
            company_score = len([c for c in expected_companies if any(c.lower() in fc.lower() for fc in found_companies)]) / len(expected_companies)
            people_score = len([p for p in expected_people if any(p.split()[-1].lower() in fp.lower() for fp in found_people)]) / len(expected_people)

            quality_score = (brand_score + company_score + people_score) / 3
            notes.append(f"Brands: {len(found_brands)}, Companies: {len(found_companies)}, People: {len(found_people)}")

            result = TestResult(
                test_name="Nova Lite Tool Use NER",
                model_id=NOVA_LITE_MODEL_ID,
                success=True,
                latency_ms=latency_ms,
                output_sample=json.dumps(entities, indent=2)[:500],
                quality_score=quality_score,
                notes=notes
            )
            print(f"✅ PASSED - Latency: {latency_ms:.0f}ms, Quality: {quality_score:.2f}")
            print(f"   Entities found: {entities}")

        except Exception as e:
            result = TestResult(
                test_name="Nova Lite Tool Use NER",
                model_id=NOVA_LITE_MODEL_ID,
                success=False,
                latency_ms=0,
                error=str(e)
            )
            print(f"❌ FAILED: {e}")

        self.results.append(result)
        return result

    # =========================================================================
    # NOVA EMBEDDING TESTS
    # =========================================================================

    def test_nova_embedding_text(self) -> TestResult:
        """Test Nova Multimodal Embeddings for text"""
        print("\n" + "=" * 60)
        print("TEST: Nova Multimodal Embeddings - Text")
        print("=" * 60)

        try:
            start = time.time()

            # Nova 2 Multimodal Embeddings format (SINGLE_EMBEDDING)
            request_body = {
                'taskType': 'SINGLE_EMBEDDING',
                'singleEmbeddingParams': {
                    'embeddingPurpose': 'GENERIC_INDEX',
                    'embeddingDimension': NOVA_EMBEDDING_DIMENSION,
                    'text': {
                        'truncationMode': 'END',
                        'value': "This is a marketing video about cloud computing and AI technology."
                    },
                },
            }

            response = self.bedrock.invoke_model(
                body=json.dumps(request_body),
                modelId=NOVA_EMBEDDING_MODEL_ID,
                accept='application/json',
                contentType='application/json'
            )

            latency_ms = (time.time() - start) * 1000
            response_body = json.loads(response['body'].read())
            # Nova 2 returns embeddings array with objects containing embedding
            embeddings_data = response_body.get('embeddings', [])
            embedding = embeddings_data[0].get('embedding', []) if embeddings_data else []

            # Quality checks
            quality_score = 0.0
            notes = []

            if embedding:
                notes.append(f"Dimension: {len(embedding)}")
                if len(embedding) == NOVA_EMBEDDING_DIMENSION:
                    quality_score += 0.5
                    notes.append("Correct dimension")
                # Check for valid float values
                if all(isinstance(v, (int, float)) for v in embedding[:10]):
                    quality_score += 0.3
                    notes.append("Valid float values")
                # Check for reasonable range
                if all(-5 < v < 5 for v in embedding[:100]):
                    quality_score += 0.2
                    notes.append("Values in expected range")

            result = TestResult(
                test_name="Nova Embedding Text",
                model_id=NOVA_EMBEDDING_MODEL_ID,
                success=True,
                latency_ms=latency_ms,
                output_sample=f"Embedding dim: {len(embedding)}, first 5: {embedding[:5]}",
                quality_score=quality_score,
                notes=notes
            )
            print(f"✅ PASSED - Latency: {latency_ms:.0f}ms, Dimension: {len(embedding)}")

        except Exception as e:
            result = TestResult(
                test_name="Nova Embedding Text",
                model_id=NOVA_EMBEDDING_MODEL_ID,
                success=False,
                latency_ms=0,
                error=str(e)
            )
            print(f"❌ FAILED: {e}")

        self.results.append(result)
        return result

    def test_nova_embedding_semantic_similarity(self) -> TestResult:
        """Test semantic similarity between related texts"""
        print("\n" + "=" * 60)
        print("TEST: Nova Embeddings - Semantic Similarity")
        print("=" * 60)

        try:
            import numpy as np

            texts = [
                "A marketing video showcasing cloud computing benefits",
                "Advertisement about cloud technology advantages",
                "A cooking tutorial for making pasta",
            ]

            start = time.time()
            embeddings = []

            for text in texts:
                # Nova 2 Multimodal Embeddings format (SINGLE_EMBEDDING)
                request_body = {
                    'taskType': 'SINGLE_EMBEDDING',
                    'singleEmbeddingParams': {
                        'embeddingPurpose': 'GENERIC_INDEX',
                        'embeddingDimension': NOVA_EMBEDDING_DIMENSION,
                        'text': {
                            'truncationMode': 'END',
                            'value': text
                        },
                    },
                }

                response = self.bedrock.invoke_model(
                    body=json.dumps(request_body),
                    modelId=NOVA_EMBEDDING_MODEL_ID,
                    accept='application/json',
                    contentType='application/json'
                )

                response_body = json.loads(response['body'].read())
                embeddings_data = response_body.get('embeddings', [])
                embedding = embeddings_data[0].get('embedding', []) if embeddings_data else []
                embeddings.append(embedding)

            latency_ms = (time.time() - start) * 1000

            # Calculate cosine similarities
            def cosine_sim(a, b):
                a, b = np.array(a), np.array(b)
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            sim_0_1 = cosine_sim(embeddings[0], embeddings[1])  # Similar texts
            sim_0_2 = cosine_sim(embeddings[0], embeddings[2])  # Different texts

            # Quality check: similar texts should have higher similarity
            quality_score = 0.0
            notes = []

            notes.append(f"Cloud texts similarity: {sim_0_1:.3f}")
            notes.append(f"Cloud vs Cooking similarity: {sim_0_2:.3f}")

            if sim_0_1 > sim_0_2:
                quality_score += 0.5
                notes.append("Similar texts have higher similarity ✓")
            if sim_0_1 > 0.7:
                quality_score += 0.25
                notes.append("High similarity for related texts ✓")
            if sim_0_2 < 0.5:
                quality_score += 0.25
                notes.append("Low similarity for unrelated texts ✓")

            result = TestResult(
                test_name="Nova Embedding Similarity",
                model_id=NOVA_EMBEDDING_MODEL_ID,
                success=True,
                latency_ms=latency_ms,
                output_sample=f"Similar: {sim_0_1:.3f}, Different: {sim_0_2:.3f}",
                quality_score=quality_score,
                notes=notes
            )
            print(f"✅ PASSED - Similar texts: {sim_0_1:.3f}, Different: {sim_0_2:.3f}")

        except Exception as e:
            result = TestResult(
                test_name="Nova Embedding Similarity",
                model_id=NOVA_EMBEDDING_MODEL_ID,
                success=False,
                latency_ms=0,
                error=str(e)
            )
            print(f"❌ FAILED: {e}")

        self.results.append(result)
        return result

    # =========================================================================
    # NOVA OMNI VIDEO TESTS
    # =========================================================================

    def test_nova_omni_video_basic(self, video_bucket: str, video_key: str) -> TestResult:
        """Test Nova Omni basic video understanding"""
        print("\n" + "=" * 60)
        print("TEST: Nova Omni - Basic Video Understanding")
        print("=" * 60)

        try:
            start = time.time()
            video_s3_uri = f"s3://{video_bucket}/{video_key}"
            video_format = video_key.split('.')[-1].lower()
            if video_format not in ['mp4', 'mov', 'mkv', 'webm']:
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
                                    "s3Location": {"uri": video_s3_uri}
                                }
                            }
                        },
                        {"text": "Describe what you see in this video in 2-3 sentences."}
                    ]
                }],
                "inferenceConfig": {
                    "temperature": 0.3,
                    "maxTokens": 500
                }
            }

            response = self.bedrock.converse(**request_body)
            latency_ms = (time.time() - start) * 1000

            # Extract response
            output_text = ""
            if 'output' in response and 'message' in response['output']:
                content = response['output']['message']['content']
                if content:
                    output_text = content[0].get('text', '')

            # Quality check
            quality_score = 0.0
            notes = []

            if output_text:
                if len(output_text) > 50:
                    quality_score += 0.5
                    notes.append("Substantial response")
                if '.' in output_text:
                    quality_score += 0.25
                    notes.append("Complete sentences")
                # Check for visual description terms
                visual_terms = ['video', 'scene', 'shows', 'appears', 'visible', 'see', 'display']
                if any(term in output_text.lower() for term in visual_terms):
                    quality_score += 0.25
                    notes.append("Visual description present")

            result = TestResult(
                test_name="Nova Omni Video Basic",
                model_id=NOVA_OMNI_MODEL_ID,
                success=True,
                latency_ms=latency_ms,
                output_sample=output_text[:300],
                quality_score=quality_score,
                notes=notes
            )
            print(f"✅ PASSED - Latency: {latency_ms:.0f}ms, Quality: {quality_score:.2f}")
            print(f"   Output: {output_text[:200]}...")

        except Exception as e:
            result = TestResult(
                test_name="Nova Omni Video Basic",
                model_id=NOVA_OMNI_MODEL_ID,
                success=False,
                latency_ms=0,
                error=str(e)
            )
            print(f"❌ FAILED: {e}")

        self.results.append(result)
        return result

    def test_nova_omni_video_structured(self, video_bucket: str, video_key: str) -> TestResult:
        """Test Nova Omni with structured JSON output request"""
        print("\n" + "=" * 60)
        print("TEST: Nova Omni - Structured JSON Output")
        print("=" * 60)

        try:
            start = time.time()
            video_s3_uri = f"s3://{video_bucket}/{video_key}"
            video_format = video_key.split('.')[-1].lower()
            if video_format not in ['mp4', 'mov', 'mkv', 'webm']:
                video_format = 'mp4'

            # Request structured output
            prompt = """Analyze this video and provide a structured analysis.

Return ONLY valid JSON in this exact format:
{
    "summary": "Brief 1-2 sentence summary",
    "main_topic": "Primary topic or subject",
    "visual_elements": ["element1", "element2", "element3"],
    "sentiment": "positive/negative/neutral",
    "estimated_duration_seconds": 0,
    "production_quality": "professional/amateur/mixed"
}"""

            request_body = {
                "modelId": NOVA_OMNI_MODEL_ID,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "video": {
                                "format": video_format,
                                "source": {
                                    "s3Location": {"uri": video_s3_uri}
                                }
                            }
                        },
                        {"text": prompt}
                    ]
                }],
                "inferenceConfig": {
                    "temperature": 0.2,
                    "maxTokens": 1000
                }
            }

            response = self.bedrock.converse(**request_body)
            latency_ms = (time.time() - start) * 1000

            output_text = ""
            if 'output' in response and 'message' in response['output']:
                content = response['output']['message']['content']
                if content:
                    output_text = content[0].get('text', '')

            # Try to parse JSON
            quality_score = 0.0
            notes = []
            parsed_json = None

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', output_text)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group())
                    quality_score += 0.4
                    notes.append("Valid JSON parsed")

                    # Check for expected fields
                    expected_fields = ['summary', 'main_topic', 'visual_elements', 'sentiment']
                    found_fields = [f for f in expected_fields if f in parsed_json]
                    quality_score += 0.15 * len(found_fields)
                    notes.append(f"Found {len(found_fields)}/{len(expected_fields)} expected fields")

                except json.JSONDecodeError:
                    notes.append("JSON parsing failed")
            else:
                notes.append("No JSON found in response")

            result = TestResult(
                test_name="Nova Omni Structured Output",
                model_id=NOVA_OMNI_MODEL_ID,
                success=parsed_json is not None,
                latency_ms=latency_ms,
                output_sample=json.dumps(parsed_json, indent=2)[:500] if parsed_json else output_text[:300],
                quality_score=quality_score,
                notes=notes
            )

            if parsed_json:
                print(f"✅ PASSED - Latency: {latency_ms:.0f}ms, Quality: {quality_score:.2f}")
                print(f"   Parsed JSON: {json.dumps(parsed_json, indent=2)[:200]}...")
            else:
                print(f"⚠️ PARTIAL - Got response but couldn't parse JSON")
                print(f"   Raw output: {output_text[:200]}...")

        except Exception as e:
            result = TestResult(
                test_name="Nova Omni Structured Output",
                model_id=NOVA_OMNI_MODEL_ID,
                success=False,
                latency_ms=0,
                error=str(e)
            )
            print(f"❌ FAILED: {e}")

        self.results.append(result)
        return result

    # =========================================================================
    # OPTIMIZATION COMPARISON TEST
    # =========================================================================

    def test_optimization_comparison(self, video_bucket: str, video_key: str) -> Dict[str, Any]:
        """Compare current 8-call approach vs optimized consolidated approach"""
        print("\n" + "=" * 60)
        print("TEST: Optimization Comparison (8 calls vs 2 calls)")
        print("=" * 60)

        video_s3_uri = f"s3://{video_bucket}/{video_key}"
        video_format = video_key.split('.')[-1].lower()
        if video_format not in ['mp4', 'mov', 'mkv', 'webm']:
            video_format = 'mp4'

        results = {
            'current_approach': {'calls': 0, 'total_latency_ms': 0, 'outputs': {}},
            'optimized_approach': {'calls': 0, 'total_latency_ms': 0, 'outputs': {}}
        }

        # Current approach: Multiple separate calls (simulate 3 to save time)
        print("\n--- Current Approach (3 sample calls) ---")
        current_prompts = [
            ("summary", "Provide a brief summary of this video's visual content."),
            ("topics", "List the main topics and themes shown in this video."),
            ("sentiment", "Analyze the visual sentiment and emotional tone of this video.")
        ]

        for name, prompt in current_prompts:
            try:
                start = time.time()
                request_body = {
                    "modelId": NOVA_OMNI_MODEL_ID,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"video": {"format": video_format, "source": {"s3Location": {"uri": video_s3_uri}}}},
                            {"text": prompt}
                        ]
                    }],
                    "inferenceConfig": {"temperature": 0.3, "maxTokens": 1000}
                }
                response = self.bedrock.converse(**request_body)
                latency = (time.time() - start) * 1000

                output = response['output']['message']['content'][0].get('text', '')
                results['current_approach']['calls'] += 1
                results['current_approach']['total_latency_ms'] += latency
                results['current_approach']['outputs'][name] = output[:200]
                print(f"  {name}: {latency:.0f}ms")

            except Exception as e:
                print(f"  {name}: FAILED - {e}")

        # Optimized approach: Single comprehensive call
        print("\n--- Optimized Approach (1 comprehensive call) ---")
        optimized_prompt = """Analyze this video's visual content and provide a comprehensive analysis.

Return your analysis in this JSON format:
{
    "summary": "2-3 sentence summary of the video content",
    "topics": {
        "primary": ["main topic 1", "main topic 2"],
        "secondary": ["supporting topic 1", "supporting topic 2"]
    },
    "sentiment": {
        "overall": "positive/negative/neutral/mixed",
        "emotions": ["emotion1", "emotion2"],
        "confidence": "high/medium/low"
    },
    "highlights": [
        {"timestamp_seconds": 0, "description": "key moment"}
    ],
    "visual_elements": ["element1", "element2"],
    "hashtags": ["#tag1", "#tag2"]
}

Focus only on visual content (ignore audio)."""

        try:
            start = time.time()
            request_body = {
                "modelId": NOVA_OMNI_MODEL_ID,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"video": {"format": video_format, "source": {"s3Location": {"uri": video_s3_uri}}}},
                        {"text": optimized_prompt}
                    ]
                }],
                "inferenceConfig": {"temperature": 0.3, "maxTokens": 2000}
            }
            response = self.bedrock.converse(**request_body)
            latency = (time.time() - start) * 1000

            output = response['output']['message']['content'][0].get('text', '')
            results['optimized_approach']['calls'] = 1
            results['optimized_approach']['total_latency_ms'] = latency
            results['optimized_approach']['outputs']['comprehensive'] = output

            # Try to parse JSON
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    results['optimized_approach']['parsed_json'] = parsed
                    print(f"  Comprehensive call: {latency:.0f}ms (JSON parsed successfully)")
                except:
                    print(f"  Comprehensive call: {latency:.0f}ms (JSON parsing failed)")
            else:
                print(f"  Comprehensive call: {latency:.0f}ms")

        except Exception as e:
            print(f"  Comprehensive call: FAILED - {e}")

        # Calculate savings
        current_total = results['current_approach']['total_latency_ms']
        optimized_total = results['optimized_approach']['total_latency_ms']

        # Extrapolate current approach to 8 calls
        avg_per_call = current_total / max(results['current_approach']['calls'], 1)
        estimated_8_calls = avg_per_call * 8

        print("\n--- Comparison Summary ---")
        print(f"Current approach (3 calls): {current_total:.0f}ms total")
        print(f"Estimated 8 calls: {estimated_8_calls:.0f}ms")
        print(f"Optimized approach (1 call): {optimized_total:.0f}ms")
        print(f"Potential time savings: {(1 - optimized_total/estimated_8_calls)*100:.0f}%")
        print(f"Potential cost savings: ~{(1 - 1/8)*100:.0f}% (1 call vs 8 calls)")

        return results

    # =========================================================================
    # REPORT GENERATION
    # =========================================================================

    def generate_report(self) -> str:
        """Generate a comprehensive test report"""
        report = []
        report.append("\n" + "=" * 70)
        report.append("NOVA 2 MODEL VALIDATION REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Region: {self.region}")
        report.append("=" * 70)

        # Summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        avg_quality = sum(r.quality_score for r in self.results) / max(total_tests, 1)

        report.append(f"\nSUMMARY:")
        report.append(f"  Total Tests: {total_tests}")
        report.append(f"  Passed: {passed_tests}")
        report.append(f"  Failed: {total_tests - passed_tests}")
        report.append(f"  Average Quality Score: {avg_quality:.2f}")

        # Model-specific results
        report.append("\nRESULTS BY MODEL:")

        models = {}
        for r in self.results:
            if r.model_id not in models:
                models[r.model_id] = []
            models[r.model_id].append(r)

        for model_id, model_results in models.items():
            report.append(f"\n  {model_id}:")
            for r in model_results:
                status = "✅" if r.success else "❌"
                report.append(f"    {status} {r.test_name}")
                report.append(f"       Latency: {r.latency_ms:.0f}ms, Quality: {r.quality_score:.2f}")
                if r.notes:
                    report.append(f"       Notes: {', '.join(r.notes)}")
                if r.error:
                    report.append(f"       Error: {r.error}")

        # Recommendations
        report.append("\nRECOMMENDATIONS:")

        if avg_quality >= 0.7:
            report.append("  ✅ Model quality is good for production use")
        elif avg_quality >= 0.5:
            report.append("  ⚠️ Model quality is acceptable but may need prompt tuning")
        else:
            report.append("  ❌ Model quality needs improvement - review prompts and model selection")

        failed_models = [r.model_id for r in self.results if not r.success]
        if failed_models:
            report.append(f"  ⚠️ Failed models need investigation: {set(failed_models)}")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='Validate Nova 2 model performance')
    parser.add_argument('--video-bucket', help='S3 bucket containing test video')
    parser.add_argument('--video-key', help='S3 key of test video')
    parser.add_argument('--compare', action='store_true', help='Run optimization comparison')
    parser.add_argument('--skip-video', action='store_true', help='Skip video tests')
    args = parser.parse_args()

    print("=" * 70)
    print("NOVA 2 MODEL PERFORMANCE VALIDATION")
    print("=" * 70)
    print(f"Region: {REGION}")
    print(f"Nova Lite: {NOVA_LITE_MODEL_ID}")
    print(f"Nova Omni: {NOVA_OMNI_MODEL_ID}")
    print(f"Nova Embedding: {NOVA_EMBEDDING_MODEL_ID}")
    print(f"Embedding Dimension: {NOVA_EMBEDDING_DIMENSION}")

    validator = NovaModelValidator()

    # Run text-based tests (no video required)
    print("\n" + "=" * 70)
    print("PHASE 1: Text-Based Model Tests")
    print("=" * 70)

    validator.test_nova_lite_basic()
    validator.test_nova_lite_tool_use_ner()
    validator.test_nova_embedding_text()
    validator.test_nova_embedding_semantic_similarity()

    # Run video tests if bucket/key provided
    if not args.skip_video and args.video_bucket and args.video_key:
        print("\n" + "=" * 70)
        print("PHASE 2: Video-Based Model Tests")
        print("=" * 70)

        validator.test_nova_omni_video_basic(args.video_bucket, args.video_key)
        validator.test_nova_omni_video_structured(args.video_bucket, args.video_key)

        if args.compare:
            print("\n" + "=" * 70)
            print("PHASE 3: Optimization Comparison")
            print("=" * 70)
            validator.test_optimization_comparison(args.video_bucket, args.video_key)

    elif not args.skip_video:
        print("\n⚠️ Skipping video tests - use --video-bucket and --video-key to enable")

    # Generate report
    report = validator.generate_report()
    print(report)

    # Exit with appropriate code
    failed = sum(1 for r in validator.results if not r.success)
    if failed > 0:
        print(f"\n⚠️ {failed} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
