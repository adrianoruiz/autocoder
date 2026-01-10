"""
Agent Communication Layer
==========================

Bidirectional communication system for agent-server interaction via stdin/stdout.

Protocol:
- Messages use format: @@MESSAGE@@<JSON>
- Server → Agent: stdin writes
- Agent → Server: stdout writes with @@MESSAGE@@ prefix
"""

import json
import queue
import sys
import threading
from datetime import datetime
from typing import Any, Callable


class AgentCommunicator:
    """
    Manages bidirectional communication between agent and server.

    Features:
    - Stdin listener thread for receiving messages from server
    - Message sender for outgoing messages via stdout
    - Callback system for handling incoming messages
    """

    def __init__(self):
        """Initialize the communicator."""
        self.running = False
        self.listener_thread: threading.Thread | None = None
        self.callbacks: dict[str, list[Callable]] = {
            "user_message": [],
            "command": [],
            "ping": [],
        }

    def register_callback(self, message_type: str, callback: Callable) -> None:
        """
        Register a callback for a specific message type.

        Args:
            message_type: Type of message to handle (e.g., "user_message", "command")
            callback: Function to call when message received
        """
        if message_type not in self.callbacks:
            self.callbacks[message_type] = []
        self.callbacks[message_type].append(callback)

    def send_message(self, message_type: str, payload: dict[str, Any]) -> None:
        """
        Send a message to the server via stdout.

        Args:
            message_type: Type of message (e.g., "agent_chat_message", "step_update")
            payload: Message payload data
        """
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Write to stdout with protocol prefix
        message_json = json.dumps(message)
        print(f"@@MESSAGE@@{message_json}", flush=True)

    def send_chat_message(self, content: str) -> None:
        """
        Send a chat message to the server.

        Args:
            content: The message content
        """
        self.send_message("agent_chat_message", {"content": content})

    def send_step_update(
        self,
        feature_id: int,
        step_index: int,
        status: str,
        notes: str = ""
    ) -> None:
        """
        Send a step progress update to the server.

        Args:
            feature_id: ID of the feature
            step_index: Index of the step (0-based)
            status: "started" or "completed"
            notes: Optional notes about the step
        """
        self.send_message("step_update", {
            "feature_id": feature_id,
            "step_index": step_index,
            "status": status,
            "notes": notes
        })

    def send_narrative(self, content: str) -> None:
        """
        Send a narrative/thinking update to the server.

        Args:
            content: The narrative text
        """
        self.send_message("agent_narrative", {"content": content})

    def send_pong(self) -> None:
        """Send a pong response to keep connection alive."""
        self.send_message("pong", {})

    def _listen_stdin(self) -> None:
        """
        Listen for messages on stdin (runs in separate thread).

        Reads lines from stdin and processes messages in format:
        @@MESSAGE@@<JSON>
        """
        while self.running:
            try:
                # Read line from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()

                # Check for protocol prefix
                if not line.startswith("@@MESSAGE@@"):
                    continue

                # Extract JSON payload
                message_json = line[len("@@MESSAGE@@"):]
                message = json.loads(message_json)

                # Validate message structure
                if "type" not in message or "payload" not in message:
                    continue

                message_type = message["type"]
                payload = message["payload"]

                # Execute callbacks for this message type
                if message_type in self.callbacks:
                    for callback in self.callbacks[message_type]:
                        try:
                            callback(payload)
                        except Exception as e:
                            # Log error but continue processing
                            print(f"Error in callback for {message_type}: {e}", file=sys.stderr)

            except json.JSONDecodeError:
                # Ignore malformed JSON
                continue
            except Exception as e:
                # Log unexpected errors
                print(f"Error in stdin listener: {e}", file=sys.stderr)

    def start(self) -> None:
        """Start the stdin listener thread."""
        if self.running:
            return

        self.running = True
        self.listener_thread = threading.Thread(target=self._listen_stdin, daemon=True)
        self.listener_thread.start()

    def stop(self) -> None:
        """Stop the stdin listener thread."""
        self.running = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1.0)
