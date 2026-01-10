#!/usr/bin/env python3
"""
Test bidirectional communication between server and agent.

This script simulates an agent to test the communication protocol.
"""

import asyncio
import json
import sys
import time
from datetime import datetime


def send_message(message_type: str, payload: dict) -> None:
    """Send a message to server via stdout."""
    message = {
        "type": message_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat()
    }
    message_json = json.dumps(message)
    print(f"@@MESSAGE@@{message_json}", flush=True)


def main():
    """Mock agent that responds to stdin messages."""
    print("Mock agent started")
    print("Listening for messages on stdin...")
    print()

    # Send initial chat message
    send_message("agent_chat_message", {"content": "Mock agent initialized"})

    # Send narrative
    send_message("agent_narrative", {"content": "Starting feature implementation"})

    # Simulate step progress
    send_message("step_update", {
        "feature_id": 1,
        "step_index": 0,
        "status": "started",
        "notes": "Beginning first step"
    })

    time.sleep(1)

    send_message("step_update", {
        "feature_id": 1,
        "step_index": 0,
        "status": "completed",
        "notes": "First step completed successfully"
    })

    # Regular output (not a message)
    print("This is regular output from the agent")
    print()

    # Listen for messages from server
    print("Entering stdin listen loop...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                print("EOF received, exiting")
                break

            line = line.strip()
            print(f"Received from server: {line}")

            # Check for protocol prefix
            if line.startswith("@@MESSAGE@@"):
                message_json = line[len("@@MESSAGE@@"):]
                message = json.loads(message_json)

                message_type = message.get("type")
                payload = message.get("payload", {})

                print(f"Parsed message type: {message_type}")
                print(f"Payload: {payload}")
                print()

                # Respond to ping
                if message_type == "ping":
                    send_message("pong", {})
                    print("Sent pong response")
                    print()

                # Respond to user message
                elif message_type == "user_message":
                    content = payload.get("content", "")
                    send_message("agent_chat_message", {
                        "content": f"Acknowledged: {content}"
                    })
                    print(f"Acknowledged user message: {content}")
                    print()

                # Handle command
                elif message_type == "command":
                    command = payload.get("command", "")
                    print(f"Received command: {command}")
                    print()

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
        except Exception as e:
            print(f"Error: {e}")
            break

    print("Mock agent exiting")


if __name__ == "__main__":
    main()
