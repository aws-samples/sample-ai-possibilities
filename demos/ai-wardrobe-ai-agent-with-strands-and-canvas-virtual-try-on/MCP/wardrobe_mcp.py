#!/usr/bin/env python3
"""
AI Unicorn Wardrobe MCP Server

This server provides specialized tools for managing a virtual wardrobe.
It handles image uploads, clothing analysis, and virtual try-on operations
using AWS services like Bedrock, DynamoDB, and S3.
"""

import os
import json
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional
from mcp.server import FastMCP
from PIL import Image
import io
import base64
import requests
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()

# Create the MCP server instance with our tool collection
mcp = FastMCP("AI Unicorn Wardrobe Tools")

# AI model settings - configure which Bedrock models to use for different tasks
MODEL_CONFIG = {
    "analysis_model": {
        "id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "name": "Claude 3.5 Sonnet",
        "max_tokens": 1500,
        "temperature": 0.3,
        "image_size_limit_kb": 800
    },
    "profile_validation_model": {
        "id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0", 
        "name": "Claude 3.5 Sonnet",
        "max_tokens": 800,
        "temperature": 0.1,
        "image_size_limit_kb": 800
    }
    # Add other models here as needed:
    # "haiku": {
    #     "id": "us.anthropic.claude-3-haiku-20240307-v1:0",
    #     "name": "Claude 3 Haiku",
    #     "max_tokens": 1000,
    #     "temperature": 0.3,
    #     "image_size_limit_kb": 500
    # }
}

def prepare_for_dynamodb(obj):
    """Prepare data for DynamoDB storage by converting floats to Decimal format"""
    # Use JSON to convert then parse with Decimal
    return json.loads(json.dumps(obj), parse_float=Decimal)

def resize_image_for_claude(image_base64: str, max_size_kb: int = 1024) -> str:
    """Optimize image size for Claude Vision API while preserving quality for analysis"""
    try:
        import base64
        from PIL import Image
        import io
        
        # Decode base64 image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Calculate current size in KB
        current_size_kb = len(image_data) / 1024
        
        if current_size_kb <= max_size_kb:
            # Already small enough
            return image_base64
        
        # Calculate resize ratio to target size
        resize_ratio = (max_size_kb / current_size_kb) ** 0.5
        new_width = int(image.width * resize_ratio)
        new_height = int(image.height * resize_ratio)
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to bytes with optimized quality
        output = io.BytesIO()
        quality = 85
        while quality > 30:
            output.seek(0)
            output.truncate(0)
            resized_image.save(output, format='JPEG', quality=quality, optimize=True)
            
            if len(output.getvalue()) / 1024 <= max_size_kb:
                break
            quality -= 10
        
        # Encode back to base64
        output.seek(0)
        resized_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
        
        print(f"Image resized: {current_size_kb:.1f}KB → {len(output.getvalue())/1024:.1f}KB")
        return resized_base64
        
    except Exception as e:
        print(f"Image resize failed: {e}")
        # Return original if resize fails
        return image_base64

def analyze_clothing_item_with_claude(image_base64: str, category: str, user_attributes: dict) -> dict:
    """Use Claude to analyze a clothing item and extract detailed attributes"""
    try:
        print(f"=== Analyzing clothing item with Claude ===")
        print(f"  category: {category}")
        print(f"  user_attributes: {user_attributes}")
        
        # Get model configuration
        model_config = MODEL_CONFIG["analysis_model"]
        
        # Resize image for Claude analysis (keep original for Nova Canvas)
        analysis_image = resize_image_for_claude(image_base64, max_size_kb=model_config["image_size_limit_kb"])
        
        prompt = f"""
Analyze this {category} clothing item image and provide detailed fashion attributes. Consider the user provided these details:
- Color: {user_attributes.get('color', 'not specified')}
- Style: {user_attributes.get('style', 'not specified')}
- Season: {user_attributes.get('season', 'not specified')}
- Description: {user_attributes.get('description', 'not specified')}

Please analyze the image and return a JSON object with these attributes:
{{
    "color": "primary color of the garment",
    "secondaryColors": ["list", "of", "secondary", "colors"],
    "material": "estimated fabric type (cotton, polyester, wool, etc.)",
    "pattern": "solid, striped, floral, plaid, etc.",
    "fit": "loose, fitted, regular, oversized, etc.",
    "formalityLevel": "casual, business-casual, formal, athletic",
    "styleCategory": "classic, trendy, vintage, minimalist, bohemian, etc.",
    "versatility": "high, medium, low - how well it pairs with other items",
    "seasonality": ["spring", "summer", "fall", "winter"] - which seasons it's suitable for,
    "occasions": ["casual", "work", "party", "athletic", "formal"] - appropriate occasions,
    "weatherSuitability": "hot, warm, cool, cold, any",
    "timeOfDay": "morning, afternoon, evening, night, any",
    "colorTemperature": "warm, cool, neutral",
    "layeringType": "base, mid, outer, standalone",
    "careInstructions": "estimated care requirements",
    "description": "detailed description of the item including style, cut, and notable features"
}}

Focus on accuracy and be specific. If the user provided attributes conflict with what you see, note this in your analysis but prioritize what you observe in the image.
"""

        response = bedrock_runtime.invoke_model(
            modelId=model_config["id"],
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': 'image/jpeg',
                                'data': analysis_image
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }],
                'max_tokens': model_config["max_tokens"],
                'temperature': model_config["temperature"]
            })
        )
        
        result = json.loads(response['body'].read())
        claude_response = result['content'][0]['text']
        
        print(f"Claude analysis response: {claude_response}")
        
        # Parse the JSON response from Claude
        try:
            # Extract JSON from Claude's response (it might be wrapped in markdown)
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', claude_response, re.DOTALL)
            if json_match:
                analysis_json = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', claude_response, re.DOTALL)
                if json_match:
                    analysis_json = json_match.group(0)
                else:
                    analysis_json = claude_response
            
            analysis = json.loads(analysis_json)
            print(f"Parsed Claude analysis: {analysis}")
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse Claude response as JSON: {e}")
            print(f"Raw response: {claude_response}")
            # Return basic fallback analysis
            return {
                'color': user_attributes.get('color', 'unknown'),
                'category': category,
                'style': user_attributes.get('style', 'casual'),
                'material': 'unknown',
                'pattern': 'unknown',
                'fit': 'regular',
                'description': user_attributes.get('description', f'{category} item')
            }
            
    except Exception as e:
        print(f"Claude analysis failed: {e}")
        print("Falling back to basic analysis based on user input")
        # Return enhanced fallback analysis using user attributes
        return {
            'color': user_attributes.get('color', 'unknown'),
            'secondaryColors': [],
            'category': category,
            'style': user_attributes.get('style', 'casual'),
            'material': 'cotton',  # Common default
            'pattern': 'solid',   # Common default
            'fit': 'regular',
            'formalityLevel': 'casual' if user_attributes.get('style', 'casual') == 'casual' else 'business-casual',
            'styleCategory': user_attributes.get('style', 'classic'),
            'versatility': 'medium',
            'seasonality': [user_attributes.get('season', 'all-season')] if user_attributes.get('season') != 'all' else ['spring', 'summer', 'fall', 'winter'],
            'occasions': ['casual', 'everyday'],
            'weatherSuitability': 'any',
            'timeOfDay': 'any',
            'colorTemperature': 'neutral',
            'layeringType': 'standalone',
            'careInstructions': 'Machine wash cold',
            'description': user_attributes.get('description', f'{category} item in {user_attributes.get("color", "unknown")} color')
        }

# AWS Clients
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# Table references
USERS_TABLE = os.getenv('USERS_TABLE', 'ai-wardrobe-users')
WARDROBE_ITEMS_TABLE = os.getenv('WARDROBE_ITEMS_TABLE', 'ai-wardrobe-wardrobe-items')
OUTFITS_TABLE = os.getenv('OUTFITS_TABLE', 'ai-wardrobe-outfits')
S3_BUCKET = os.getenv('S3_BUCKET', 'ai-wardrobe-images')

# In-memory storage for demo purposes (fallback when DynamoDB is not available)
in_memory_users = {}
in_memory_wardrobe_items = {}
in_memory_outfits = {}

try:
    users_table = dynamodb.Table(USERS_TABLE)
    wardrobe_items_table = dynamodb.Table(WARDROBE_ITEMS_TABLE)
    outfits_table = dynamodb.Table(OUTFITS_TABLE)
    use_dynamodb = True
    print("Using DynamoDB for storage")
except Exception as e:
    print(f"DynamoDB not available, using in-memory storage: {e}")
    use_dynamodb = False


@mcp.tool(description="Validate a profile photo for virtual try-on compatibility")
def validate_user_photo(image_base64: str) -> Dict[str, Any]:
    """Validate a profile photo before upload to ensure Nova Canvas compatibility"""
    return validate_profile_photo(image_base64)


@mcp.tool(description="Validate a clothing item image for virtual try-on compatibility")
def validate_clothing_image(image_base64: str, category: str = "unknown") -> Dict[str, Any]:
    """Validate a clothing item image before upload to ensure Nova Canvas compatibility"""
    return validate_clothing_item_image(image_base64, category)


@mcp.tool(description="Create or get a user by name")
def manage_user(user_name: str, profile_photo_base64: Optional[str] = None) -> Dict[str, Any]:
    """Create a new user or retrieve existing user by name"""
    try:
        print(f"\n=== manage_user called ===")
        print(f"  user_name: {user_name}")
        print(f"  has_photo: {profile_photo_base64 is not None}")
        print(f"  use_dynamodb: {use_dynamodb}")
        
        # First, try to find existing user by userName using DynamoDB GSI
        existing_user = None
        
        if use_dynamodb:
            try:
                # Query the userName-index GSI to find existing user
                response = users_table.query(
                    IndexName='userName-index',
                    KeyConditionExpression='userName = :username',
                    ExpressionAttributeValues={':username': user_name},
                    Limit=1
                )
                
                print(f"  DynamoDB query response: {response.get('Count', 0)} items found")
                print(f"  Response: {response}")
                
                if response['Items']:
                    existing_user = response['Items'][0]
                    
                    # If user has S3 photo, generate presigned URL
                    if existing_user.get('profilePhotoUrl', '').startswith('s3://'):
                        try:
                            s3_key = existing_user['profilePhotoUrl'].replace(f's3://{S3_BUCKET}/', '')
                            # Get the photo from S3 and convert to base64 for frontend
                            photo_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
                            photo_data = photo_obj['Body'].read()
                            existing_user['profilePhotoBase64'] = base64.b64encode(photo_data).decode('utf-8')
                            print(f"  Retrieved profile photo from S3 for user {user_name}")
                        except Exception as s3_error:
                            print(f"  Failed to retrieve photo from S3: {s3_error}")
                    
                    # Also cache in memory for faster subsequent access
                    in_memory_users[existing_user['userId']] = existing_user
                    print(f"Found existing user {user_name} in DynamoDB with ID {existing_user['userId']}")
                else:
                    print(f"  No existing user found for userName: {user_name}")
                
            except Exception as db_error:
                print(f"DynamoDB query error: {db_error}")
                # If DynamoDB fails, fall back to in-memory check
                for user_id, user in in_memory_users.items():
                    if user.get('userName') == user_name:
                        existing_user = user
                        break
        else:
            # Fallback to in-memory storage when DynamoDB is not available
            for user_id, user in in_memory_users.items():
                if user.get('userName') == user_name:
                    existing_user = user
                    break
        
        if existing_user:
            # User exists - update photo if provided, otherwise return existing data
            if profile_photo_base64:
                validation_result = validate_profile_photo(profile_photo_base64)
                
                if not validation_result['valid']:
                    return {
                        "status": "validation_error",
                        "errors": validation_result['errors'],
                        "warnings": validation_result['warnings'],
                        "recommendations": validation_result['recommendations']
                    }
                
                # Store photo in S3 instead of DynamoDB
                try:
                    photo_data = base64.b64decode(profile_photo_base64)
                    photo_s3_key = f"users/{existing_user['userId']}/profile-photo.jpg"
                    s3_client.put_object(
                        Bucket=S3_BUCKET,
                        Key=photo_s3_key,
                        Body=photo_data,
                        ContentType='image/jpeg'
                    )
                    existing_user['profilePhotoUrl'] = f"s3://{S3_BUCKET}/{photo_s3_key}"
                    print(f"Uploaded profile photo to S3: {photo_s3_key}")
                except Exception as s3_error:
                    print(f"S3 upload error: {s3_error}")
                    existing_user['profilePhotoUrl'] = f"demo://profile-{existing_user['userId']}"
                
                # Don't store base64 in DynamoDB - too large!
                # existing_user['profilePhotoBase64'] = profile_photo_base64
                
                existing_user['photoValidation'] = {
                    "warnings": validation_result['warnings'],
                    "recommendations": validation_result['recommendations'],
                    "image_info": validation_result['image_info']
                }
                
                # Update in both DynamoDB and memory
                if use_dynamodb:
                    try:
                        users_table.update_item(
                            Key={'userId': existing_user['userId']},
                            UpdateExpression='SET profilePhotoUrl = :url, photoValidation = :validation',
                            ExpressionAttributeValues={
                                ':url': existing_user['profilePhotoUrl'],
                                ':validation': prepare_for_dynamodb(existing_user['photoValidation'])
                            }
                        )
                        print(f"Updated photo in DynamoDB for existing user {user_name}")
                    except Exception as update_error:
                        print(f"DynamoDB update error: {update_error}")
                
                # Update in memory cache
                in_memory_users[existing_user['userId']] = existing_user
                
                return {
                    "status": "existing",
                    "user": existing_user
                }
            else:
                # Return existing user data
                print(f"Found existing user {user_name}")
                return {
                    "status": "existing",
                    "user": existing_user
                }
        
        # Create new user
        user_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        user = {
            'userId': user_id,
            'userName': user_name,
            'createdAt': timestamp,
            'wardrobeItems': []
        }
        
        # Validate and store profile photo if provided
        if profile_photo_base64:
            validation_result = validate_profile_photo(profile_photo_base64)
            
            if not validation_result['valid']:
                return {
                    "status": "validation_error",
                    "errors": validation_result['errors'],
                    "warnings": validation_result['warnings'],
                    "recommendations": validation_result['recommendations']
                }
            
            # Store photo in S3 instead of DynamoDB to avoid size limits
            try:
                photo_data = base64.b64decode(profile_photo_base64)
                photo_s3_key = f"users/{user_id}/profile-photo.jpg"
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=photo_s3_key,
                    Body=photo_data,
                    ContentType='image/jpeg'
                )
                user['profilePhotoUrl'] = f"s3://{S3_BUCKET}/{photo_s3_key}"
                print(f"Uploaded profile photo to S3: {photo_s3_key}")
            except Exception as s3_error:
                print(f"S3 upload error: {s3_error}")
                user['profilePhotoUrl'] = f"demo://profile-{user_id}"
            
            # Don't store base64 in DynamoDB - too large!
            # user['profilePhotoBase64'] = profile_photo_base64
            
            user['photoValidation'] = {
                "warnings": validation_result['warnings'],
                "recommendations": validation_result['recommendations'],
                "image_info": validation_result['image_info']
            }
        
        # Store user in both DynamoDB and memory
        if use_dynamodb:
            try:
                # Convert floats to Decimal for DynamoDB
                user_for_dynamo = prepare_for_dynamodb(user)
                users_table.put_item(Item=user_for_dynamo)
                print(f"Stored new user {user_name} in DynamoDB with ID {user_id}")
            except Exception as store_error:
                print(f"DynamoDB store error: {store_error}")
                # Even if DynamoDB fails, continue with in-memory storage
        
        # Always store in memory as cache/fallback
        in_memory_users[user_id] = user
        print(f"Created user {user_name} with ID {user_id}")
        
        # Return user data (including base64 if just uploaded)
        return_user = user.copy()
        if profile_photo_base64 and 'profilePhotoUrl' in user:
            return_user['profilePhotoBase64'] = profile_photo_base64
        
        return {
            "status": "created",
            "user": return_user
        }
        
    except Exception as e:
        print(f"manage_user error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@mcp.tool(description="Upload a clothing item to user's wardrobe")
def upload_wardrobe_item(
    user_id: str,
    image_base64: str,
    category: str,
    color: Optional[str] = None,
    style: Optional[str] = None,
    season: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Upload a new clothing item to the user's wardrobe"""
    try:
        print(f"=== upload_wardrobe_item called ===")
        print(f"  user_id: {user_id}")
        print(f"  category: {category}")
        print(f"  has_image: {bool(image_base64)}")
        
        # Validate image first
        validation_result = validate_clothing_item_image(image_base64, category)
        if not validation_result.get('valid', False):
            return {
                "error": "validation_error",
                "message": f"Image validation failed: {validation_result.get('error', 'Unknown error')}",
                "validation": validation_result
            }
        
        item_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Upload image to S3
        s3_key = f"users/{user_id}/wardrobe/{item_id}.jpg"
        
        try:
            # Decode base64 image and upload to S3
            import base64
            image_data = base64.b64decode(image_base64)
            
            # Store both the image and metadata in S3
            # Upload the actual image
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=image_data,
                ContentType='image/jpeg',
                Metadata={
                    'user_id': user_id,
                    'item_id': item_id,
                    'category': category,
                    'uploaded_at': timestamp
                }
            )
            
            print(f"Successfully uploaded image to S3: s3://{S3_BUCKET}/{s3_key}")
        except Exception as e:
            print(f"S3 upload failed: {e}")
            return {"error": f"Failed to upload to S3: {str(e)}"}
        
        # Use Claude to analyze the clothing item
        analysis = analyze_clothing_item_with_claude(image_base64, category, {
            'color': color,
            'style': style,
            'season': season,
            'description': description
        })
        
        # Merge user-provided attributes with AI analysis
        comprehensive_attributes = analysis.copy()
        
        # Override with user-provided values if available
        if color:
            comprehensive_attributes['color'] = color
        if style:
            comprehensive_attributes['styleCategory'] = style
        if season:
            comprehensive_attributes['seasonality'] = [season] if season != 'all' else ['all-season']
        if description:
            comprehensive_attributes['description'] = description
        
        # Create wardrobe item with comprehensive attributes and validation info
        item = {
            'itemId': item_id,
            'userId': user_id,
            'imageUrl': f"s3://{S3_BUCKET}/{s3_key}",
            'category': category,
            'attributes': comprehensive_attributes,
            'uploadedAt': timestamp,
            'analysisVersion': '2.0',  # Track analysis version for future upgrades
            'imageValidation': {
                "warnings": validation_result['warnings'],
                "recommendations": validation_result['recommendations'],
                "category_specific": validation_result['category_specific'],
                "image_info": validation_result['image_info']
            }
        }
        
        # Store metadata as a JSON file alongside the image in S3
        try:
            metadata_key = f"users/{user_id}/wardrobe/{item_id}_metadata.json"
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=metadata_key,
                Body=json.dumps(item, indent=2),
                ContentType='application/json'
            )
            print(f"Successfully stored metadata to S3: {metadata_key}")
        except Exception as e:
            print(f"Failed to store metadata to S3: {e}")
            # Continue anyway - item will be available in memory
        
        print(f"upload_wardrobe_item: Item {item_id} successfully stored in S3 for user {user_id}")
        print(f"Item data: {item}")
        
        # PRIMARY STORAGE: Store in DynamoDB
        if use_dynamodb:
            try:
                wardrobe_items_table.put_item(Item=prepare_for_dynamodb(item))
                print(f"DEBUG: Item {item_id} stored in DynamoDB (primary storage)")
            except Exception as e:
                print(f"DEBUG: Failed to store item in DynamoDB: {e}")
                return {"error": f"Failed to store item in DynamoDB: {e}"}
        
        # ACCELERATION: Store in memory for faster access
        in_memory_wardrobe_items[item_id] = item
        if user_id not in in_memory_users:
            in_memory_users[user_id] = {'wardrobeItems': []}
        in_memory_users[user_id]['wardrobeItems'].append(item_id)
        print(f"DEBUG: Added item to in-memory cache for acceleration")
        
        return {
            "status": "success",
            "item": item,
            "validation": {
                "warnings": validation_result['warnings'],
                "recommendations": validation_result['recommendations'],
                "category_specific": validation_result['category_specific'],
                "image_info": validation_result['image_info']
            }
        }
        
    except Exception as e:
        print(f"upload_wardrobe_item error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@mcp.tool(description="Get all wardrobe items for a user")
def get_wardrobe(user_id: str, category: Optional[str] = None, clean_cache: bool = False) -> Dict[str, Any]:
    """Retrieve all wardrobe items for a user from S3, optionally filtered by category"""
    try:
        print(f"=== get_wardrobe called ===")
        print(f"  user_id: {user_id}")
        print(f"  category: {category}")
        print(f"  clean_cache: {clean_cache}")
        
        # Clean memory cache if requested
        if clean_cache:
            print("Cleaning memory cache before retrieving wardrobe...")
            clean_result = clean_memory_cache(user_id)
            print(f"Cache cleanup result: {clean_result}")
        
        items = []
        
        # List all metadata files for this user
        prefix = f"users/{user_id}/wardrobe/"
        try:
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                # Find all metadata files
                metadata_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('_metadata.json')]
                
                print(f"Found {len(metadata_files)} metadata files for user {user_id}")
                
                # Load each metadata file
                for metadata_key in metadata_files:
                    try:
                        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=metadata_key)
                        metadata = json.loads(obj['Body'].read().decode('utf-8'))
                        
                        # Filter by category if specified
                        if not category or metadata.get('category') == category:
                            items.append(metadata)
                            
                    except Exception as e:
                        print(f"Failed to load metadata from {metadata_key}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Failed to list S3 objects: {e}")
            
        # Check in-memory storage, but prioritize S3 as source of truth
        print(f"Checking in-memory storage for user {user_id}")
        s3_item_ids = {item.get('itemId') for item in items}
        memory_items_to_remove = []
        
        for item_id, item in in_memory_wardrobe_items.items():
            if item.get('userId') == user_id:
                if item_id in s3_item_ids:
                    # Item exists in both S3 and memory - S3 is source of truth, skip memory version
                    print(f"Skipping memory item {item_id} - using S3 version")
                    continue
                elif not category or item.get('category') == category:
                    # Item only in memory (recent upload not yet in S3)
                    items.append(item)
                    print(f"Added memory-only item {item_id} to results")
        
        print(f"Found {len(items)} total items for user {user_id} after combining S3 and memory")
        
        # Generate presigned URLs for images
        for item in items:
            try:
                # Construct the S3 key from the item data
                item_id = item.get('itemId')
                s3_key = f"users/{user_id}/wardrobe/{item_id}.jpg"
                
                # Generate presigned URL
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': s3_key},
                    ExpiresIn=3600
                )
                item['presignedUrl'] = presigned_url
                print(f"Generated presigned URL for item {item_id}: {presigned_url[:50]}...")
                
            except Exception as e:
                print(f"Failed to generate presigned URL for item {item.get('itemId')}: {e}")
                # For demo/development, create a placeholder
                category = item.get('category', 'item')
                color = item.get('attributes', {}).get('color', 'gray')
                item['presignedUrl'] = f"https://via.placeholder.com/300x400/{color.replace('#', '')}00/FFFFFF?text={category.capitalize()}"
                print(f"Using placeholder URL for item {item.get('itemId')}")
        
        print(f"get_wardrobe: Found {len(items)} items for user {user_id}")
        print(f"get_wardrobe: use_dynamodb = {use_dynamodb}")
        print(f"get_wardrobe: in_memory_wardrobe_items = {in_memory_wardrobe_items}")
        for item in items:
            print(f"  Item: {item.get('itemId', 'no-id')} - {item.get('category', 'no-category')}")
        
        return {
            "status": "success",
            "items": items,
            "count": len(items)
        }
        
    except Exception as e:
        print(f"get_wardrobe error: {e}")
        return {"error": str(e)}


@mcp.tool(description="Get intelligent outfit recommendations based on comprehensive item analysis")
def recommend_outfit(
    user_id: str,
    occasion: str,
    weather: Optional[str] = None,
    season: Optional[str] = None,
    time_of_day: Optional[str] = None,
    formality_level: Optional[str] = None,
    color_preference: Optional[str] = None,
    style_preference: Optional[str] = None
) -> Dict[str, Any]:
    """Generate intelligent outfit recommendations using comprehensive wardrobe analysis"""
    try:
        # Get user's wardrobe
        wardrobe_response = get_wardrobe(user_id)
        if wardrobe_response.get('error'):
            return wardrobe_response
        
        items = wardrobe_response['items']
        if not items:
            return {
                "status": "no_items",
                "message": "User has no items in wardrobe"
            }
        
        # Create comprehensive item summaries for intelligent matching
        item_summaries = []
        for item in items:
            attrs = item.get('attributes', {})
            summary = {
                'itemId': item['itemId'],
                'category': item['category'],
                'color': attrs.get('color', 'unknown'),
                'secondaryColors': attrs.get('secondaryColors', []),
                'formalityLevel': attrs.get('formalityLevel', 'casual'),
                'styleCategory': attrs.get('styleCategory', 'classic'),
                'versatility': attrs.get('versatility', 'medium'),
                'seasonality': attrs.get('seasonality', ['all-season']),
                'occasions': attrs.get('occasions', ['casual']),
                'weatherSuitability': attrs.get('weatherSuitability', 'any'),
                'timeOfDay': attrs.get('timeOfDay', 'any'),
                'colorTemperature': attrs.get('colorTemperature', 'neutral'),
                'layeringType': attrs.get('layeringType', 'standalone'),
                'fit': attrs.get('fit', 'regular'),
                'pattern': attrs.get('pattern', 'solid'),
                'material': attrs.get('material', 'unknown'),
                'recommendedPairings': attrs.get('recommendedPairings', [])
            }
            item_summaries.append(summary)
        
        # Enhanced prompt with comprehensive analysis
        prompt = f"""You are an expert personal stylist. Based on the comprehensive wardrobe analysis below, create an intelligent outfit recommendation.

        REQUIREMENTS:
        - Occasion: {occasion}
        - Weather: {weather or 'Any'}
        - Season: {season or 'Any'}
        - Time of day: {time_of_day or 'Any'}
        - Desired formality: {formality_level or 'Any'}
        - Color preference: {color_preference or 'None'}
        - Style preference: {style_preference or 'None'}

        AVAILABLE WARDROBE ITEMS:
        {json.dumps(item_summaries, indent=2)}

        STYLING GUIDELINES:
        1. Match formality levels appropriately
        2. Consider color harmony and temperature
        3. Ensure weather and seasonal appropriateness
        4. Balance patterns and textures
        5. Create cohesive layering if needed
        6. Consider occasion suitability
        7. Maximize versatility and item synergy

        Return a JSON object with:
        {{
            "primaryRecommendation": {{
                "outfit": ["itemId1", "itemId2", "itemId3"],
                "explanation": "Detailed styling rationale",
                "stylingTips": ["tip1", "tip2"],
                "colorStory": "How colors work together",
                "alternativeOptions": ["alternative styling suggestions"]
            }},
            "alternativeRecommendations": [
                {{
                    "outfit": ["itemId4", "itemId5"],
                    "explanation": "Why this alternative works",
                    "difference": "How it differs from primary"
                }}
            ],
            "missingPieces": ["What would enhance the wardrobe"],
            "seasonalConsiderations": "Weather/season specific notes"
        }}"""
        
        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }],
                'max_tokens': 1500,
                'temperature': 0.7
            })
        )
        
        result = json.loads(response['body'].read())
        recommendation = json.loads(result['content'][0]['text'])
        
        # Enhance response with full item details
        def get_items_by_ids(item_ids):
            return [item for item in items if item['itemId'] in item_ids]
        
        primary_items = get_items_by_ids(recommendation['primaryRecommendation']['outfit'])
        
        enhanced_response = {
            "status": "success",
            "recommendation": {
                "occasion": occasion,
                "primary_outfit": {
                    "items": primary_items,
                    "explanation": recommendation['primaryRecommendation']['explanation'],
                    "styling_tips": recommendation['primaryRecommendation'].get('stylingTips', []),
                    "color_story": recommendation['primaryRecommendation'].get('colorStory', ''),
                    "alternatives": recommendation['primaryRecommendation'].get('alternativeOptions', [])
                },
                "alternative_outfits": [
                    {
                        "items": get_items_by_ids(alt['outfit']),
                        "explanation": alt['explanation'],
                        "difference": alt.get('difference', '')
                    }
                    for alt in recommendation.get('alternativeRecommendations', [])
                ],
                "missing_pieces": recommendation.get('missingPieces', []),
                "seasonal_notes": recommendation.get('seasonalConsiderations', ''),
                "criteria": {
                    "weather": weather,
                    "season": season,
                    "time_of_day": time_of_day,
                    "formality": formality_level
                }
            }
        }
        
        return enhanced_response
        
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(description="Create a virtual try-on using Nova Canvas")
def create_virtual_try_on(
    user_id: str,
    garment_item_id: str,
    model_image_base64: Optional[str] = None,
    preserve_pose: bool = True,
    preserve_face: bool = True,
    sleeve_style: str = "default",  # "SLEEVE_DOWN", "SLEEVE_UP", or "default"
    tucking_style: str = "default",  # "TUCKED", "UNTUCKED", or "default"
    outer_layer_style: str = "default"  # "OPEN", "CLOSED", or "default"
) -> Dict[str, Any]:
    """Generate a virtual try-on image using Nova Canvas"""
    global use_dynamodb
    print(f"=== create_virtual_try_on STARTED ===")
    print(f"  user_id: {user_id}")
    print(f"  garment_item_id: {garment_item_id}")
    print(f"  model_image_base64 provided: {bool(model_image_base64)}")
    print(f"  use_dynamodb: {use_dynamodb}")
    try:
        # If no model image provided, try to get user's profile photo
        if not model_image_base64:
            user_data = None
            
            if use_dynamodb:
                try:
                    # Primary: Get user from DynamoDB
                    user_response = users_table.get_item(Key={'userId': user_id})
                    if 'Item' in user_response:
                        user_data = user_response['Item']
                        print(f"DEBUG: Found user in DynamoDB: {user_id}")
                    else:
                        print(f"DEBUG: User {user_id} not found in DynamoDB")
                except Exception as e:
                    print(f"DEBUG: DynamoDB user lookup failed: {e}")
            
            # Fallback: Check in-memory storage
            if not user_data and user_id in in_memory_users:
                user_data = in_memory_users[user_id]
                print(f"DEBUG: Found user in memory: {user_id}")
            
            if not user_data:
                return {"error": "User not found"}
            
            # Get profile photo from S3 using profilePhotoUrl
            if 'profilePhotoUrl' in user_data and user_data['profilePhotoUrl'].startswith('s3://'):
                profile_s3_key = user_data['profilePhotoUrl'].replace(f's3://{S3_BUCKET}/', '')
                print(f"DEBUG: Using profilePhotoUrl from user data: {profile_s3_key}")
            else:
                # Fallback to constructed path
                profile_s3_key = f"users/{user_id}/profile-photo.jpg"
                print(f"DEBUG: Using constructed profile photo path: {profile_s3_key}")
            
            try:
                profile_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=profile_s3_key)
                model_image_data = profile_obj['Body'].read()
                print(f"DEBUG: Loaded user profile photo from S3: {profile_s3_key}")
            except Exception as e:
                print(f"DEBUG: Failed to load user profile photo: {e}")
                return {"error": "No profile photo found. Please upload a photo of yourself first."}
            
            # Process image to ensure proper format
            model_image = Image.open(io.BytesIO(model_image_data))
            model_image_base64 = convert_image_for_canvas(model_image)
        
        # Get garment item from DynamoDB (primary) or fallback to memory/S3
        garment_item = None
        
        # Debug: Show current in-memory items
        print(f"DEBUG: Current in-memory items: {len(in_memory_wardrobe_items)}")
        for item_id, item in in_memory_wardrobe_items.items():
            print(f"  Memory item: {item_id} (user: {item.get('userId')})")
        
        if use_dynamodb:
            try:
                # Primary: Get from DynamoDB
                garment_response = wardrobe_items_table.get_item(
                    Key={'itemId': garment_item_id}
                )
                
                if 'Item' in garment_response:
                    item = garment_response['Item']
                    # SECURITY: Verify the item belongs to the requesting user
                    if item.get('userId') == user_id:
                        garment_item = item
                        print(f"DEBUG: Found garment item in DynamoDB: {garment_item_id} (user verified)")
                    else:
                        print(f"DEBUG: Garment item {garment_item_id} belongs to different user, access denied")
                else:
                    print(f"DEBUG: Garment item {garment_item_id} not found in DynamoDB")
            except Exception as e:
                print(f"DEBUG: DynamoDB lookup failed: {e}")
        
        # Fallback: Check in-memory storage if DynamoDB failed or not available
        if not garment_item:
            print(f"DEBUG: Falling back to in-memory storage for {garment_item_id}")
            for item in in_memory_wardrobe_items.values():
                if item.get('itemId') == garment_item_id and item.get('userId') == user_id:
                    garment_item = item
                    print(f"DEBUG: Found garment item in memory: {garment_item_id} (user verified)")
                    break
        
        # Final fallback: Try S3 metadata
        if not garment_item:
            try:
                metadata_key = f"users/{user_id}/wardrobe/{garment_item_id}.json"
                print(f"DEBUG: Final fallback - trying S3: {metadata_key}")
                metadata_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=metadata_key)
                garment_item = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                print(f"DEBUG: Loaded garment item from S3 metadata: {garment_item_id}")
            except Exception as e:
                print(f"DEBUG: S3 fallback failed: {e}")
        
        if not garment_item:
            print(f"DEBUG: Garment item {garment_item_id} not found in any storage")
            return {"error": f"Garment item {garment_item_id} not found"}
        
        # Get garment image from S3 using imageUrl from metadata
        if 'imageUrl' in garment_item and garment_item['imageUrl'].startswith('s3://'):
            s3_key = garment_item['imageUrl'].replace(f's3://{S3_BUCKET}/', '')
            print(f"DEBUG: Using imageUrl from metadata: {s3_key}")
        else:
            # Fallback to constructed path
            s3_key = f"users/{user_id}/wardrobe/{garment_item_id}.jpg"
            print(f"DEBUG: Using constructed S3 path: {s3_key}")
            
        garment_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        garment_image_data = garment_obj['Body'].read()
        
        # Process garment image to ensure proper format
        garment_image = Image.open(io.BytesIO(garment_image_data))
        garment_image_base64 = convert_image_for_canvas(garment_image)
        
        # Determine garment type from category
        garment_type = garment_item.get('category', 'top')
        
        # Map garment type to correct format
        garment_class_mapping = {
            "TOP": "UPPER_BODY",
            "SHIRT": "UPPER_BODY", 
            "BLOUSE": "UPPER_BODY",
            "SWEATER": "UPPER_BODY",
            "JACKET": "UPPER_BODY",
            "COAT": "UPPER_BODY",
            "BOTTOM": "LOWER_BODY",
            "PANTS": "LOWER_BODY",
            "JEANS": "LOWER_BODY",
            "SKIRT": "LOWER_BODY",
            "SHORTS": "LOWER_BODY",
            "DRESS": "FULL_BODY",
            "SHOES": "FOOTWEAR",
            "SNEAKERS": "FOOTWEAR",
            "BOOTS": "FOOTWEAR",
            "HEELS": "FOOTWEAR"
        }
        
        garment_class = garment_class_mapping.get(garment_type.upper(), "UPPER_BODY")
        
        # Build style configuration with custom options
        style_config = {"mergeStyle": "BALANCED"}
        
        # Add style options based on garment type and user preferences
        if garment_class == "UPPER_BODY" and sleeve_style != "default":
            if sleeve_style in ["SLEEVE_DOWN", "SLEEVE_UP"]:
                style_config["longSleeveStyle"] = sleeve_style
        
        if garment_class == "UPPER_BODY" and tucking_style != "default":
            if tucking_style in ["TUCKED", "UNTUCKED"]:
                style_config["tuckingStyle"] = tucking_style
        
        if garment_class == "UPPER_BODY" and outer_layer_style != "default":
            if outer_layer_style in ["OPEN", "CLOSED"]:
                style_config["outerLayerStyle"] = outer_layer_style
        
        # Debug image data before Nova Canvas call
        print(f"DEBUG: Before Nova Canvas call:")
        print(f"  model_image_base64 length: {len(model_image_base64) if model_image_base64 else 'None'}")
        print(f"  garment_image_base64 length: {len(garment_image_base64) if garment_image_base64 else 'None'}")
        print(f"  model_image_base64 type: {type(model_image_base64)}")
        print(f"  garment_image_base64 type: {type(garment_image_base64)}")
        
        # Prepare Nova Canvas request with minimal required parameters
        nova_request = {
            "taskType": "VIRTUAL_TRY_ON",
            "virtualTryOnParams": {
                "sourceImage": model_image_base64,
                "referenceImage": garment_image_base64,
                "maskType": "GARMENT",
                "garmentBasedMask": {
                    "garmentClass": garment_class
                }
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "standard",
                "height": 1024,
                "width": 1024
            }
        }
        
        # Call Nova Canvas API
        response = bedrock_runtime.invoke_model(
            modelId='amazon.nova-canvas-v1:0',
            body=json.dumps(nova_request)
        )
        
        result = json.loads(response['body'].read())
        
        if 'images' in result and result['images']:
            # Save try-on result
            outfit_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            # Upload try-on image to S3
            tryon_image_data = base64.b64decode(result['images'][0])
            tryon_s3_key = f"users/{user_id}/tryons/{outfit_id}.jpg"
            
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=tryon_s3_key,
                Body=tryon_image_data,
                ContentType='image/jpeg'
            )
            
            # Save outfit record
            outfit = {
                'outfitId': outfit_id,
                'userId': user_id,
                'items': [garment_item_id],
                'occasion': 'virtual_try_on',
                'tryOnImageUrl': f"s3://{S3_BUCKET}/{tryon_s3_key}",
                'createdAt': timestamp,
                'metadata': {
                    'garmentType': garment_type,
                    'preserveSettings': {
                        'pose': preserve_pose,
                        'face': preserve_face
                    }
                }
            }
            
            # Store outfit in DynamoDB (primary) or fallback to memory/S3
            if use_dynamodb:
                try:
                    outfits_table.put_item(Item=outfit)
                    print(f"DEBUG: Saved outfit to DynamoDB: {outfit_id}")
                except Exception as e:
                    print(f"DEBUG: DynamoDB outfit save failed: {e}")
                    use_dynamodb = False  # Fallback for this operation
            
            if not use_dynamodb:
                # Fallback: Store in S3 and memory
                outfit_metadata_key = f"users/{user_id}/outfits/{outfit_id}.json"
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=outfit_metadata_key,
                    Body=json.dumps(outfit),
                    ContentType='application/json'
                )
                print(f"DEBUG: Saved outfit metadata to S3 fallback: {outfit_metadata_key}")
                
                # Also store in memory for immediate access
                if not hasattr(create_virtual_try_on, 'in_memory_outfits'):
                    create_virtual_try_on.in_memory_outfits = []
                create_virtual_try_on.in_memory_outfits.append(outfit)
            
            # Generate presigned URL
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET, 'Key': tryon_s3_key},
                ExpiresIn=3600
            )
            
            return {
                "status": "success",
                "outfit": outfit,
                "tryOnImageUrl": presigned_url
            }
        else:
            return {
                "error": "Nova Canvas did not return any images"
            }
            
    except Exception as e:
        print(f"=== create_virtual_try_on ERROR ===")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")
        import traceback
        print(f"  Traceback: {traceback.format_exc()}")
        return {"error": f"Virtual try-on failed: {str(e)}"}


@mcp.tool(description="Save a complete outfit combination")
def save_outfit(
    user_id: str,
    item_ids: List[str],
    occasion: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Save a combination of wardrobe items as an outfit"""
    try:
        outfit_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        outfit = {
            'outfitId': outfit_id,
            'userId': user_id,
            'items': item_ids,
            'occasion': occasion,
            'createdAt': timestamp,
            'notes': notes
        }
        
        # Store outfit in DynamoDB (primary) or fallback
        if use_dynamodb:
            try:
                outfits_table.put_item(Item=outfit)
                print(f"DEBUG: Saved outfit to DynamoDB: {outfit_id}")
            except Exception as e:
                print(f"DEBUG: DynamoDB outfit save failed: {e}")
                use_dynamodb = False  # Fallback for this operation
        
        if not use_dynamodb:
            # Fallback: Store in S3 and memory
            outfit_metadata_key = f"users/{user_id}/outfits/{outfit_id}.json"
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=outfit_metadata_key,
                Body=json.dumps(outfit),
                ContentType='application/json'
            )
            print(f"DEBUG: Saved outfit to S3 fallback: {outfit_metadata_key}")
            
            # Also store in memory for immediate access
            if not hasattr(create_virtual_try_on, 'in_memory_outfits'):
                create_virtual_try_on.in_memory_outfits = []
            create_virtual_try_on.in_memory_outfits.append(outfit)
        
        return {
            "status": "success",
            "outfit": outfit
        }
        
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(description="Get saved outfits for a user")
def get_outfits(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """Retrieve saved outfits for a user from DynamoDB or fallback"""
    try:
        outfits = []
        
        # Primary: Try to get from DynamoDB
        if use_dynamodb:
            try:
                response = outfits_table.query(
                    IndexName='userId-createdAt-index',
                    KeyConditionExpression='userId = :uid',
                    ExpressionAttributeValues={':uid': user_id},
                    ScanIndexForward=False,
                    Limit=limit
                )
                outfits = response['Items']
                print(f"DEBUG: Found {len(outfits)} outfits in DynamoDB for user {user_id}")
            except Exception as e:
                print(f"DEBUG: DynamoDB outfit query failed: {e}")
        
        # Fallback: Check in-memory and S3 storage
        if not outfits:
            print(f"DEBUG: Falling back to memory/S3 for outfits")
            
            # Check in-memory storage
            if hasattr(create_virtual_try_on, 'in_memory_outfits'):
                memory_outfits = [o for o in create_virtual_try_on.in_memory_outfits if o.get('userId') == user_id]
                outfits.extend(memory_outfits)
                print(f"DEBUG: Found {len(memory_outfits)} outfits in memory for user {user_id}")
            
            # Try to load outfits from S3
            try:
                outfit_prefix = f"users/{user_id}/outfits/"
                response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=outfit_prefix)
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        if obj['Key'].endswith('.json'):
                            try:
                                outfit_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=obj['Key'])
                                outfit = json.loads(outfit_obj['Body'].read().decode('utf-8'))
                                
                                # Check if already in memory (avoid duplicates)
                                if not any(o.get('outfitId') == outfit.get('outfitId') for o in outfits):
                                    outfits.append(outfit)
                            except Exception as e:
                                print(f"DEBUG: Failed to load outfit from {obj['Key']}: {e}")
                                
                print(f"DEBUG: Total outfits found: {len(outfits)}")
            except Exception as e:
                print(f"DEBUG: Failed to list outfits from S3: {e}")
            
            # Sort by creation date (newest first) and limit
            outfits.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
            outfits = outfits[:limit]
        
        # Add presigned URLs for try-on images
        for outfit in outfits:
            if 'tryOnImageUrl' in outfit and outfit['tryOnImageUrl'].startswith('s3://'):
                s3_key = outfit['tryOnImageUrl'].replace(f's3://{S3_BUCKET}/', '')
                try:
                    outfit['tryOnPresignedUrl'] = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': S3_BUCKET, 'Key': s3_key},
                        ExpiresIn=3600
                    )
                except Exception as e:
                    print(f"DEBUG: Failed to generate presigned URL for outfit image: {e}")
        
        return {
            "status": "success",
            "outfits": outfits,
            "count": len(outfits)
        }
        
    except Exception as e:
        return {"error": str(e)}


def validate_clothing_item_image(image_base64: str, category: str = "unknown") -> Dict[str, Any]:
    """Validate clothing item image for Nova Canvas virtual try-on compatibility"""
    try:
        # Decode and load image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        validation_errors = []
        validation_warnings = []
        
        # 1. Format validation
        if image.format not in ['JPEG', 'JPG', 'PNG']:
            validation_errors.append(f"Unsupported format: {image.format}. Use JPEG or PNG")
        
        # 2. Size validation (clothing items need good resolution for virtual try-on)
        width, height = image.size
        if width < 256 or height < 256:
            validation_errors.append(f"Image too small: {width}x{height}. Minimum 256x256 required for clothing recognition")
        
        if width > 4096 or height > 4096:
            validation_warnings.append(f"Large image: {width}x{height}. Will be resized to 1024x1024")
        
        # 3. Aspect ratio validation (clothing items work best square or portrait)
        aspect_ratio = width / height
        if aspect_ratio < 0.3 or aspect_ratio > 3.0:
            validation_warnings.append(f"Extreme aspect ratio: {aspect_ratio:.2f}. Square or portrait images work best for clothing")
        
        # 4. File size validation
        file_size_mb = len(image_data) / (1024 * 1024)
        if file_size_mb > 20:
            validation_errors.append(f"File too large: {file_size_mb:.1f}MB. Maximum 20MB allowed")
        
        # 5. Image quality checks
        if image.mode not in ['RGB', 'RGBA']:
            validation_warnings.append(f"Color mode: {image.mode}. Will be converted to RGB")
        
        # 6. Content validation for clothing items
        image_rgb = image.convert('RGB')
        pixels = list(image_rgb.getdata())
        
        # Sample pixels to check for content
        sample_size = min(1000, len(pixels))
        sample_pixels = pixels[::len(pixels)//sample_size] if sample_size < len(pixels) else pixels
        
        # Check for mostly white/blank images (common for clothing on white background)
        white_pixels = sum(1 for r, g, b in sample_pixels if r > 240 and g > 240 and b > 240)
        white_ratio = white_pixels / len(sample_pixels)
        
        # For clothing, some white background is OK, but too much suggests no garment
        if white_ratio > 0.95:
            validation_warnings.append("Image appears almost entirely white. Make sure the clothing item is clearly visible")
        elif white_ratio > 0.85:
            validation_warnings.append("High white background ratio. Consider cropping closer to the garment")
        
        # Check for very dark images
        dark_pixels = sum(1 for r, g, b in sample_pixels if r < 20 and g < 20 and b < 20)
        dark_ratio = dark_pixels / len(sample_pixels)
        
        if dark_ratio > 0.8:
            validation_warnings.append("Image appears very dark. Better lighting recommended for clothing recognition")
        
        # 7. Category-specific recommendations
        category_recommendations = {
            "top": [
                "Show the full garment laid flat or on a hanger",
                "Ensure sleeves and neckline are clearly visible",
                "White or neutral background works best",
                "Avoid heavy shadows or wrinkles"
            ],
            "bottom": [
                "Show the full length from waist to hem",
                "Lay flat or hang to show the proper shape",
                "Include waistband and any details clearly",
                "Ensure the fit/cut is visible"
            ],
            "dress": [
                "Show the complete dress from neckline to hem",
                "Display on a hanger or dress form if possible",
                "Ensure the silhouette and details are clear",
                "Good lighting to show fabric texture"
            ],
            "shoes": [
                "Show from multiple angles if possible",
                "Include both side view and top view",
                "Clean background to highlight shoe details",
                "Ensure sole and upper are clearly visible"
            ],
            "outerwear": [
                "Show both closed and open positions if applicable",
                "Include details like buttons, zippers, pockets",
                "Display the full length and cut",
                "Show collar and sleeve details clearly"
            ]
        }
        
        specific_recommendations = category_recommendations.get(category, [
            "Ensure the item is clearly visible and well-lit",
            "Use a clean, neutral background",
            "Show the full garment without cropping",
            "Minimize shadows and wrinkles"
        ])
        
        # 8. General clothing photography recommendations
        general_recommendations = [
            "Use natural lighting or bright, even artificial light",
            "White or light neutral background for best results",
            "Lay garment flat or use a hanger/dress form",
            "Remove wrinkles and ensure proper shape",
            "Fill the frame with the garment (minimal empty space)",
            "Take photo straight-on (avoid angled shots)"
        ]
        
        all_recommendations = specific_recommendations + general_recommendations
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "recommendations": all_recommendations,
            "category_specific": specific_recommendations,
            "image_info": {
                "format": image.format,
                "size": f"{width}x{height}",
                "file_size_mb": round(file_size_mb, 2),
                "aspect_ratio": round(aspect_ratio, 2),
                "color_mode": image.mode,
                "white_background_ratio": round(white_ratio, 2),
                "category": category
            }
        }
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to process clothing image: {str(e)}"],
            "warnings": [],
            "recommendations": ["Please upload a valid JPEG or PNG image of the clothing item"],
            "category_specific": [],
            "image_info": {}
        }

def validate_profile_photo(image_base64: str) -> Dict[str, Any]:
    """Validate profile photo for Nova Canvas virtual try-on compatibility"""
    try:
        # Decode and load image
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        validation_errors = []
        validation_warnings = []
        
        # 1. Format validation
        if image.format not in ['JPEG', 'JPG', 'PNG']:
            validation_errors.append(f"Unsupported format: {image.format}. Use JPEG or PNG")
        
        # 2. Size validation (Nova Canvas works best with reasonable sizes)
        width, height = image.size
        if width < 256 or height < 256:
            validation_errors.append(f"Image too small: {width}x{height}. Minimum 256x256 required")
        
        if width > 4096 or height > 4096:
            validation_warnings.append(f"Large image: {width}x{height}. Will be resized to 1024x1024")
        
        # 3. Aspect ratio validation (person should be visible)
        aspect_ratio = width / height
        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
            validation_warnings.append(f"Unusual aspect ratio: {aspect_ratio:.2f}. Portrait photos work best")
        
        # 4. File size validation (approximate)
        file_size_mb = len(image_data) / (1024 * 1024)
        if file_size_mb > 20:
            validation_errors.append(f"File too large: {file_size_mb:.1f}MB. Maximum 20MB allowed")
        
        # 5. Image quality checks
        if image.mode not in ['RGB', 'RGBA']:
            validation_warnings.append(f"Color mode: {image.mode}. Will be converted to RGB")
        
        # 6. Content validation using basic image analysis
        # Check if image is mostly blank/white (likely not a person)
        image_rgb = image.convert('RGB')
        pixels = list(image_rgb.getdata())
        
        # Sample pixels to check for content
        sample_size = min(1000, len(pixels))
        sample_pixels = pixels[::len(pixels)//sample_size] if sample_size < len(pixels) else pixels
        
        # Check for mostly white/blank images
        white_pixels = sum(1 for r, g, b in sample_pixels if r > 240 and g > 240 and b > 240)
        white_ratio = white_pixels / len(sample_pixels)
        
        if white_ratio > 0.8:
            validation_warnings.append("Image appears mostly blank. Make sure it shows a person clearly")
        
        # Check for very dark images
        dark_pixels = sum(1 for r, g, b in sample_pixels if r < 30 and g < 30 and b < 30)
        dark_ratio = dark_pixels / len(sample_pixels)
        
        if dark_ratio > 0.7:
            validation_warnings.append("Image appears very dark. Better lighting recommended")
        
        # 7. Additional recommendations for virtual try-on
        recommendations = [
            "Use a photo showing your full upper body for best virtual try-on results",
            "Ensure good lighting with the person clearly visible",
            "Avoid busy backgrounds - plain backgrounds work best",
            "Face the camera directly for optimal results",
            "Wear fitted clothing to help with accurate virtual try-on"
        ]
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "recommendations": recommendations,
            "image_info": {
                "format": image.format,
                "size": f"{width}x{height}",
                "file_size_mb": round(file_size_mb, 2),
                "aspect_ratio": round(aspect_ratio, 2),
                "color_mode": image.mode
            }
        }
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to process image: {str(e)}"],
            "warnings": [],
            "recommendations": ["Please upload a valid JPEG or PNG image"],
            "image_info": {}
        }

def convert_image_for_canvas(image: Image.Image, target_size: int = 1024) -> str:
    """Convert and resize image for Nova Canvas requirements"""
    # Convert RGBA to RGB if necessary
    if image.mode == 'RGBA':
        # Create a white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Nova Canvas works best with square images (1024x1024)
    # Resize while maintaining aspect ratio, then pad to square
    original_width, original_height = image.size
    
    # Calculate scaling to fit within target size
    scale = min(target_size / original_width, target_size / original_height)
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    
    # Resize the image
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Create a white square background and center the image
    square_image = Image.new('RGB', (target_size, target_size), (255, 255, 255))
    paste_x = (target_size - new_width) // 2
    paste_y = (target_size - new_height) // 2
    square_image.paste(image, (paste_x, paste_y))
    
    # Convert to base64
    buffer = io.BytesIO()
    square_image.save(buffer, format='JPEG', quality=95)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def analyze_clothing_image(image_base64: str) -> Dict[str, Any]:
    """Use Claude Vision to analyze clothing attributes"""
    try:
        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': 'image/jpeg',
                                'data': image_base64
                            }
                        },
                        {
                            'type': 'text',
                            'text': """Analyze this clothing item comprehensively and return a detailed JSON object with:

                            BASIC ATTRIBUTES:
                            - color: primary color of the item
                            - secondaryColors: array of additional colors if present
                            - pattern: solid/striped/floral/geometric/abstract/plaid/polka-dot/etc
                            - material: cotton/denim/silk/wool/polyester/leather/etc (if visible)
                            - texture: smooth/rough/ribbed/knit/woven/etc
                            
                            STYLE & FORMALITY:
                            - formalityLevel: very-casual/smart-casual/business-casual/formal/black-tie
                            - styleCategory: classic/trendy/vintage/bohemian/minimalist/edgy/romantic
                            - versatility: high/medium/low (how well it pairs with other items)
                            
                            GARMENT SPECIFICS:
                            - fit: slim/regular/loose/oversized/fitted
                            - weight: lightweight/medium/heavy
                            - transparency: opaque/semi-transparent/sheer
                            - finish: matte/glossy/metallic/textured
                            
                            FUNCTIONAL DETAILS:
                            - seasonality: spring/summer/fall/winter/all-season (can be multiple)
                            - layeringType: base-layer/mid-layer/outer-layer/standalone
                            - weatherSuitability: sunny/rainy/cold/windy/any
                            - careLevel: low-maintenance/medium/high-maintenance
                            
                            OCCASION SUITABILITY:
                            - occasions: array from [work, casual, date, party, formal-event, travel, gym, beach, outdoor]
                            - timeOfDay: morning/afternoon/evening/any
                            
                            GARMENT-SPECIFIC (only include if applicable):
                            - sleeveLength: sleeveless/short/three-quarter/long (for tops)
                            - neckline: crew/v-neck/scoop/turtleneck/off-shoulder/etc (for tops)
                            - length: mini/knee-length/midi/maxi/ankle (for dresses/skirts)
                            - rise: low/mid/high (for pants)
                            - closure: button/zip/pullover/wrap/etc
                            - pockets: yes/no
                            - tuckingCompatibility: excellent/good/poor/not-applicable
                            
                            STYLING NOTES:
                            - colorTemperature: warm/cool/neutral
                            - standoutFeatures: array of notable design elements
                            - recommendedPairings: suggest what types of items would pair well
                            
                            Be precise and comprehensive. Use arrays for multiple values where applicable."""
                        }
                    ]
                }],
                'max_tokens': 800,
                'temperature': 0.3
            })
        )
        
        result = json.loads(response['body'].read())
        analysis = json.loads(result['content'][0]['text'])
        return analysis
        
    except Exception as e:
        return {
            'color': 'unknown',
            'secondaryColors': [],
            'pattern': 'solid',
            'material': 'unknown',
            'texture': 'unknown',
            'formalityLevel': 'casual',
            'styleCategory': 'classic',
            'versatility': 'medium',
            'fit': 'regular',
            'weight': 'medium',
            'transparency': 'opaque',
            'finish': 'matte',
            'seasonality': ['all-season'],
            'layeringType': 'standalone',
            'weatherSuitability': 'any',
            'careLevel': 'medium',
            'occasions': ['casual'],
            'timeOfDay': 'any',
            'colorTemperature': 'neutral',
            'standoutFeatures': [],
            'recommendedPairings': ['basic items']
        }


@mcp.tool(description="Create a virtual try-on with multiple garments using Nova Canvas")
def create_multi_item_virtual_try_on(
    user_id: str,
    garment_item_ids: List[str],
    model_image_base64: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a virtual try-on image with multiple garments using Nova Canvas"""
    global use_dynamodb
    print(f"=== create_multi_item_virtual_try_on STARTED ===")
    print(f"  user_id: {user_id}")
    print(f"  garment_item_ids: {garment_item_ids}")
    print(f"  model_image_base64 provided: {bool(model_image_base64)}")
    print(f"  use_dynamodb: {use_dynamodb}")
    try:
        # CRITICAL: Always clean cache before multi-item operations to prevent phantom items
        print("DEBUG: Cleaning cache before multi-item try-on to prevent phantom items")
        clean_result = clean_memory_cache(user_id)
        print(f"DEBUG: Cache clean result: {clean_result}")
        # If no model image provided, try to get user's profile photo
        if not model_image_base64:
            user_data = None
            
            if use_dynamodb:
                try:
                    user_response = users_table.get_item(Key={'userId': user_id})
                    if 'Item' in user_response:
                        user_data = user_response['Item']
                        print(f"DEBUG: Found user in DynamoDB for multi-item: {user_id}")
                except Exception as e:
                    print(f"DEBUG: DynamoDB user lookup failed for multi-item: {e}")
            
            if not user_data and user_id in in_memory_users:
                user_data = in_memory_users[user_id]
                print(f"DEBUG: Found user in memory for multi-item: {user_id}")
            
            if not user_data:
                return {"error": "User not found"}
            
            if 'profilePhotoUrl' in user_data and user_data['profilePhotoUrl'].startswith('s3://'):
                profile_s3_key = user_data['profilePhotoUrl'].replace(f's3://{S3_BUCKET}/', '')
            else:
                profile_s3_key = f"users/{user_id}/profile-photo.jpg"
            
            try:
                profile_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=profile_s3_key)
                model_image_data = profile_obj['Body'].read()
                print(f"DEBUG: Loaded user profile photo for multi-item: {profile_s3_key}")
            except Exception as e:
                print(f"DEBUG: Failed to load user profile photo for multi-item: {e}")
                return {"error": "No profile photo found. Please upload a photo of yourself first."}
            
            # Process image to ensure proper format
            model_image = Image.open(io.BytesIO(model_image_data))
            model_image_base64 = convert_image_for_canvas(model_image)
        
        # Get all garment items and combine them into a single reference image
        garment_images = []
        combined_categories = []
        
        for item_id in garment_item_ids:
            garment_item = None
            
            # ALWAYS try DynamoDB first (source of truth) to prevent phantom items
            if use_dynamodb:
                try:
                    garment_response = wardrobe_items_table.get_item(Key={'itemId': item_id})
                    if 'Item' in garment_response:
                        item = garment_response['Item']
                        # SECURITY: Verify the item belongs to the requesting user
                        if item.get('userId') == user_id:
                            garment_item = item
                            print(f"DEBUG: Found FRESH item in DynamoDB for multi-item: {item_id} (user verified)")
                        else:
                            print(f"DEBUG: Item {item_id} belongs to different user, access denied")
                            continue
                    else:
                        print(f"DEBUG: Item {item_id} not found in DynamoDB - may be phantom item")
                except Exception as e:
                    print(f"DEBUG: DynamoDB lookup failed for multi-item: {e}")
            
            # Only use memory if DynamoDB failed AND item was recently added
            if not garment_item:
                for item in in_memory_wardrobe_items.values():
                    if item.get('itemId') == item_id and item.get('userId') == user_id:
                        # Verify this is a recently added item (less than 5 minutes old)
                        item_created = item.get('uploadedAt', '')
                        if item_created:
                            try:
                                from datetime import datetime as dt, timedelta
                                created_time = dt.fromisoformat(item_created.replace('Z', '+00:00'))
                                now = dt.now(created_time.tzinfo)
                                if (now - created_time) < timedelta(minutes=5):
                                    garment_item = item
                                    print(f"DEBUG: Using recent memory item for multi-item: {item_id} (age: {now - created_time})")
                                    break
                                else:
                                    print(f"DEBUG: Memory item {item_id} is too old ({now - created_time}), likely phantom")
                            except Exception as date_error:
                                print(f"DEBUG: Could not parse date for {item_id}: {date_error}")
                        break
            
            # Skip S3 fallback for multi-item to prevent phantom items
            if not garment_item:
                print(f"DEBUG: Skipping phantom item {item_id} - not found in fresh DynamoDB query")
                print(f"DEBUG: Available memory items: {list(in_memory_wardrobe_items.keys())}")
                continue
                
            item_category = garment_item.get('category', 'top')
            combined_categories.append(item_category)
            print(f"DEBUG: Processing item {item_id} - Category: {item_category}, ItemId: {garment_item.get('itemId', 'unknown')}")
            
            # Get garment image from S3 using imageUrl from metadata
            if 'imageUrl' in garment_item and garment_item['imageUrl'].startswith('s3://'):
                s3_key = garment_item['imageUrl'].replace(f's3://{S3_BUCKET}/', '')
            else:
                s3_key = f"users/{user_id}/wardrobe/{item_id}.jpg"
            
            try:
                garment_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
                garment_image_data = garment_obj['Body'].read()
                
                # Process garment image
                garment_image = Image.open(io.BytesIO(garment_image_data))
                garment_images.append(garment_image)
                print(f"DEBUG: Loaded garment image for multi-item: {s3_key}")
            except Exception as e:
                print(f"DEBUG: Failed to load garment image for multi-item {item_id}: {e}")
                continue
        
        if not garment_images:
            return {"error": "No valid garment items found"}
        
        # Debug: Log exactly what images we're combining
        print(f"DEBUG: About to combine {len(garment_images)} garment images:")
        for i, img in enumerate(garment_images):
            print(f"  Image {i+1}: Size={img.size}, Mode={img.mode}")
            # Save debug image to check what we're combining
            try:
                debug_key = f"debug/multi-item-{user_id}-image-{i+1}-{uuid.uuid4().hex[:8]}.jpg"
                debug_buffer = io.BytesIO()
                img.save(debug_buffer, format='JPEG', quality=95)
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=debug_key,
                    Body=debug_buffer.getvalue(),
                    ContentType='image/jpeg'
                )
                print(f"  Saved debug image: s3://{S3_BUCKET}/{debug_key}")
            except Exception as debug_error:
                print(f"  Failed to save debug image: {debug_error}")
        
        # Combine multiple garment images into one
        reference_image = combine_garment_images(garment_images)
        
        # Save the combined reference image for debugging
        try:
            combined_debug_key = f"debug/multi-item-{user_id}-combined-{uuid.uuid4().hex[:8]}.jpg"
            combined_buffer = io.BytesIO()
            reference_image.save(combined_buffer, format='JPEG', quality=95)
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=combined_debug_key,
                Body=combined_buffer.getvalue(),
                ContentType='image/jpeg'
            )
            print(f"DEBUG: Saved combined reference image: s3://{S3_BUCKET}/{combined_debug_key}")
        except Exception as debug_error:
            print(f"DEBUG: Failed to save combined debug image: {debug_error}")
        
        reference_image_base64 = convert_image_for_canvas(reference_image)
        
        # Use FULL_BODY for multi-item try-ons to handle complete outfits
        nova_request = {
            "taskType": "VIRTUAL_TRY_ON",
            "virtualTryOnParams": {
                "sourceImage": model_image_base64,
                "referenceImage": reference_image_base64,
                "maskType": "GARMENT",
                "garmentBasedMask": {
                    "garmentClass": "FULL_BODY"
                }
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "standard",
                "height": 1024,
                "width": 1024
            }
        }
        
        # Debug: Log request details (without actual image data for brevity)
        print(f"DEBUG: Nova Canvas request prepared:")
        print(f"  Categories being processed: {combined_categories}")
        print(f"  Item IDs: {garment_item_ids}")
        print(f"  Source image length: {len(model_image_base64)}")
        print(f"  Reference image length: {len(reference_image_base64)}")
        print(f"  Garment class: FULL_BODY")
        print(f"  Task type: VIRTUAL_TRY_ON")
        
        # Call Nova Canvas API
        response = bedrock_runtime.invoke_model(
            modelId='amazon.nova-canvas-v1:0',
            body=json.dumps(nova_request)
        )
        
        result = json.loads(response['body'].read())
        
        if 'images' in result and result['images']:
            # Save try-on result as an outfit
            outfit_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            # Upload try-on image to S3
            tryon_image_data = base64.b64decode(result['images'][0])
            tryon_s3_key = f"users/{user_id}/tryons/{outfit_id}.jpg"
            
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=tryon_s3_key,
                Body=tryon_image_data,
                ContentType='image/jpeg'
            )
            
            # Save outfit record with multiple items
            outfit = {
                'outfitId': outfit_id,
                'userId': user_id,
                'items': garment_item_ids,
                'occasion': 'multi_item_try_on',
                'tryOnImageUrl': f"s3://{S3_BUCKET}/{tryon_s3_key}",
                'createdAt': timestamp,
                'metadata': {
                    'itemCount': len(garment_item_ids),
                    'categories': combined_categories
                }
            }
            
            # Store outfit in DynamoDB (primary) or fallback
            if use_dynamodb:
                try:
                    outfits_table.put_item(Item=outfit)
                    print(f"DEBUG: Saved multi-item outfit to DynamoDB: {outfit_id}")
                except Exception as e:
                    print(f"DEBUG: DynamoDB multi-item outfit save failed: {e}")
                    use_dynamodb = False  # Fallback for this operation
            
            if not use_dynamodb:
                # Fallback: Store in S3 and memory
                outfit_metadata_key = f"users/{user_id}/outfits/{outfit_id}.json"
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=outfit_metadata_key,
                    Body=json.dumps(outfit),
                    ContentType='application/json'
                )
                print(f"DEBUG: Saved multi-item outfit to S3 fallback: {outfit_metadata_key}")
                
                if not hasattr(create_virtual_try_on, 'in_memory_outfits'):
                    create_virtual_try_on.in_memory_outfits = []
                create_virtual_try_on.in_memory_outfits.append(outfit)
            
            # Generate presigned URL
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET, 'Key': tryon_s3_key},
                ExpiresIn=3600
            )
            
            result = {
                "status": "success",
                "outfit": outfit,
                "tryOnImageUrl": presigned_url,
                "itemCount": len(garment_item_ids)
            }
            print(f"=== create_multi_item_virtual_try_on SUCCESS ===")
            print(f"  outfit_id: {outfit_id}")
            print(f"  presigned_url: {presigned_url}")
            return result
        else:
            return {
                "error": "Nova Canvas did not return any images"
            }
            
    except Exception as e:
        print(f"=== create_multi_item_virtual_try_on ERROR ===")
        print(f"  error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def combine_garment_images(images: List[Image.Image], target_size: int = 1024) -> Image.Image:
    """Combine multiple garment images into a single reference image"""
    if len(images) == 1:
        return images[0]
    
    # Create a canvas to arrange multiple items
    combined = Image.new('RGB', (target_size, target_size), (255, 255, 255))
    
    if len(images) == 2:
        # Side by side for 2 items
        for i, img in enumerate(images):
            # Resize to fit half width
            img_resized = img.copy()
            img_resized.thumbnail((target_size // 2 - 20, target_size - 40), Image.Resampling.LANCZOS)
            x = (target_size // 4) + i * (target_size // 2)
            y = (target_size - img_resized.height) // 2
            combined.paste(img_resized, (x - img_resized.width // 2, y))
    else:
        # Grid layout for 3+ items
        cols = 2 if len(images) <= 4 else 3
        rows = (len(images) + cols - 1) // cols
        
        cell_width = target_size // cols
        cell_height = target_size // rows
        
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            
            # Resize to fit cell with padding
            img_resized = img.copy()
            img_resized.thumbnail((cell_width - 20, cell_height - 20), Image.Resampling.LANCZOS)
            
            x = col * cell_width + (cell_width - img_resized.width) // 2
            y = row * cell_height + (cell_height - img_resized.height) // 2
            combined.paste(img_resized, (x, y))
    
    return combined


@mcp.tool(description="Clear stale in-memory cache by syncing with S3/DynamoDB")
def clean_memory_cache(user_id: str) -> Dict[str, Any]:
    """Clean up stale in-memory wardrobe items for a user"""
    try:
        print(f"=== clean_memory_cache called ===")
        print(f"  user_id: {user_id}")
        
        cleaned_count = 0
        items_to_remove = []
        
        # Get list of valid items from S3
        valid_item_ids = set()
        prefix = f"users/{user_id}/wardrobe/"
        try:
            response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('_metadata.json'):
                        # Extract item ID from filename
                        filename = obj['Key'].split('/')[-1]
                        item_id = filename.replace('_metadata.json', '')
                        valid_item_ids.add(item_id)
                        
            print(f"Found {len(valid_item_ids)} valid items in S3 for user {user_id}")
        except Exception as e:
            print(f"Failed to list S3 objects during cleanup: {e}")
            
        # Check in-memory items and mark stale ones for removal
        for item_id, item in list(in_memory_wardrobe_items.items()):
            if item.get('userId') == user_id:
                if item_id not in valid_item_ids:
                    items_to_remove.append(item_id)
                    cleaned_count += 1
                    
        # Remove stale items
        for item_id in items_to_remove:
            del in_memory_wardrobe_items[item_id]
            print(f"Removed stale memory item: {item_id}")
            
        return {
            "status": "success",
            "message": f"Cleaned {cleaned_count} stale items from memory cache",
            "cleaned_count": cleaned_count,
            "valid_items": len(valid_item_ids)
        }
        
    except Exception as e:
        print(f"Error cleaning memory cache: {e}")
        return {
            "status": "error",
            "message": f"Failed to clean memory cache: {str(e)}"
        }


@mcp.tool(description="Delete an outfit from user's collection")
def delete_outfit(user_id: str, outfit_id: str) -> Dict[str, Any]:
    """Delete a saved outfit from the user's collection"""
    try:
        print(f"=== delete_outfit called ===")
        print(f"  user_id: {user_id}")
        print(f"  outfit_id: {outfit_id}")
        
        # Delete from DynamoDB using table interface
        if use_dynamodb:
            response = outfits_table.delete_item(
                Key={
                    'outfitId': outfit_id
                },
                ReturnValues='ALL_OLD'
            )
        else:
            # Fallback to in-memory (if DynamoDB not available)
            return {
                "status": "error",
                "message": "DynamoDB not available for deletion"
            }
        
        deleted_item = response.get('Attributes')
        if deleted_item:
            # Verify the outfit belongs to the requesting user
            if deleted_item.get('userId') != user_id:
                print(f"  Security error: Outfit {outfit_id} belongs to different user")
                return {
                    "status": "error",
                    "message": "Not authorized to delete this outfit"
                }
            
            print(f"  Successfully deleted outfit: {outfit_id}")
            
            # Optionally clean up the S3 image if it exists
            try:
                if 'tryOnImageUrl' in deleted_item:
                    # Table interface returns plain values, not DynamoDB format
                    s3_key = deleted_item['tryOnImageUrl']
                    if s3_key.startswith('s3://'):
                        # Extract the key from s3:// URL
                        s3_key = s3_key.replace(f's3://{S3_BUCKET}/', '')
                    
                    s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
                    print(f"  Deleted S3 image: {s3_key}")
            except Exception as s3_error:
                print(f"  Warning: Could not delete S3 image: {s3_error}")
            
            return {
                "status": "success",
                "message": f"Outfit {outfit_id} deleted successfully",
                "deleted_outfit": {
                    "outfitId": outfit_id,
                    "userId": user_id
                }
            }
        else:
            return {
                "status": "not_found",
                "message": f"Outfit {outfit_id} not found for user {user_id}"
            }
            
    except Exception as e:
        print(f"Error deleting outfit: {e}")
        return {
            "status": "error",
            "message": f"Failed to delete outfit: {str(e)}"
        }


@mcp.tool(description="Delete a wardrobe item from user's collection")
def delete_wardrobe_item(user_id: str, item_id: str) -> Dict[str, Any]:
    """Delete a wardrobe item from all storage layers (DynamoDB, S3, and in-memory cache)"""
    try:
        print(f"=== delete_wardrobe_item called ===")
        print(f"  user_id: {user_id}")
        print(f"  item_id: {item_id}")
        
        deleted_item = None
        
        # Delete from DynamoDB
        if use_dynamodb:
            try:
                response = wardrobe_items_table.delete_item(
                    Key={
                        'userId': user_id,
                        'itemId': item_id
                    },
                    ReturnValues='ALL_OLD'
                )
                deleted_item = response.get('Attributes')
                if deleted_item:
                    print(f"  Successfully deleted item from DynamoDB: {item_id}")
                else:
                    print(f"  Item {item_id} not found in DynamoDB")
            except Exception as e:
                print(f"  Error deleting from DynamoDB: {e}")
        
        # Delete from S3 (both image and metadata)
        try:
            # Delete the image file
            image_key = f"users/{user_id}/wardrobe/{item_id}.jpg"
            s3_client.delete_object(Bucket=S3_BUCKET, Key=image_key)
            print(f"  Deleted S3 image: {image_key}")
            
            # Delete the metadata file
            metadata_key = f"users/{user_id}/wardrobe/{item_id}_metadata.json"
            s3_client.delete_object(Bucket=S3_BUCKET, Key=metadata_key)
            print(f"  Deleted S3 metadata: {metadata_key}")
            
        except Exception as s3_error:
            print(f"  Warning: Could not delete S3 files: {s3_error}")
        
        # Remove from in-memory cache
        removed_from_memory = False
        if item_id in in_memory_wardrobe_items:
            del in_memory_wardrobe_items[item_id]
            removed_from_memory = True
            print(f"  Removed item from in-memory cache: {item_id}")
            
        # Remove from user's wardrobe item list in memory
        if user_id in in_memory_users and 'wardrobeItems' in in_memory_users[user_id]:
            if item_id in in_memory_users[user_id]['wardrobeItems']:
                in_memory_users[user_id]['wardrobeItems'].remove(item_id)
                print(f"  Removed item from user's wardrobe list in memory")
        
        # Determine if deletion was successful
        success = deleted_item is not None or removed_from_memory
        
        if success:
            return {
                "status": "success",
                "message": f"Wardrobe item {item_id} deleted successfully",
                "deleted_item": {
                    "itemId": item_id,
                    "userId": user_id,
                    "found_in_dynamodb": deleted_item is not None,
                    "found_in_memory": removed_from_memory
                }
            }
        else:
            return {
                "status": "not_found",
                "message": f"Wardrobe item {item_id} not found for user {user_id}"
            }
            
    except Exception as e:
        print(f"Error deleting wardrobe item: {e}")
        return {
            "status": "error",
            "message": f"Failed to delete wardrobe item: {str(e)}"
        }


if __name__ == "__main__":
    # Get MCP server configuration from environment
    MCP_HOST = os.getenv('MCP_HOST', 'localhost')
    MCP_PORT = os.getenv('MCP_PORT', '8000')
    
    # Set the correct environment variables that FastMCP actually reads
    os.environ["FASTMCP_PORT"] = MCP_PORT
    os.environ["FASTMCP_HOST"] = MCP_HOST
    
    print(f"Starting AI Wardrobe MCP server on http://{MCP_HOST}:{MCP_PORT}/sse")
    print(f"(Using FASTMCP_PORT={MCP_PORT} environment variable)")
    
    # Run with SSE transport for Strands
    mcp.run(transport="sse")