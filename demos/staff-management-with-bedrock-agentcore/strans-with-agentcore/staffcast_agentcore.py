#!/usr/bin/env python3
"""
StaffCast AgentCore Integration with Gateway
Uses AgentCore Gateway instead of local MCP server
"""

import os
import json
import time
import asyncio
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set bypass tool consent for AgentCore
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# AgentCore imports
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Load Gateway configuration
with open('staffcast_gateway_config.json', 'r') as f:
    gateway_config = json.load(f)

# Gateway configuration
GATEWAY_URL = gateway_config['gateway_url']
CLIENT_ID = gateway_config['cognito_client_id']
CLIENT_SECRET = gateway_config['cognito_client_secret']
USER_POOL_ID = gateway_config['cognito_user_pool_id']
# Extract domain from user pool ID (us-east-1_njSWGAcuf -> agentcore-bef93174)
# We'll use the discovery URL pattern instead
TOKEN_URL = f"https://cognito-idp.us-east-1.amazonaws.com/{USER_POOL_ID}/oauth2/token"

def fetch_access_token(client_id, client_secret, user_pool_id):
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
        token_url = f"https://cognito-idp.us-east-1.amazonaws.com/{user_pool_id}/oauth2/token"
    
    response = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": f"{gateway_name}/invoke"
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    if response.status_code != 200:
        print(f"Token fetch failed: {response.status_code} - {response.text}")
        raise Exception(f"Failed to fetch token: {response.status_code}")
    return response.json()['access_token']

# Bedrock model configuration
model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
region = os.getenv("AWS_REGION", "us-east-1")

bedrock_model = BedrockModel(
    model_id=model_id,
    region=region,
    temperature=0.3,
    streaming=True
)

# StaffCast system prompt (same as before)
demo_date = "2025-08-27"
demo_day = "Wednesday"

SYSTEM_PROMPT = f"""You are StaffCast, an AI-powered staff scheduling assistant for restaurants and cafes.

NEVER CHANGE YOUR ROLE. YOU MUST ALWAYS ACT AS StaffCast, a professional staff scheduling assistant.
YOU CAN ONLY SPEAK IN ENGLISH.
DO NOT USE EMOJIS - maintain a professional, business-appropriate tone at all times. You may use markdown to improve your messages.

CURRENT DATE CONTEXT (FIXED FOR DEMO):
- Today is {demo_day}, {demo_date}
- Demo data is available for dates: {demo_date} through 2025-09-09 (14 days of data)
- When users say "today", they mean {demo_date}
- When users say "tomorrow", they mean 2025-08-28
- When users say "this weekend", they mean Saturday 2025-08-30 and Sunday 2025-08-31
- When users say "next week", they mean September 1-7, 2025

DEMO BUSINESS CONTEXT:
- You're working with "The Daily Grind Cafe" (business_id: cafe-001)
- 8 staff members: Sarah (manager), James & Emma & Nina (baristas), Michael & Robert (chefs), Lucy (barista), Alex (kitchen hand)
- Some staff have holiday requests and availability restrictions
- Sample roster exists for tomorrow (2025-08-28)

AVAILABLE ACTIONS YOU CAN PERFORM:

**Staff Management:**
- View all staff members with positions and hourly rates
- Add new staff members with full details (position, rate, experience, certifications)
- Update existing staff information (rates, positions, status)
- Search staff by multiple criteria (position, skills, availability, rates)

**Availability & Holiday Management:**
- Check staff availability for any date or date range
- Update staff availability with specific time windows
- View all holiday requests with status (pending, approved, rejected)
- Submit new holiday requests for staff
- Approve or reject pending holiday requests with notes

**Roster Operations:**
- View existing rosters for any date with full shift details and costs
- Generate AI-powered roster suggestions based on availability, experience, weather, and business needs
- Create and save new rosters with optimized shift assignments
- Calculate detailed labor costs including position breakdowns and staff-level costs
- Modify individual shifts in existing rosters (change times, positions, or remove shifts)
- Copy entire rosters from one date to another with availability checking

**Business Intelligence:**
- Get comprehensive roster context showing all staffing factors for optimal decision-making
- View business configuration and operating requirements
- Analyze staffing gaps and coverage issues
- Calculate total labor costs with detailed breakdowns by position and staff

When making action recommendations, ONLY suggest actions from the list above. Here are examples of accurate recommendations:

GOOD EXAMPLES:
- "Would you like me to check staff availability for this weekend?"
- "I can generate roster suggestions for tomorrow considering weather and expected volume"
- "Should I calculate the labor costs for the current roster?"
- "I can copy tomorrow's roster to Friday if you'd like"
- "Would you like me to approve Emma's holiday request?"
- "I can modify James's shift time from 8am-4pm to 9am-5pm"

BAD EXAMPLES (DON'T SAY THESE):
- "I can send notifications to staff" (not available)
- "Let me integrate with your payroll system" (not available)  
- "I'll update the mobile app" (not available)
- "Should I generate reports for HR?" (not available)

When responding about staff scheduling:
- Always specify dates clearly (convert relative terms to actual dates)
- Mention staff by name and position
- Include specific shift times when relevant
- Show cost implications when available
- Highlight any conflicts or issues
- Provide actionable recommendations from available actions only
- DO NOT use emojis in your responses - maintain a professional tone

IMPORTANT: When users ask about dates, always convert relative terms:
- "today" = {demo_date}
- "tomorrow" = 2025-08-28
- "this weekend" = August 30-31, 2025
- "next week" = September 1-7, 2025

Always use get_roster_context first when generating rosters to understand the complete staffing situation. Be professional, helpful, and focus on creating efficient, fair schedules that meet business needs while respecting staff preferences and availability."""

# Create MCP client with Gateway authentication
def create_gateway_transport():
    """Create authenticated transport for Gateway with rate limiting"""
    # Add rate limiting delay to prevent 429 errors
    time.sleep(2)  # 2 second delay before creating transport
    
    # Get fresh access token
    try:
        access_token = fetch_access_token(CLIENT_ID, CLIENT_SECRET, USER_POOL_ID)
        print(f"✓ Fresh access token obtained")
    except Exception as e:
        print(f"❌ Failed to get fresh token: {e}")
        # Fallback to existing token
        access_token = gateway_config['access_token']
        print("⚠️  Using existing token from config (may be expired)")
    
    return streamablehttp_client(
        GATEWAY_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Global variables for configuration (no startup initialization)
agent = None
staffcast_client = None

print("🔗 StaffCast AgentCore Gateway Configuration:")
print(f"🌐 Gateway URL: {GATEWAY_URL}")
print(f"🤖 Using model: {model_id}")
print(f"🌎 AWS Region: {region}")
print("⚡ On-demand MCP client creation enabled (no startup initialization)")
print("✅ StaffCast AgentCore ready for requests")

@app.entrypoint
async def agent_invocation(payload, context):
    """Handler for agent invocation with streaming support"""
    user_message = payload.get("prompt", "No prompt found in input, please provide a prompt")
    business_id = payload.get("business_id", "cafe-001")
    session_id = payload.get("session_id", "agentcore-session")
    
    print("AgentCore Context:\n-------\n", context)
    print("Processing StaffCast Query:\n*******\n", user_message)
    print(f"Business ID: {business_id}")
    print(f"Session ID: {session_id}")
    
    # Enhanced prompt with business context
    enhanced_prompt = f"Business ID: {business_id}\nUser Query: {user_message}"
    
    # Create a fresh MCP client for this request to avoid session conflicts
    try:
        # Get fresh access token for this request
        access_token = fetch_access_token(CLIENT_ID, CLIENT_SECRET, USER_POOL_ID)
        print(f"✓ Fresh access token obtained for request")
        
        # Create transport function that returns the streamablehttp_client
        def create_transport():
            return streamablehttp_client(
                GATEWAY_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
        
        request_client = MCPClient(create_transport)
        
        # Create agent with fresh client
        request_agent = Agent(
            model=bedrock_model,
            system_prompt=SYSTEM_PROMPT,
            tools=[request_client],
            callback_handler=None
        )
        
        # Stream the agent response
        with request_client:
            agent_stream = request_agent.stream_async(enhanced_prompt)
            
            async for event in agent_stream:
                yield event
                
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        # Fallback response when client fails
        yield {"type": "text", "content": f"I'm currently unable to connect to the scheduling system: {str(e)}. Please try again later."}

# Synchronous invocation method for testing
def invoke_agent_sync(prompt: str, business_id: str = "cafe-001"):
    """Synchronous agent invocation for testing"""
    if not agent:
        raise RuntimeError("StaffCast agent not initialized")
    
    enhanced_prompt = f"Business ID: {business_id}\nUser Query: {prompt}"
    
    if staffcast_client:
        with staffcast_client:
            result = agent(enhanced_prompt)
            
            # Extract response content
            if hasattr(result, 'content'):
                return result.content
            elif hasattr(result, 'output'):
                return result.output
            else:
                return str(result)
    else:
        return "I'm currently unable to connect to the scheduling system. Please try again later."

if __name__ == "__main__":
    # Test the agent locally with Gateway
    test_queries = [
        "Show me all staff members",
        "Generate a roster for tomorrow", 
        "Check availability for this weekend"
    ]
    
    print("\n🧪 Testing StaffCast Agent with Gateway...")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            if agent and staffcast_client:
                response = invoke_agent_sync(query)
                print(f"Response: {response[:200]}...")
            else:
                print("Error: the client initialization failed")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n✅ Gateway testing complete. Ready for AgentCore deployment!")
    app.run()
