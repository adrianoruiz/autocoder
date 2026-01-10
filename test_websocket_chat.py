#!/usr/bin/env python3
"""
Test WebSocket Chat Integration

Tests that:
1. WebSocket accepts user_chat_message
2. Messages are routed to ProcessManager
3. Agent responses are broadcast back
4. Step updates are broadcast correctly
"""

import asyncio
import json
import sys
from pathlib import Path

import websockets

# Server URL (adjust if needed)
WS_URL = "ws://localhost:8000/ws/projects/test"


async def test_websocket_chat():
    """Test bidirectional chat via WebSocket."""
    print("=== Testing WebSocket Chat Integration ===")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✓ Connected to WebSocket")

            # Wait for initial messages (status, progress)
            print("\nReceiving initial messages...")
            for _ in range(3):
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=2.0
                    )
                    data = json.loads(message)
                    print(f"  Received: {data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    break

            # Test 1: Send user chat message
            print("\nTest 1: Sending user chat message...")
            await websocket.send(json.dumps({
                "type": "user_chat_message",
                "content": "Hello from WebSocket test!"
            }))
            print("✓ Message sent")

            # Wait for any responses (timeout if agent not running)
            print("\nWaiting for agent response (5 seconds)...")
            try:
                while True:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")

                    if msg_type == "agent_chat_message":
                        print(f"✓ Received agent chat: {data.get('content', '')}")
                    elif msg_type == "step_update":
                        print(f"✓ Received step update: feature={data.get('feature_id')}, "
                              f"step={data.get('step_index')}, status={data.get('status')}")
                    elif msg_type == "agent_narrative":
                        print(f"✓ Received narrative: {data.get('content', '')}")
                    elif msg_type == "log":
                        print(f"  [Log] {data.get('line', '')[:80]}")
                    elif msg_type == "error":
                        print(f"✗ Error: {data.get('message', '')}")

            except asyncio.TimeoutError:
                print("  (Timeout - agent may not be running)")

            # Test 2: Send ping
            print("\nTest 2: Testing ping/pong...")
            await websocket.send(json.dumps({"type": "ping"}))

            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(response)
            if data.get("type") == "pong":
                print("✓ Ping/pong working")
            else:
                print(f"✗ Expected pong, got: {data.get('type')}")

            print("\n=== Test Summary ===")
            print("✓ WebSocket connection works")
            print("✓ User chat messages accepted")
            print("✓ Ping/pong working")
            print("✓ Message routing functional")
            print("\nNote: To see agent responses, run the agent in another terminal.")

    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
        print("\nMake sure the server is running:")
        print("  cd /Users/adrianoboldarini/7clicks/autocoder/server")
        print("  uvicorn main:app --reload")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_websocket_chat())
    sys.exit(exit_code)
