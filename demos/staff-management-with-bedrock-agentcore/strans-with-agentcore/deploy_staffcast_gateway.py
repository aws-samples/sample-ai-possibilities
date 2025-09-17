#!/usr/bin/env python3
"""
Deploy StaffCast Lambda function and create AgentCore Gateway
Using the official AgentCore Starter Toolkit
Based on: https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/gateway/quickstart.html
"""

import boto3
import json
import time
import zipfile
import os
import logging
from datetime import datetime
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Configuration
REGION = os.getenv("AWS_REGION")
LAMBDA_FUNCTION_NAME = 'staffcast-mcp-lambda'
GATEWAY_NAME = f'StaffCastMCPGateway-{int(time.time())}'  # Use timestamp to make it unique

def create_lambda_zip():
    """Create ZIP file for Lambda deployment"""
    zip_path = 'staffcast_lambda.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('staffcast_lambda.py', 'staffcast_lambda.py')
    
    print(f"✓ Created Lambda ZIP: {zip_path}")
    return zip_path

def create_lambda_role():
    """Create IAM role for Lambda function"""
    iam = boto3.client('iam', region_name=REGION)
    
    role_name = f'{LAMBDA_FUNCTION_NAME}-role'
    
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": "arn:aws:dynamodb:*:*:table/staffcast-*"
            }
        ]
    }
    
    try:
        # Create role
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description='IAM role for StaffCast MCP Lambda function'
        )
        
        # Attach policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='StaffCastLambdaPolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✓ Created IAM role: {role_name}")
        return role_response['Role']['Arn']
        
    except iam.exceptions.EntityAlreadyExistsException:
        role_response = iam.get_role(RoleName=role_name)
        print(f"✓ Using existing IAM role: {role_name}")
        return role_response['Role']['Arn']

def deploy_lambda_function(role_arn, zip_path):
    """Deploy Lambda function"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    with open(zip_path, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    try:
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime='python3.12',
            Role=role_arn,
            Handler='staffcast_lambda.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='StaffCast MCP tools Lambda function',
            Timeout=30,
            MemorySize=256
        )
        
        print(f"✓ Created Lambda function: {LAMBDA_FUNCTION_NAME}")
        return response['FunctionArn']
        
    except lambda_client.exceptions.ResourceConflictException:
        # Update existing function
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_content
        )
        
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        print(f"✓ Updated existing Lambda function: {LAMBDA_FUNCTION_NAME}")
        return response['Configuration']['FunctionArn']

def create_agentcore_gateway(lambda_arn):
    """Create AgentCore Gateway using boto3 client with proper error handling"""
    print("\n🌐 Creating AgentCore Gateway...")
    
    # Setup boto3 client for bedrock-agentcore-control
    boto_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    
    try:
        # Step 1: Check if gateway already exists
        print("🔍 Checking for existing gateways...")
        gateways = boto_client.list_gateways()
        
        for gateway in gateways.get('gateways', []):
            if gateway.get('name') == GATEWAY_NAME:
                print(f"✓ Found existing gateway: {GATEWAY_NAME}")
                gateway_id = gateway.get('gatewayId')
                gateway_url = gateway.get('gatewayUrl')
                gateway_arn = gateway.get('gatewayArn', '')
                
                # Get existing targets
                target_id = 'unknown'
                try:
                    gateway_targets = boto_client.list_gateway_targets(gatewayIdentifier=gateway_id)
                    targets = gateway_targets.get('gatewayTargets', [])
                    if targets:
                        target_id = targets[0].get('targetId', 'unknown')
                        print(f"  Using existing target: {target_id}")
                except Exception as e:
                    print(f"  Warning: Could not get targets: {e}")
                
                # Create a dummy cognito response for compatibility
                cognito_response = {
                    "client_info": {
                        "user_pool_id": "us-east-1_Q8S5xEgFu",  # From deployment logs
                        "client_id": "5v22fqn5gnb4ma3kfi686l1jum",  # From deployment logs
                        "client_secret": "placeholder-secret",
                        "discovery_url": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Q8S5xEgFu/.well-known/openid-configuration"
                    }
                }
                
                return {
                    'gateway_id': gateway_id,
                    'gateway_url': gateway_url,
                    'gateway_arn': gateway_arn,
                    'target_id': target_id,
                    'cognito_response': cognito_response,
                    'access_token': 'existing-token'
                }
        
        # Step 2: If no existing gateway, use the Starter Toolkit to create one
        print("🌉 No existing gateway found. Creating new gateway with Starter Toolkit...")
        
        # Initialize Gateway Client
        from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
        client = GatewayClient(region_name=REGION)
        client.logger.setLevel(logging.INFO)  # Reduce verbosity
        
        # Create OAuth authorization server
        print("🔒 Creating OAuth authorization server...")
        cognito_response = client.create_oauth_authorizer_with_cognito(GATEWAY_NAME)
        print("✓ Created Cognito authorizer")
        
        # Create the gateway
        print("🌉 Creating Gateway...")
        gateway = client.create_mcp_gateway(
            name=GATEWAY_NAME,
            role_arn=None,  # Will be created automatically
            authorizer_config=cognito_response["authorizer_config"],
            enable_semantic_search=True,
        )
        print(f"✓ Created Gateway: {gateway['gatewayId']}")
        print(f"  Gateway URL: {gateway['gatewayUrl']}")
        
        # Create Lambda target with StaffCast tools
        print("🛠️ Creating Lambda target...")
        lambda_target = client.create_mcp_gateway_target(
            gateway=gateway,
            name="StaffCastLambdaTarget",
            target_type="lambda",
            target_payload={
                "lambdaArn": lambda_arn,
                "toolSchema": {
                    "inlinePayload": [
                        {
                            "name": "get_staff_tool",
                            "description": "Get staff members for a business",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "business_id": {"type": "string"},
                                    "position": {"type": "string"},
                                    "active_only": {"type": "boolean"}
                                },
                                "required": ["business_id"]
                            }
                        },
                        {
                            "name": "get_availability_tool",
                            "description": "Get staff availability for a date range",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "business_id": {"type": "string"},
                                    "start_date": {"type": "string"},
                                    "end_date": {"type": "string"},
                                    "staff_id": {"type": "string"}
                                },
                                "required": ["business_id", "start_date", "end_date"]
                            }
                        },
                        {
                            "name": "suggest_roster_tool",
                            "description": "Generate roster suggestions based on parameters",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "business_id": {"type": "string"},
                                    "roster_date": {"type": "string"},
                                    "expected_customers": {"type": "integer"},
                                    "weather_conditions": {"type": "string"}
                                },
                                "required": ["business_id", "roster_date"]
                            }
                        },
                        {
                            "name": "get_roster_context_tool",
                            "description": "Get comprehensive roster context for intelligent generation",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "business_id": {"type": "string"},
                                    "date": {"type": "string"}
                                },
                                "required": ["business_id", "date"]
                            }
                        }
                    ]
                }
            },
            credentials=None,  # Will use Gateway IAM role
        )
        print(f"✓ Created Lambda target: {lambda_target['targetId']}")
        
        # Get access token
        print("🎫 Getting access token...")
        access_token = client.get_access_token_for_cognito(cognito_response["client_info"])
        print("✓ Access token obtained")
        
        return {
            'gateway_id': gateway["gatewayId"],
            'gateway_url': gateway["gatewayUrl"],
            'gateway_arn': gateway.get("gatewayArn", ""),
            'target_id': lambda_target["targetId"],
            'cognito_response': cognito_response,
            'access_token': access_token
        }
        
    except Exception as e:
        print(f"❌ Failed to create/access gateway: {str(e)}")
        print("   Make sure you have the correct permissions for bedrock-agentcore-control")
        raise

def main():
    """Main deployment function"""
    print("🚀 Deploying StaffCast Lambda and AgentCore Gateway")
    print("=" * 60)
    
    # Step 1: Create Lambda ZIP
    zip_path = create_lambda_zip()
    
    # Step 2: Create Lambda role and function
    print("\n📦 Creating Lambda function...")
    lambda_role_arn = create_lambda_role()
    time.sleep(10)  # Wait for role propagation
    lambda_arn = deploy_lambda_function(lambda_role_arn, zip_path)
    
    # Step 3: Create Gateway using Starter Toolkit
    print("\n🌐 Creating AgentCore Gateway...")
    gateway_config = create_agentcore_gateway(lambda_arn)
    
    # Step 4: Output configuration
    print("\n" + "=" * 60)
    print("🎉 Deployment Complete!")
    print("=" * 60)
    
    config = {
        "lambda_function_arn": lambda_arn,
        "gateway_id": gateway_config['gateway_id'],
        "gateway_url": gateway_config['gateway_url'],
        "gateway_arn": gateway_config['gateway_arn'],
        "target_id": gateway_config['target_id'],
        "cognito_user_pool_id": gateway_config['cognito_response']['client_info']['user_pool_id'],
        "cognito_client_id": gateway_config['cognito_response']['client_info']['client_id'],
        "cognito_client_secret": gateway_config['cognito_response']['client_info']['client_secret'],
        "discovery_url": gateway_config['cognito_response']['client_info'].get('discovery_url') or 
                        gateway_config['cognito_response']['client_info'].get('discoveryUrl') or
                        f"https://cognito-idp.{REGION}.amazonaws.com/{gateway_config['cognito_response']['client_info']['user_pool_id']}/.well-known/openid-configuration",
        "access_token": gateway_config['access_token']
    }
    
    # Save configuration
    with open('staffcast_gateway_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Lambda Function ARN: {lambda_arn}")
    print(f"Gateway URL: {gateway_config['gateway_url']}")
    print(f"Gateway ID: {gateway_config['gateway_id']}")
    print(f"Target ID: {gateway_config['target_id']}")
    print(f"Client ID: {gateway_config['cognito_response']['client_info']['client_id']}")
    print(f"\n📄 Configuration saved to: staffcast_gateway_config.json")
    
    # Cleanup
    os.remove(zip_path)
    
    return config

if __name__ == "__main__":
    main()
