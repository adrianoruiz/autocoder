#!/usr/bin/env python3
"""
Test ProcessManager bidirectional communication.

Tests that ProcessManager can:
1. Parse @@MESSAGE@@ lines from agent stdout
2. Route messages to appropriate callbacks
3. Send messages to agent via stdin
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server.services.process_manager import AgentProcessManager


async def test_communication():
    """Test bidirectional communication with mock agent."""
    print("=== Testing ProcessManager Communication ===")
    print()

    # Use current directory as project
    project_dir = Path(__file__).parent / "test_project"
    project_dir.mkdir(exist_ok=True)

    # Create features.db to prevent agent errors
    (project_dir / "features.db").touch()

    root_dir = Path(__file__).parent

    # Create process manager
    manager = AgentProcessManager(
        project_name="test",
        project_dir=project_dir,
        root_dir=root_dir,
    )

    # Storage for received messages
    received_messages = {
        "chat": [],
        "step_update": [],
        "narrative": [],
        "output": [],
    }

    # Register callbacks
    async def on_chat(payload: dict):
        print(f"[Chat Callback] {payload}")
        received_messages["chat"].append(payload)

    async def on_step_update(payload: dict):
        print(f"[Step Update Callback] {payload}")
        received_messages["step_update"].append(payload)

    async def on_narrative(payload: dict):
        print(f"[Narrative Callback] {payload}")
        received_messages["narrative"].append(payload)

    async def on_output(line: str):
        if not line.startswith("@@MESSAGE@@"):  # Only log regular output
            print(f"[Output] {line}")
            received_messages["output"].append(line)

    manager.add_chat_callback(on_chat)
    manager.add_step_update_callback(on_step_update)
    manager.add_narrative_callback(on_narrative)
    manager.add_output_callback(on_output)

    # Start mock agent (using test_communication.py as the agent)
    print("Starting mock agent...")
    # Override the command to run test_communication.py instead
    import subprocess
    manager.process = subprocess.Popen(
        [sys.executable, str(root_dir / "test_communication.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(project_dir),
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    manager.status = "running"
    manager._output_task = asyncio.create_task(manager._stream_output())

    print("Mock agent started")
    print()

    # Wait for initial messages
    await asyncio.sleep(2)

    print("\n=== Verification ===")
    print(f"Chat messages received: {len(received_messages['chat'])}")
    print(f"Step updates received: {len(received_messages['step_update'])}")
    print(f"Narratives received: {len(received_messages['narrative'])}")
    print(f"Regular output lines: {len(received_messages['output'])}")
    print()

    # Test sending message to agent
    print("Sending user message to agent...")
    success, msg = await manager.send_message_to_agent(
        "user_message",
        {"content": "Hello from server!"}
    )
    print(f"Send result: {success} - {msg}")
    print()

    # Wait for agent response
    await asyncio.sleep(1)

    # Send ping
    print("Sending ping to agent...")
    success, msg = await manager.send_message_to_agent("ping", {})
    print(f"Send result: {success} - {msg}")
    print()

    # Wait for pong
    await asyncio.sleep(1)

    # Stop agent
    print("Stopping agent...")
    if manager._output_task:
        manager._output_task.cancel()
        try:
            await manager._output_task
        except asyncio.CancelledError:
            pass

    if manager.process:
        manager.process.terminate()
        try:
            await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(None, manager.process.wait),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            manager.process.kill()

    print()
    print("=== Test Summary ===")
    print(f"✓ Chat messages: {len(received_messages['chat'])} (expected: 2+)")
    print(f"✓ Step updates: {len(received_messages['step_update'])} (expected: 2)")
    print(f"✓ Narratives: {len(received_messages['narrative'])} (expected: 1)")
    print()

    if (len(received_messages['chat']) >= 2 and
        len(received_messages['step_update']) == 2 and
        len(received_messages['narrative']) == 1):
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_communication())
    sys.exit(exit_code)
