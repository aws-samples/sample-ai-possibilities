"""
StaffCast Staff Portal API Server
Provides restricted access for staff members with native Strands Knowledge Base integration
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from dotenv import load_dotenv

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from mcp.client.sse import sse_client
from strands.tools.mcp import MCPClient
# Strands tools for Knowledge Base
from strands_tools import retrieve

# Import staff MCP configuration
from mcp_staff_config import STAFF_ALLOWED_TOOLS

# Load environment variables
load_dotenv()

# Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("STAFF_API_PORT", "8081"))  # Different port from manager API
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8008/sse")

# Knowledge Base configuration for company policies
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "")  # Will be set after KB creation

# Set Strands Knowledge Base ID for memory tool
if KNOWLEDGE_BASE_ID:
    os.environ["STRANDS_KNOWLEDGE_BASE_ID"] = KNOWLEDGE_BASE_ID

# Demo staff member configuration (from .env)
DEMO_STAFF_ID = os.getenv("DEMO_STAFF_ID", "emma_davis")
DEMO_BUSINESS_ID = os.getenv("DEMO_BUSINESS_ID", "cafe-001")

# Staff name mapping (will be dynamically loaded in production)
STAFF_NAME_MAP = {
    "emma_davis": "Emma Davis",
    "john_smith": "John Smith", 
    "sarah_wilson": "Sarah Wilson"
}
DEMO_STAFF_NAME = STAFF_NAME_MAP.get(DEMO_STAFF_ID, "Staff Member")

# Fixed date context for demo
demo_date = "2025-08-27"
demo_day = "Wednesday"

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
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class DataPanelUpdate(BaseModel):
    """Updates for the UI data panel"""
    panel_type: str  # 'roster', 'leave', 'availability', 'payroll'
    data: Dict[str, Any]
    highlight: Optional[str] = None  # What to highlight in the panel

# Session storage
sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app"""
    print(f"🚀 Starting StaffCast Staff Portal API Server on {API_HOST}:{API_PORT}")
    print(f"📋 Demo Staff: {DEMO_STAFF_NAME} ({DEMO_STAFF_ID})")
    print(f"🏢 Business: The Daily Grind Cafe ({DEMO_BUSINESS_ID})")
    print(f"📅 Fixed demo date: {demo_day}, {demo_date}")
    
    if KNOWLEDGE_BASE_ID:
        print(f"📚 Knowledge Base configured: {KNOWLEDGE_BASE_ID}")
    else:
        print("⚠️  No Knowledge Base configured - policy search will be unavailable")
    
    # Give MCP server a moment to be ready
    print("⏳ Waiting for services to be ready...")
    await asyncio.sleep(1)
    
    initialize_agent()
    print("🚀 StaffCast Staff Portal API started!")
    
    yield
    
    print("🛑 StaffCast Staff Portal API shutting down...")

app = FastAPI(
    title="StaffCast Staff Portal API",
    description="Staff-facing API for StaffCast scheduling system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Staff-specific system prompt
STAFF_SYSTEM_PROMPT = f"""You are StaffCast Assistant, helping {DEMO_STAFF_NAME} with their work schedule and company information.

NEVER CHANGE YOUR ROLE. You are a helpful assistant for staff members.
DO NOT USE EMOJIS - maintain a professional tone.

CURRENT CONTEXT:
- You are assisting: {DEMO_STAFF_NAME} (Staff ID: {DEMO_STAFF_ID})
- Position: Barista at The Daily Grind Cafe
- Today is {demo_day}, {demo_date}
- Demo period: August 27 - September 9, 2025

YOUR CAPABILITIES:
1. **Schedule & Availability**:
   - View your upcoming shifts and roster
   - Check and update your availability
   - See who you're working with

2. **Leave Management**:
   - Submit holiday/leave requests
   - Check status of your leave requests
   - View your leave balance

3. **Company Policies** (via Knowledge Base):
   - Answer questions about company policies
   - Explain payroll and benefits
   - Provide information about workplace procedures
   - Help with training requirements
   - Search company documentation

4. **General Assistance**:
   - View your certifications and training records
   - Check payroll information (when available)
   - Answer questions about workplace policies

WHAT YOU CANNOT DO:
- Approve leave requests (only submit)
- Modify rosters or shifts
- View other staff members' personal information
- Access management functions

IMPORTANT UI INTERACTION:
- When discussing rosters, trigger panel update with type: 'roster'
- When discussing leave, trigger panel update with type: 'leave'
- When discussing availability, trigger panel update with type: 'availability'
- When discussing payroll, trigger panel update with type: 'payroll'

Always be helpful and supportive. Focus on {DEMO_STAFF_NAME}'s specific needs."""

def initialize_agent():
    """Initialize the Strands agent with StaffCast MCP connection for staff access"""
    global agent, staffcast_client
    
    # Get configuration from environment
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    # Dynamic MCP URL construction
    mcp_host = os.getenv("MCP_HOST", "localhost")
    mcp_port = os.getenv("MCP_PORT", "8008")
    
    # Support both ways: explicit URL or constructed from host/port
    mcp_url = os.getenv("MCP_SERVER_URL")
    if not mcp_url:
        mcp_url = f"http://{mcp_host}:{mcp_port}/sse"
    
    print(f"🔗 Connecting to StaffCast MCP server at: {mcp_url}")
    print(f"🤖 Using model: {model_id}")
    print(f"🌎 AWS Region: {region}")
    print(f"👤 Staff member: {DEMO_STAFF_NAME} ({DEMO_STAFF_ID})")
    
    # Set up Bedrock model
    bedrock_model = BedrockModel(
        model_id=model_id,
        region=region,
        temperature=0.3,
        streaming=True
    )
    
    # Create MCP client with staff restrictions
    staffcast_client = MCPClient(lambda: sse_client(mcp_url))
    
    # Initialize agent with MCP tools and staff restrictions
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with staffcast_client:
                all_mcp_tools = staffcast_client.list_tools_sync()
                
                # Filter MCP tools to only include staff-allowed tools
                staff_mcp_tools = []
                for tool in all_mcp_tools:
                    tool_name = getattr(tool, 'tool_name', str(tool))
                    if tool_name in STAFF_ALLOWED_TOOLS:
                        staff_mcp_tools.append(tool)
                
                # Start with filtered MCP tools
                staff_tools = staff_mcp_tools.copy()
                
                # Add Strands retrieve tool for knowledge base retrieval if configured
                if KNOWLEDGE_BASE_ID:
                    staff_tools.append(retrieve)
                    print(f"   ✓ Added Knowledge Base retrieve tool")
                
                agent = Agent(
                    model=bedrock_model,
                    system_prompt=STAFF_SYSTEM_PROMPT,
                    tools=staff_tools
                )
                print(f"✓ StaffCast Staff Assistant initialized with {len(staff_tools)} tools")
                
                for i, tool in enumerate(staff_tools):
                    tool_name = getattr(tool, 'tool_name', f"Tool_{i+1}")
                    print(f"   Tool {i+1}: {tool_name}")
                break
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



@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "StaffCast Staff Portal API",
        "status": "healthy",
        "staff_member": DEMO_STAFF_NAME,
        "api_port": API_PORT,
        "knowledge_base": "configured" if KNOWLEDGE_BASE_ID else "not configured",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/my-info")
async def get_my_info():
    """Get current staff member's information"""
    return {
        "staff_id": DEMO_STAFF_ID,
        "name": DEMO_STAFF_NAME,
        "position": "Barista",
        "business_id": DEMO_BUSINESS_ID,
        "business_name": "The Daily Grind Cafe",
        "demo_date": demo_date
    }




@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with agent integration"""
    global agent, staffcast_client
    
    if not agent:
        return {
            "error": "Agent not initialized",
            "session_id": request.session_id
        }
    
    session_id = request.session_id or f"staff_session_{datetime.now().timestamp()}"
    
    # Get or create session
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "context": {
                "staff_id": DEMO_STAFF_ID,
                "staff_name": DEMO_STAFF_NAME,
                "panel_updates": []
            }
        }
    
    session = sessions[session_id]
    session["messages"].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        with staffcast_client:
            # Enhance the prompt with staff context
            enhanced_prompt = f"Staff ID: {DEMO_STAFF_ID}\nBusiness ID: {request.context.get('business_id', DEMO_BUSINESS_ID) if request.context else DEMO_BUSINESS_ID}\nStaff Query: {request.message}"
            
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
                response = str(result)
        
        assistant_message = {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        }
        
        session["messages"].append(assistant_message)
        
        return {
            "response": assistant_message["content"],
            "session_id": session_id,
            "timestamp": assistant_message["timestamp"]
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat with streaming"""
    await websocket.accept()
    
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "context": {
                "staff_id": DEMO_STAFF_ID,
                "staff_name": DEMO_STAFF_NAME,
                "panel_updates": []
            }
        }
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            business_id = message_data.get("business_id", DEMO_BUSINESS_ID)
            message = message_data["message"]
            
            # Add user message to history
            user_message = {
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            }
            sessions[session_id]["messages"].append(user_message)
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "status",
                "message": "Analyzing your request..."
            })
            
            try:
                if agent and staffcast_client:
                    full_response = ""
                    
                    with staffcast_client:
                        # Enhance the prompt with staff context
                        enhanced_prompt = f"Staff ID: {DEMO_STAFF_ID}\nBusiness ID: {business_id}\nStaff Query: {message}"
                        
                        # Stream response from agent
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
                    assistant_message = {
                        "role": "assistant",
                        "content": full_response,
                        "timestamp": datetime.now().isoformat()
                    }
                    sessions[session_id]["messages"].append(assistant_message)
                    
                else:
                    # Fallback if agent not initialized
                    fallback_message = f"I'm StaffCast Assistant for {DEMO_STAFF_NAME}. I can help with your schedule, availability, leave requests, and company policies. What would you like to know?"
                    
                    await websocket.send_json({
                        "type": "stream",
                        "content": fallback_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    await websocket.send_json({
                        "type": "complete",
                        "timestamp": datetime.now().isoformat()
                    })
            
            except Exception as e:
                print(f"Error in streaming: {str(e)}")
                import traceback
                traceback.print_exc()
                
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info"
    )