#!/usr/bin/env python3
"""
Test script for Nick - Video Insights Agent
Tests both REST and WebSocket endpoints
"""

import requests
import json
import asyncio
import websockets
from datetime import datetime
import os
import time

# Configuration
# Get port from environment or use default
import os
API_PORT = os.getenv("API_PORT", "8090")
BASE_URL = f"http://localhost:{API_PORT}"
WS_URL = f"ws://localhost:{API_PORT}/ws"
SESSION_ID = "test_session"

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    print(f"   Connecting to: {BASE_URL}/")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection failed: Cannot connect to {BASE_URL}")
        print(f"   Error: {e}")
        print("\n⚠️  Make sure Nick agent is running on the correct port!")
        print(f"   Expected: {BASE_URL}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 5 seconds")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def test_chat_endpoint():
    """Test the synchronous chat endpoint"""
    print("\n💬 Testing chat endpoint...")
    
    test_messages = [
        "Hi Nick, can you help me find videos about construction?",
        "What's the sentiment of the first video?",
        "Can you write code for me?",  # Should be rejected
        "Show me videos that mention Nike"
    ]
    
    for message in test_messages:
        print(f"\n📤 Sending: {message}")
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": message, "session_id": SESSION_ID}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response received:")
            print(f"   {data['response'][:200]}..." if len(data['response']) > 200 else f"   {data['response']}")
        else:
            print(f"❌ Chat failed: {response.status_code}")

def test_history_endpoint():
    """Test the history endpoint"""
    print("\n📜 Testing history endpoint...")
    response = requests.get(f"{BASE_URL}/history/{SESSION_ID}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ History retrieved: {len(data['messages'])} messages")
        if data.get('video_context'):
            print(f"   Video context: {data['video_context']}")
    else:
        print(f"❌ History retrieval failed: {response.status_code}")

def test_suggestions_endpoint():
    """Test the suggestions endpoint"""
    print("\n💡 Testing suggestions endpoint...")
    response = requests.get(f"{BASE_URL}/api/search/suggestions")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Suggestions retrieved: {len(data['suggestions'])} suggestions")
        for i, suggestion in enumerate(data['suggestions'][:3], 1):
            print(f"   {i}. {suggestion}")
    else:
        print(f"❌ Suggestions failed: {response.status_code}")

async def test_websocket_endpoint():
    """Test the WebSocket endpoint"""
    print("\n🔌 Testing WebSocket endpoint...")
    
    try:
        async with websockets.connect(f"{WS_URL}/{SESSION_ID}") as websocket:
            # Send a message
            message = {"message": "Find videos with positive sentiment about training"}
            print(f"📤 Sending via WebSocket: {message['message']}")
            await websocket.send(json.dumps(message))
            
            # Receive responses
            complete = False
            chunks = []
            
            while not complete:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data["type"] == "status":
                    print(f"📊 Status: {data['message']}")
                elif data["type"] == "tool_use":
                    print(f"🔧 Using tool: {data['tool']} - {data.get('status', '')}")
                elif data["type"] == "stream":
                    chunks.append(data["content"])
                    print(".", end="", flush=True)
                elif data["type"] == "complete":
                    print(f"\n✅ WebSocket streaming completed")
                    complete = True
                elif data["type"] == "error":
                    print(f"\n❌ WebSocket error: {data['message']}")
                    complete = True
            
            if chunks:
                full_response = "".join(chunks)
                print(f"📝 Full response: {full_response[:200]}...")
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

def test_context_endpoint():
    """Test the context endpoint"""
    print("\n🎯 Testing context endpoint...")
    response = requests.get(f"{BASE_URL}/api/session/{SESSION_ID}/context")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Context retrieved:")
        print(f"   Recent videos: {data['context'].get('recent_videos', [])}")
        print(f"   All mentioned videos: {len(data['context'].get('all_mentioned_videos', {}))}")
    else:
        print(f"❌ Context retrieval failed: {response.status_code}")

def test_clear_history():
    """Test clearing history"""
    print("\n🗑️ Testing clear history...")
    response = requests.delete(f"{BASE_URL}/history/{SESSION_ID}")
    
    if response.status_code == 200:
        print(f"✅ History cleared: {response.json()['message']}")
    else:
        print(f"❌ Clear history failed: {response.status_code}")

async def main():
    """Run all tests"""
    print("🧪 Starting Nick Agent Tests")
    print("=" * 50)
    
    # Give the server a moment to be fully ready
    print("⏳ Waiting for services to be ready...")
    await asyncio.sleep(2)
    
    # Check health first
    if not test_health_check():
        print("\n❌ Cannot proceed without a healthy agent connection")
        return
    
    # REST API tests
    test_suggestions_endpoint()
    test_chat_endpoint()
    test_history_endpoint()
    test_context_endpoint()
    
    # WebSocket test
    await test_websocket_endpoint()
    
    # Cleanup
    test_clear_history()
    
    print("\n" + "=" * 50)
    print("✨ All tests completed!")

if __name__ == "__main__":
    print("🎬 Nick Agent Test Suite")
    print("Make sure both the MCP server and Nick agent are running!")
    print("")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()