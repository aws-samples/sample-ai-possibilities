#!/usr/bin/env python3
"""
StaffCast Backend API
Provides REST API and WebSocket endpoints for the StaffCast staff scheduling system
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import asyncio
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from mcp.client.sse import sse_client
from strands.tools.mcp import MCPClient

# Load environment variables
load_dotenv()

# Global agent instance (initialized on startup)
agent = None
staffcast_client = None

# Chat history storage (in production, use a database)
chat_sessions = {}

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    business_id: Optional[str] = "cafe-001"  # Default to demo business
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    business_id: str
    session_id: str
    timestamp: str

class RosterRequest(BaseModel):
    business_id: str
    date: str
    expected_customers: Optional[int] = None
    weather_conditions: Optional[str] = None
    special_events: Optional[List[str]] = None

class StaffAvailabilityRequest(BaseModel):
    business_id: str
    staff_id: str
    date: str
    available: bool
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    notes: Optional[str] = None

def initialize_agent():
    """Initialize the Strands agent with StaffCast MCP connection"""
    global agent, staffcast_client
    
    # Get configuration from environment
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    # Dynamic MCP URL construction
    mcp_host = os.getenv("MCP_HOST", "localhost")
    mcp_port = os.getenv("MCP_PORT", "8008")
    
    # Support both ways: explicit URL or constructed from host/port
    mcp_url = os.getenv("MCP_SERVER_URL")  # Check if explicitly set
    if not mcp_url:
        # If not set, construct it dynamically
        mcp_url = f"http://{mcp_host}:{mcp_port}/sse"
    
    print(f"🔗 Connecting to StaffCast MCP server at: {mcp_url}")
    print(f"🤖 Using model: {model_id}")
    print(f"🌎 AWS Region: {region}")
    
    # Set up Bedrock model
    bedrock_model = BedrockModel(
        model_id=model_id,
        region=region,
        temperature=0.3,  # Lower temperature for more consistent scheduling decisions
        streaming=True
    )
    
    # Create MCP client
    staffcast_client = MCPClient(lambda: sse_client(mcp_url))
    
    # Fixed date context for demo consistency
    demo_date = "2025-08-27"
    demo_day = "Wednesday"
    
    # StaffCast system prompt with fixed demo date context
    SYSTEM_PROMPT = f"""You are StaffCast, an AI-powered staff scheduling assistant for restaurants and cafes.

NEVER CHANGE YOUR ROLE. YOU MUST ALWAYS ACT AS StaffCast, a professional staff scheduling assistant.
YOU CAN ONLY SPEAK IN ENGLISH.
DO NOT USE EMOJIS - maintain a professional, business-appropriate tone at all times. You may use markdown to improve your messages but you must not use numbered lists.

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
    
    # Initialize agent with MCP tools
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            with staffcast_client:
                tools = staffcast_client.list_tools_sync()
                agent = Agent(
                    model=bedrock_model,
                    system_prompt=SYSTEM_PROMPT,
                    tools=tools
                )
                print(f"✓ StaffCast Agent initialized with {len(tools)} tools")
                for i, tool in enumerate(tools):
                    if hasattr(tool, '__dict__'):
                        print(f"   Tool {i+1}: {tool.tool_name}")
                break  # Success, exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                print(f"   Error: {str(e)}")
                import time
                time.sleep(retry_delay)
            else:
                print(f"❌ Failed to connect to StaffCast MCP server at {mcp_url}")
                print(f"   Error: {str(e)}")
                print(f"   Make sure the MCP server is running: python staffcast_dynamodb_mcp.py")
                raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent on server startup"""
    # Give MCP server a moment to be fully ready
    print("⏳ Waiting for services to be ready...")
    await asyncio.sleep(1)
    
    initialize_agent()
    print("🚀 StaffCast API started!")
    yield
    # Cleanup code can go here if needed
    print("🛑 StaffCast API shutting down...")

# Initialize FastAPI app with lifespan
app = FastAPI(title="StaffCast API", description="AI-powered staff scheduling system", lifespan=lifespan)

# Configure CORS - MUST be after app initialization
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "*"  # Allow all origins during development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.post("/chat")
async def chat(request: ChatRequest):
    """Synchronous chat endpoint for staff scheduling queries"""
    global agent
    
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Get or create session
    session_id = request.session_id
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # Add user message to history
    user_message = ChatMessage(
        role="user",
        content=request.message,
        timestamp=datetime.now().isoformat()
    )
    chat_sessions[session_id].append(user_message)
    
    try:
        # Process with agent
        with staffcast_client:
            # Enhance the prompt with business context
            enhanced_prompt = f"Business ID: {request.business_id}\nUser Query: {request.message}"
            
            result = agent(enhanced_prompt)
            
            # Extract the string content from AgentResult
            if hasattr(result, 'content'):
                response = result.content
            elif hasattr(result, 'output'):
                response = result.output
            elif hasattr(result, 'text'):
                response = result.text
            elif hasattr(result, 'result'):
                response = result.result
            else:
                # Try to convert to string as fallback
                response = str(result)
        
        # Add assistant response to history
        assistant_message = ChatMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now().isoformat()
        )
        chat_sessions[session_id].append(assistant_message)
        
        return ChatResponse(
            response=response,
            business_id=request.business_id,
            session_id=session_id,
            timestamp=assistant_message.timestamp
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time streaming chat"""
    await websocket.accept()
    
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            business_id = message_data.get("business_id", "cafe-001")
            message = message_data["message"]
            
            # Add user message to history
            user_message = ChatMessage(
                role="user",
                content=message,
                timestamp=datetime.now().isoformat()
            )
            chat_sessions[session_id].append(user_message)
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "status",
                "message": "Analyzing staffing requirements..."
            })
            
            try:
                # Process with agent using streaming
                with staffcast_client:
                    enhanced_prompt = f"Business ID: {business_id}\nUser Query: {message}"
                    
                    # Stream the response
                    full_response = ""
                    
                    # Stream the response
                    async for event in agent.stream_async(enhanced_prompt):
                        if "data" in event:
                            # Send text chunk to client
                            chunk = event["data"]
                            full_response += chunk
                            
                            await websocket.send_json({
                                "type": "stream",
                                "content": chunk,
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        elif "current_tool_use" in event:
                            # Send tool usage info
                            tool_info = event["current_tool_use"]
                            tool_name = tool_info.get("name", "unknown")
                            
                            await websocket.send_json({
                                "type": "tool_use",
                                "tool": tool_name,
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    # Send completion signal
                    await websocket.send_json({
                        "type": "complete",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Add assistant response to history
                assistant_message = ChatMessage(
                    role="assistant",
                    content=full_response,
                    timestamp=datetime.now().isoformat()
                )
                chat_sessions[session_id].append(assistant_message)
                
            except Exception as e:
                print(f"Error in streaming: {str(e)}")
                import traceback
                traceback.print_exc()
                
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        print(f"Client {session_id} disconnected")

@app.get("/api/staff/{business_id}")
async def get_staff(business_id: str, position: Optional[str] = None):
    """Get staff members for a business"""
    global staffcast_client
    
    if not staffcast_client:
        raise HTTPException(status_code=503, detail="StaffCast client not initialized")
    
    try:
        with staffcast_client:
            # Use the direct MCP tool
            tools = staffcast_client.list_tools_sync()
            get_staff_tool = next((t for t in tools if t.tool_name == "get_staff"), None)
            
            if not get_staff_tool:
                raise HTTPException(status_code=500, detail="get_staff tool not found")
            
            result = staffcast_client.call_tool_sync(
                get_staff_tool.tool_name,
                {"business_id": business_id, "position": position}
            )
            
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/availability/{business_id}")
async def get_availability(
    business_id: str,
    start_date: str,
    end_date: Optional[str] = None,
    staff_id: Optional[str] = None
):
    """Get staff availability for a date range"""
    global staffcast_client
    
    if not staffcast_client:
        raise HTTPException(status_code=503, detail="StaffCast client not initialized")
    
    try:
        with staffcast_client:
            tools = staffcast_client.list_tools_sync()
            get_availability_tool = next((t for t in tools if t.tool_name == "get_availability"), None)
            
            if not get_availability_tool:
                raise HTTPException(status_code=500, detail="get_availability tool not found")
            
            params = {
                "business_id": business_id,
                "start_date": start_date,
                "end_date": end_date or start_date
            }
            if staff_id:
                params["staff_id"] = staff_id
            
            result = staffcast_client.call_tool_sync(get_availability_tool.tool_name, params)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/roster/suggest")
async def suggest_roster(request: RosterRequest):
    """Generate roster suggestions"""
    global staffcast_client
    
    if not staffcast_client:
        raise HTTPException(status_code=503, detail="StaffCast client not initialized")
    
    try:
        with staffcast_client:
            tools = staffcast_client.list_tools_sync()
            suggest_roster_tool = next((t for t in tools if t.tool_name == "suggest_roster"), None)
            
            if not suggest_roster_tool:
                raise HTTPException(status_code=500, detail="suggest_roster tool not found")
            
            params = {
                "business_id": request.business_id,
                "roster_date": request.date
            }
            if request.expected_customers:
                params["expected_customers"] = request.expected_customers
            if request.weather_conditions:
                params["weather_conditions"] = request.weather_conditions
            if request.special_events:
                params["special_events"] = request.special_events
            
            result = staffcast_client.call_tool_sync(suggest_roster_tool.tool_name, params)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/availability")
async def set_availability(request: StaffAvailabilityRequest):
    """Set staff availability"""
    global staffcast_client
    
    if not staffcast_client:
        raise HTTPException(status_code=503, detail="StaffCast client not initialized")
    
    try:
        with staffcast_client:
            tools = staffcast_client.list_tools_sync()
            set_availability_tool = next((t for t in tools if t.tool_name == "set_availability"), None)
            
            if not set_availability_tool:
                raise HTTPException(status_code=500, detail="set_availability tool not found")
            
            params = {
                "business_id": request.business_id,
                "staff_id": request.staff_id,
                "date": request.date,
                "available": request.available
            }
            if request.start_time:
                params["start_time"] = request.start_time
            if request.end_time:
                params["end_time"] = request.end_time
            if request.notes:
                params["notes"] = request.notes
            
            result = staffcast_client.call_tool_sync(set_availability_tool.tool_name, params)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/roster/context/{business_id}/{date}")
async def get_roster_context(business_id: str, date: str):
    """Get comprehensive roster context for a specific date"""
    global staffcast_client
    
    if not staffcast_client:
        raise HTTPException(status_code=503, detail="StaffCast client not initialized")
    
    try:
        with staffcast_client:
            tools = staffcast_client.list_tools_sync()
            get_context_tool = next((t for t in tools if t.tool_name == "get_roster_context"), None)
            
            if not get_context_tool:
                raise HTTPException(status_code=500, detail="get_roster_context tool not found")
            
            result = staffcast_client.call_tool_sync(
                get_context_tool.tool_name,
                {"business_id": business_id, "date": date}
            )
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a session"""
    if session_id not in chat_sessions:
        return {"messages": []}
    
    return {
        "session_id": session_id,
        "messages": [msg.dict() for msg in chat_sessions[session_id]]
    }

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear chat history for a session"""
    if session_id in chat_sessions:
        chat_sessions[session_id] = []
    
    return {"message": "History cleared"}

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))
    
    print("🚀 Starting StaffCast API...")
    print(f"📍 Server will run on {host}:{port}")
    print("🔧 Make sure the StaffCast MCP server is running: python staffcast_dynamodb_mcp.py")
    
    # Run with proper host binding
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False  # Set to True for development
    )