#!/usr/bin/env python3
"""
StaffCast Staff Portal AgentCore Entrypoint
Minimal AgentCore implementation for staff access with restrictions
"""

import os
import json
import requests
from dotenv import load_dotenv

# Set bypass tool consent for AgentCore
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from strands_tools import retrieve

# AgentCore imports
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Import staff configuration
from mcp_staff_config import STAFF_ALLOWED_TOOLS, filter_tool_response, validate_tool_params

# Load environment variables
load_dotenv()

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "")
DEMO_STAFF_ID = os.getenv("DEMO_STAFF_ID", "emma_davis")
DEMO_BUSINESS_ID = os.getenv("DEMO_BUSINESS_ID", "cafe-001")

# Set Strands Knowledge Base ID
if KNOWLEDGE_BASE_ID:
    os.environ["STRANDS_KNOWLEDGE_BASE_ID"] = KNOWLEDGE_BASE_ID

# Load Gateway configuration
with open('staffcast_gateway_config.json', 'r') as f:
    gateway_config = json.load(f)

GATEWAY_URL = gateway_config['gateway_url']
CLIENT_ID = gateway_config['cognito_client_id']
CLIENT_SECRET = gateway_config['cognito_client_secret']

def fetch_access_token():
    """Fetch OAuth2 access token from Cognito"""
    # Extract gateway name from the gateway URL dynamically
    gateway_url_parts = GATEWAY_URL.split('.')
    gateway_id = gateway_url_parts[0].split('://')[-1]  # Extract the subdomain part
    
    # Convert gateway ID to gateway name format (remove the suffix after second dash)
    parts = gateway_id.split('-')
    if len(parts) >= 3:
        gateway_name = f"StaffCastMCPGateway-{parts[1]}"
    else:
        gateway_name = gateway_id
    
    # Try to get the token endpoint from the discovery URL
    discovery_url = gateway_config['discovery_url']
    try:
        # Fetch the OpenID configuration to get the token endpoint
        discovery_response = requests.get(discovery_url)
        if discovery_response.status_code == 200:
            discovery_data = discovery_response.json()
            token_url = discovery_data.get('token_endpoint')
            if token_url:
                print(f"✓ Using token endpoint from discovery: {token_url}")
            else:
                raise Exception("No token_endpoint in discovery response")
        else:
            raise Exception(f"Discovery failed: {discovery_response.status_code}")
    except Exception as e:
        print(f"⚠️  Discovery failed ({e}), trying direct Cognito endpoint")
        # Fallback to standard Cognito token endpoint
        user_pool_id = gateway_config['cognito_user_pool_id']
        token_url = f"https://cognito-idp.us-east-1.amazonaws.com/{user_pool_id}/oauth2/token"
    
    response = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": f"{gateway_name}/invoke"
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    if response.status_code != 200:
        print(f"Token fetch failed: {response.status_code} - {response.text}")
        raise Exception(f"Failed to fetch token: {response.status_code}")
    return response.json()['access_token']

# Staff system prompt
STAFF_SYSTEM_PROMPT = f"""You are StaffCast Assistant, helping Emma Davis with their work schedule and company information.

CURRENT CONTEXT:
- You are assisting: Emma Davis (Staff ID: {DEMO_STAFF_ID})
- Position: Barista at The Daily Grind Cafe
- Today is Wednesday, 2025-08-27

YOUR CAPABILITIES:
1. **Schedule & Availability**: View shifts, update availability
2. **Leave Management**: Submit holiday requests, check status
3. **Company Policies**: Search company documentation
4. **Personal Records**: View certifications, training, payroll

RESTRICTIONS:
- You can only access your own personal data
- Cannot approve leave requests (only submit)
- Cannot modify rosters or access management functions

Always focus on Emma Davis's specific needs and maintain data privacy."""

def create_staff_filtered_tool(original_tool, tool_name):
    """Wrap MCP tool with staff-specific filtering"""
    class StaffFilteredTool:
        def __init__(self, tool, name):
            self.original_tool = tool
            self.tool_name = name
            for attr in dir(tool):
                if not attr.startswith('_') and attr != 'tool_name':
                    try:
                        setattr(self, attr, getattr(tool, attr))
                    except:
                        pass
        
        def __call__(self, *args, **kwargs):
            if kwargs:
                kwargs = validate_tool_params(self.tool_name, kwargs, DEMO_STAFF_ID)
            result = self.original_tool(*args, **kwargs)
            if isinstance(result, dict):
                result = filter_tool_response(self.tool_name, result, DEMO_STAFF_ID)
            return result
    
    return StaffFilteredTool(original_tool, tool_name)

# Initialize AgentCore app
app = BedrockAgentCoreApp()

@app.entrypoint
async def staff_agent_invocation(payload, context):
    """AgentCore handler for staff agent invocation with restrictions"""
    user_message = payload.get("prompt", "No prompt found in input")
    business_id = payload.get("business_id", DEMO_BUSINESS_ID)
    
    enhanced_prompt = f"Staff ID: {DEMO_STAFF_ID}\nBusiness ID: {business_id}\nStaff Query: {user_message}"
    
    try:
        access_token = fetch_access_token()
        
        def create_transport():
            return streamablehttp_client(
                GATEWAY_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        request_client = MCPClient(create_transport)
        
        bedrock_model = BedrockModel(
            model_id=BEDROCK_MODEL_ID,
            region=AWS_REGION,
            temperature=0.3,
            streaming=True
        )
        
        with request_client:
            all_tools = request_client.list_tools_sync()
            staff_tools = []
            
            for tool in all_tools:
                tool_name = getattr(tool, 'tool_name', str(tool))
                if tool_name in STAFF_ALLOWED_TOOLS:
                    wrapped_tool = create_staff_filtered_tool(tool, tool_name)
                    staff_tools.append(wrapped_tool)
            
            if KNOWLEDGE_BASE_ID:
                staff_tools.append(retrieve)
        
        request_agent = Agent(
            model=bedrock_model,
            system_prompt=STAFF_SYSTEM_PROMPT,
            tools=staff_tools
        )
        
        with request_client:
            agent_stream = request_agent.stream_async(enhanced_prompt)
            async for event in agent_stream:
                yield event
                
    except Exception as e:
        yield {"type": "text", "content": f"I'm currently unable to connect to the scheduling system: {str(e)}. Please try again later."}

if __name__ == "__main__":
    print(f"🔗 StaffCast Staff Portal AgentCore")
    print(f"🌐 Gateway URL: {GATEWAY_URL}")
    print(f"👤 Staff Member: Emma Davis ({DEMO_STAFF_ID})")
    print(f"🤖 Model: {BEDROCK_MODEL_ID}")
    if KNOWLEDGE_BASE_ID:
        print(f"📚 Knowledge Base: {KNOWLEDGE_BASE_ID}")
    print("✅ Ready")
    
    app.run()
