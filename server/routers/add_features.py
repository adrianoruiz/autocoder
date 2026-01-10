"""
Add Features Router
===================

WebSocket and REST endpoints for adding features to existing projects with AI assistance.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from ..schemas import ImageAttachment
from ..services.add_features_session import (
    AddFeaturesSession,
    create_add_features_session,
    get_add_features_session,
    list_add_features_sessions,
    remove_add_features_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/add-features", tags=["add-features"])

# Root directory
ROOT_DIR = Path(__file__).parent.parent.parent


def _get_project_path(project_name: str) -> Path:
    """Get project path from registry."""
    import sys
    root = Path(__file__).parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from registry import get_project_path
    return get_project_path(project_name)


def validate_project_name(name: str) -> bool:
    """Validate project name to prevent path traversal."""
    return bool(re.match(r'^[a-zA-Z0-9_-]{1,50}$', name))


# ============================================================================
# REST Endpoints
# ============================================================================

class AddFeaturesSessionStatus(BaseModel):
    """Status of an add features session."""
    project_name: str
    is_active: bool
    is_complete: bool
    message_count: int
    wave_label: str
    features_created: int


@router.get("/sessions", response_model=list[str])
async def list_add_features_sessions_endpoint():
    """List all active add features sessions."""
    return list_add_features_sessions()


@router.get("/sessions/{project_name}", response_model=AddFeaturesSessionStatus)
async def get_add_features_session_status(project_name: str):
    """Get status of an add features session."""
    if not validate_project_name(project_name):
        raise HTTPException(status_code=400, detail="Invalid project name")

    session = get_add_features_session(project_name)
    if not session:
        raise HTTPException(status_code=404, detail="No active session for this project")

    return AddFeaturesSessionStatus(
        project_name=project_name,
        is_active=True,
        is_complete=session.is_complete(),
        message_count=len(session.get_messages()),
        wave_label=session.get_wave_label(),
        features_created=session.features_created,
    )


@router.delete("/sessions/{project_name}")
async def cancel_add_features_session(project_name: str):
    """Cancel and remove an add features session."""
    if not validate_project_name(project_name):
        raise HTTPException(status_code=400, detail="Invalid project name")

    session = get_add_features_session(project_name)
    if not session:
        raise HTTPException(status_code=404, detail="No active session for this project")

    await remove_add_features_session(project_name)
    return {"success": True, "message": "Session cancelled"}


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/{project_name}")
async def add_features_websocket(websocket: WebSocket, project_name: str):
    """
    WebSocket endpoint for AI-assisted feature addition.

    Message protocol:

    Client -> Server:
    - {"type": "start"} - Start the add features session
    - {"type": "message", "content": "..."} - Send user message
    - {"type": "answer", "answers": {...}, "tool_id": "..."} - Answer structured question
    - {"type": "ping"} - Keep-alive ping

    Server -> Client:
    - {"type": "text", "content": "..."} - Text chunk from Claude
    - {"type": "question", "questions": [...], "tool_id": "..."} - Structured question
    - {"type": "features_created", "count": N, "label": "..."} - Features were created
    - {"type": "spec_updated", "path": "..."} - App spec was updated
    - {"type": "response_done"} - Response finished
    - {"type": "complete"} - Session complete (user clicked done)
    - {"type": "error", "content": "..."} - Error message
    - {"type": "pong"} - Keep-alive pong
    """
    if not validate_project_name(project_name):
        await websocket.close(code=4000, reason="Invalid project name")
        return

    # Look up project directory from registry
    project_dir = _get_project_path(project_name)
    if not project_dir:
        await websocket.close(code=4004, reason="Project not found in registry")
        return

    if not project_dir.exists():
        await websocket.close(code=4004, reason="Project directory not found")
        return

    await websocket.accept()

    session: Optional[AddFeaturesSession] = None

    try:
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                elif msg_type == "start":
                    # Create and start a new session
                    session = await create_add_features_session(project_name, project_dir)

                    # Stream the initial greeting
                    async for chunk in session.start():
                        await websocket.send_json(chunk)

                elif msg_type == "message":
                    # User sent a message
                    if not session:
                        session = get_add_features_session(project_name)
                        if not session:
                            await websocket.send_json({
                                "type": "error",
                                "content": "No active session. Send 'start' first."
                            })
                            continue

                    user_content = message.get("content", "").strip()
                    feature_type = message.get("feature_type", "feature")  # Extract feature type

                    # Parse attachments if present
                    attachments: list[ImageAttachment] = []
                    raw_attachments = message.get("attachments", [])
                    if raw_attachments:
                        try:
                            for raw_att in raw_attachments:
                                attachments.append(ImageAttachment(**raw_att))
                        except (ValidationError, Exception) as e:
                            logger.warning(f"Invalid attachment data: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "content": f"Invalid attachment: {str(e)}"
                            })
                            continue

                    # Allow empty content if attachments are present
                    if not user_content and not attachments:
                        await websocket.send_json({
                            "type": "error",
                            "content": "Empty message"
                        })
                        continue

                    # Prepend type context to help Claude understand intent
                    if feature_type == "bug":
                        # Add context that user wants to report bugs
                        contextual_message = f"[User wants to report bugs/issues] {user_content}" if user_content else "[User wants to report bugs/issues (see attached screenshots)]"
                    else:
                        # Default to features
                        contextual_message = user_content

                    # Stream Claude's response
                    async for chunk in session.send_message(contextual_message, attachments if attachments else None):
                        await websocket.send_json(chunk)

                elif msg_type == "answer":
                    # User answered a structured question
                    if not session:
                        session = get_add_features_session(project_name)
                        if not session:
                            await websocket.send_json({
                                "type": "error",
                                "content": "No active session"
                            })
                            continue

                    # Format the answers as a natural response
                    answers = message.get("answers", {})
                    if isinstance(answers, dict):
                        response_parts = []
                        for question_idx, answer_value in answers.items():
                            if isinstance(answer_value, list):
                                response_parts.append(", ".join(answer_value))
                            else:
                                response_parts.append(str(answer_value))
                        user_response = "; ".join(response_parts) if response_parts else "OK"
                    else:
                        user_response = str(answers)

                    # Stream Claude's response
                    async for chunk in session.send_message(user_response):
                        await websocket.send_json(chunk)

                elif msg_type == "done":
                    # User is done adding features
                    if session:
                        session.complete = True
                    await websocket.send_json({"type": "complete"})

                else:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Unknown message type: {msg_type}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON"
                })

    except WebSocketDisconnect:
        logger.info(f"Add features WebSocket disconnected for {project_name}")

    except Exception as e:
        logger.exception(f"Add features WebSocket error for {project_name}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Server error: {str(e)}"
            })
        except Exception:
            pass

    finally:
        # Don't remove the session on disconnect - allow resume
        pass
