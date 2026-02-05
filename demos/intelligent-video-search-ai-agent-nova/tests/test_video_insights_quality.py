#!/usr/bin/env python3
"""
Video Insights Quality Evaluation Script

Tests the full video understanding pipeline to evaluate output quality
for marketing teams.
"""

import boto3
import json
import time
import sys
import os
import re
from typing import Dict, Any, List

# Configuration
REGION = os.environ.get('AWS_REGION', 'us-east-1')
NOVA_OMNI_MODEL_ID = os.environ.get('NOVA_OMNI_MODEL_ID', 'global.amazon.nova-2-omni-v1:0')
NOVA_LITE_MODEL_ID = os.environ.get('NOVA_LITE_MODEL_ID', 'global.amazon.nova-2-lite-v1:0')


def invoke_nova_omni_video(bedrock: Any, prompt: str, video_s3_uri: str) -> str:
    """Invoke Nova Omni for video understanding"""
    video_format = video_s3_uri.split('.')[-1].lower()
    if video_format not in ['mp4', 'mov', 'mkv', 'webm']:
        video_format = 'mp4'

    response = bedrock.converse(
        modelId=NOVA_OMNI_MODEL_ID,
        messages=[{
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
        inferenceConfig={
            "temperature": 0.3,
            "maxTokens": 4000
        }
    )

    if 'output' in response and 'message' in response['output']:
        content = response['output']['message']['content']
        if content and len(content) > 0:
            return content[0].get('text', '')
    return ""


def parse_json_array(response: str) -> List[Dict]:
    """Extract JSON array from response"""
    # Try direct parse first (most common case)
    try:
        data = json.loads(response.strip())
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try extracting from code blocks
    code_match = re.search(r'```(?:json)?\n?([\s\S]*?)```', response)
    if code_match:
        try:
            data = json.loads(code_match.group(1))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Try array pattern extraction
    try:
        json_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', response)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    return []


def evaluate_quality(name: str, result: Any, criteria: Dict[str, callable]) -> Dict[str, Any]:
    """Evaluate result against quality criteria"""
    scores = {}
    for criterion, check_fn in criteria.items():
        try:
            scores[criterion] = check_fn(result)
        except Exception:
            scores[criterion] = False

    passed = sum(1 for v in scores.values() if v)
    total = len(scores)
    return {
        'name': name,
        'scores': scores,
        'passed': passed,
        'total': total,
        'percentage': (passed / total * 100) if total > 0 else 0
    }


def run_insights_evaluation(video_bucket: str, video_key: str):
    """Run full insights evaluation"""
    bedrock = boto3.client('bedrock-runtime', region_name=REGION)
    video_s3_uri = f"s3://{video_bucket}/{video_key}"

    print("=" * 70)
    print("VIDEO INSIGHTS QUALITY EVALUATION")
    print("=" * 70)
    print(f"Video: {video_s3_uri}")
    print(f"Model: {NOVA_OMNI_MODEL_ID}")
    print("=" * 70)

    results = {}
    evaluations = []
    total_time = 0

    # 1. SUMMARY
    print("\n[1/8] SUMMARY - Comprehensive Visual Analysis")
    print("-" * 50)
    start = time.time()
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

    summary = invoke_nova_omni_video(bedrock, summary_prompt, video_s3_uri)
    latency = time.time() - start
    total_time += latency
    results['summary'] = summary

    print(f"Latency: {latency:.1f}s | Length: {len(summary)} chars")
    print(f"\nOutput:\n{summary[:800]}...")

    eval_result = evaluate_quality('Summary', summary, {
        'has_content_overview': lambda x: 'content' in x.lower() or 'about' in x.lower(),
        'has_visual_elements': lambda x: any(w in x.lower() for w in ['visual', 'scene', 'shot', 'camera']),
        'has_audience_insight': lambda x: 'audience' in x.lower() or 'viewer' in x.lower(),
        'has_brand_mentions': lambda x: any(w in x.lower() for w in ['brand', 'logo', 'product', 'marketing']),
        'substantial_length': lambda x: len(x) > 500,
        'structured_format': lambda x: any(c in x for c in ['1.', '2.', '-', '•', '\n\n'])
    })
    evaluations.append(eval_result)

    # 2. CHAPTERS
    print("\n[2/8] CHAPTERS - Scene-by-Scene Breakdown")
    print("-" * 50)
    start = time.time()
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

    chapters_raw = invoke_nova_omni_video(bedrock, chapters_prompt, video_s3_uri)
    chapters = parse_json_array(chapters_raw)
    latency = time.time() - start
    total_time += latency
    results['chapters'] = chapters

    print(f"Latency: {latency:.1f}s | Chapters found: {len(chapters)}")
    print(f"\nParsed Chapters:")
    for ch in chapters[:5]:
        print(f"  [{ch.get('start', '?')}-{ch.get('end', '?')}s] {ch.get('title', 'N/A')}")

    eval_result = evaluate_quality('Chapters', chapters, {
        'is_array': lambda x: isinstance(x, list),
        'has_multiple_chapters': lambda x: len(x) >= 2,
        'has_timestamps': lambda x: all('start' in c and 'end' in c for c in x) if x else False,
        'has_titles': lambda x: all('title' in c for c in x) if x else False,
        'has_summaries': lambda x: all('summary' in c for c in x) if x else False,
        'sequential_times': lambda x: all(x[i]['end'] <= x[i+1]['start'] + 5 for i in range(len(x)-1)) if len(x) > 1 else True
    })
    evaluations.append(eval_result)

    # 3. HIGHLIGHTS
    print("\n[3/8] HIGHLIGHTS - Key Visual Moments")
    print("-" * 50)
    start = time.time()
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

    highlights_raw = invoke_nova_omni_video(bedrock, highlights_prompt, video_s3_uri)
    highlights = parse_json_array(highlights_raw)
    latency = time.time() - start
    total_time += latency
    results['highlights'] = highlights

    print(f"Latency: {latency:.1f}s | Highlights found: {len(highlights)}")
    print(f"\nParsed Highlights:")
    for hl in highlights[:5]:
        print(f"  [{hl.get('start', '?')}-{hl.get('end', '?')}s] [{hl.get('type', 'N/A')}] {hl.get('highlight', 'N/A')[:60]}")

    eval_result = evaluate_quality('Highlights', highlights, {
        'is_array': lambda x: isinstance(x, list),
        'has_multiple_highlights': lambda x: len(x) >= 3,
        'has_timestamps': lambda x: all('start' in h and 'end' in h for h in x) if x else False,
        'has_descriptions': lambda x: all('highlight' in h or 'description' in h for h in x) if x else False,
        'has_types': lambda x: all('type' in h for h in x) if x else False,
        'marketing_useful': lambda x: any(h.get('type', '') in ['brand moment', 'key reveal', 'emotional peak', 'visual climax'] for h in x) if x else False
    })
    evaluations.append(eval_result)

    # 4. TOPICS
    print("\n[4/8] TOPICS - Theme Extraction")
    print("-" * 50)
    start = time.time()
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

    topics = invoke_nova_omni_video(bedrock, topics_prompt, video_s3_uri)
    latency = time.time() - start
    total_time += latency
    results['topics'] = topics

    print(f"Latency: {latency:.1f}s | Length: {len(topics)} chars")
    print(f"\nOutput:\n{topics[:600]}...")

    eval_result = evaluate_quality('Topics', topics, {
        'has_primary_topics': lambda x: 'primary' in x.lower(),
        'has_secondary_topics': lambda x: 'secondary' in x.lower(),
        'has_keywords': lambda x: 'keyword' in x.lower(),
        'has_industry': lambda x: 'industry' in x.lower() or 'category' in x.lower(),
        'structured_format': lambda x: any(c in x for c in ['-', '•', '1.', '2.']),
        'substantial_content': lambda x: len(x) > 300
    })
    evaluations.append(eval_result)

    # 5. HASHTAGS
    print("\n[5/8] HASHTAGS - Social Media Tags")
    print("-" * 50)
    start = time.time()
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

    hashtags = invoke_nova_omni_video(bedrock, hashtags_prompt, video_s3_uri)
    latency = time.time() - start
    total_time += latency
    results['hashtags'] = hashtags

    print(f"Latency: {latency:.1f}s | Length: {len(hashtags)} chars")
    print(f"\nOutput:\n{hashtags[:500]}...")

    # Count hashtags
    hashtag_count = len(re.findall(r'#\w+', hashtags))

    eval_result = evaluate_quality('Hashtags', hashtags, {
        'has_hashtags': lambda x: '#' in x,
        'has_multiple_hashtags': lambda x: len(re.findall(r'#\w+', x)) >= 10,
        'has_categories': lambda x: any(c.lower() in x.lower() for c in ['content', 'industry', 'style', 'trending']),
        'lowercase_format': lambda x: any(re.match(r'#[a-z]+', tag) for tag in re.findall(r'#\w+', x)),
        'no_spaces_in_tags': lambda x: not re.search(r'#\w+\s+\w+#', x),
        'marketing_relevant': lambda x: any(tag in x.lower() for tag in ['#marketing', '#brand', '#content', '#video'])
    })
    evaluations.append(eval_result)
    print(f"Hashtags found: {hashtag_count}")

    # 6. SENTIMENT
    print("\n[6/8] SENTIMENT - Emotional Analysis")
    print("-" * 50)
    start = time.time()
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

    sentiment = invoke_nova_omni_video(bedrock, sentiment_prompt, video_s3_uri)
    latency = time.time() - start
    total_time += latency
    results['sentiment'] = sentiment

    print(f"Latency: {latency:.1f}s | Length: {len(sentiment)} chars")
    print(f"\nOutput:\n{sentiment[:600]}...")

    eval_result = evaluate_quality('Sentiment', sentiment, {
        'has_sentiment_label': lambda x: any(s in x.lower() for s in ['positive', 'negative', 'neutral', 'mixed']),
        'has_emotions': lambda x: any(e in x.lower() for e in ['happy', 'excited', 'calm', 'confident', 'professional', 'warm', 'trust']),
        'has_color_analysis': lambda x: 'color' in x.lower(),
        'has_body_language': lambda x: 'body' in x.lower() or 'facial' in x.lower() or 'expression' in x.lower(),
        'has_confidence': lambda x: 'confidence' in x.lower() or 'high' in x.lower() or 'medium' in x.lower(),
        'structured_analysis': lambda x: any(c in x for c in ['1.', '2.', '-', '•'])
    })
    evaluations.append(eval_result)

    # 7. CONTENT ANALYTICS
    print("\n[7/8] CONTENT ANALYTICS - Technical Analysis")
    print("-" * 50)
    start = time.time()
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

    analytics = invoke_nova_omni_video(bedrock, analytics_prompt, video_s3_uri)
    latency = time.time() - start
    total_time += latency
    results['analytics'] = analytics

    print(f"Latency: {latency:.1f}s | Length: {len(analytics)} chars")
    print(f"\nOutput:\n{analytics[:600]}...")

    eval_result = evaluate_quality('Analytics', analytics, {
        'has_scene_count': lambda x: any(c in x for c in ['scene', 'location', 'setting']),
        'has_shot_types': lambda x: any(s in x.lower() for s in ['close-up', 'wide', 'medium', 'shot']),
        'has_people_count': lambda x: 'people' in x.lower() or 'person' in x.lower(),
        'has_production_quality': lambda x: any(q in x.lower() for q in ['professional', 'quality', 'production']),
        'has_format_type': lambda x: any(f in x.lower() for f in ['tutorial', 'advertisement', 'interview', 'documentary']),
        'has_engagement_analysis': lambda x: 'engagement' in x.lower() or 'attention' in x.lower() or 'hook' in x.lower()
    })
    evaluations.append(eval_result)

    # 8. VISUAL OBJECTS
    print("\n[8/8] VISUAL OBJECTS - Object Detection")
    print("-" * 50)
    start = time.time()
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

    objects = invoke_nova_omni_video(bedrock, objects_prompt, video_s3_uri)
    latency = time.time() - start
    total_time += latency
    results['objects'] = objects

    print(f"Latency: {latency:.1f}s | Length: {len(objects)} chars")
    print(f"\nOutput:\n{objects[:600]}...")

    eval_result = evaluate_quality('Objects', objects, {
        'has_objects_list': lambda x: 'object' in x.lower() or 'item' in x.lower(),
        'has_people_count': lambda x: any(c in x.lower() for c in ['people', 'person', 'individual']),
        'has_actions': lambda x: 'action' in x.lower() or 'perform' in x.lower() or 'doing' in x.lower(),
        'has_location_info': lambda x: 'location' in x.lower() or 'indoor' in x.lower() or 'outdoor' in x.lower(),
        'has_brand_detection': lambda x: 'brand' in x.lower() or 'logo' in x.lower(),
        'structured_format': lambda x: any(c in x for c in ['-', '•', '1.', '2.'])
    })
    evaluations.append(eval_result)

    # FINAL REPORT
    print("\n" + "=" * 70)
    print("QUALITY EVALUATION REPORT")
    print("=" * 70)

    total_passed = 0
    total_criteria = 0

    for eval_item in evaluations:
        status = "✅" if eval_item['percentage'] >= 80 else "⚠️" if eval_item['percentage'] >= 50 else "❌"
        print(f"{status} {eval_item['name']}: {eval_item['passed']}/{eval_item['total']} criteria ({eval_item['percentage']:.0f}%)")
        for criterion, passed in eval_item['scores'].items():
            icon = "✓" if passed else "✗"
            print(f"      {icon} {criterion}")
        total_passed += eval_item['passed']
        total_criteria += eval_item['total']

    overall_score = (total_passed / total_criteria * 100) if total_criteria > 0 else 0

    print("\n" + "-" * 70)
    print(f"OVERALL QUALITY SCORE: {total_passed}/{total_criteria} ({overall_score:.1f}%)")
    print(f"TOTAL PROCESSING TIME: {total_time:.1f}s ({total_time/8:.1f}s avg per call)")
    print("-" * 70)

    # Marketing team assessment
    print("\n" + "=" * 70)
    print("MARKETING TEAM ASSESSMENT")
    print("=" * 70)

    marketing_checks = {
        'Brand Detection': 'brand' in str(results).lower() or 'logo' in str(results).lower(),
        'Hashtag Generation': len(re.findall(r'#\w+', results.get('hashtags', ''))) >= 10,
        'Sentiment Analysis': any(s in results.get('sentiment', '').lower() for s in ['positive', 'negative', 'neutral']),
        'Chapter Timestamps': len(results.get('chapters', [])) >= 2,
        'Highlight Clips': len(results.get('highlights', [])) >= 3,
        'Target Audience': 'audience' in results.get('summary', '').lower(),
        'Visual Style Analysis': 'visual' in results.get('summary', '').lower(),
        'Engagement Predictors': 'engagement' in results.get('analytics', '').lower() or 'hook' in results.get('analytics', '').lower()
    }

    for check, passed in marketing_checks.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {check}")

    marketing_score = sum(marketing_checks.values()) / len(marketing_checks) * 100
    print(f"\nMARKETING READINESS: {marketing_score:.0f}%")

    if marketing_score >= 80:
        print("✅ Ready for marketing team use")
    elif marketing_score >= 60:
        print("⚠️ Acceptable with some manual review")
    else:
        print("❌ Needs improvement before marketing use")

    return results, evaluations


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Evaluate video insights quality')
    parser.add_argument('--video-bucket', required=True, help='S3 bucket containing test video')
    parser.add_argument('--video-key', required=True, help='S3 key of test video')
    args = parser.parse_args()

    run_insights_evaluation(args.video_bucket, args.video_key)
