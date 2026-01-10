"""
Add Features Chat Session
=========================

Manages interactive chat session for adding new features to existing projects.
Uses the add-features.md skill to guide users through feature creation.
"""

import json
import logging
import os
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from ..schemas import ImageAttachment

logger = logging.getLogger(__name__)


async def _make_multimodal_message(content_blocks: list[dict]) -> AsyncGenerator[dict, None]:
    """
    Create an async generator that yields a properly formatted multimodal message.
    """
    yield {
        "type": "user",
        "message": {"role": "user", "content": content_blocks},
        "parent_tool_use_id": None,
        "session_id": "default",
    }


# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent.parent


def generate_wave_label() -> str:
    """Generate a unique wave label based on current timestamp."""
    now = datetime.now()
    return f"Wave-{now.strftime('%Y-%m-%d-%H%M')}"


class AddFeaturesSession:
    """
    Manages a feature addition conversation for an existing project.

    Provides context about existing features and guides users
    through adding new features without duplicates.
    """

    def __init__(self, project_name: str, project_dir: Path):
        """
        Initialize the session.

        Args:
            project_name: Name of the existing project
            project_dir: Absolute path to the project directory
        """
        self.project_name = project_name
        self.project_dir = project_dir
        self.client: Optional[ClaudeSDKClient] = None
        self.messages: list[dict] = []
        self.complete: bool = False
        self.created_at = datetime.now()
        self._conversation_id: Optional[str] = None
        self._client_entered: bool = False
        self.wave_label = generate_wave_label()
        self.features_created = 0

    async def close(self) -> None:
        """Clean up resources and close the Claude client."""
        if self.client and self._client_entered:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing Claude client: {e}")
            finally:
                self._client_entered = False
                self.client = None

    def _load_project_context(self) -> dict:
        """Load existing project context: spec, features, and stats."""
        context = {
            "project_name": self.project_name,
            "wave_label": self.wave_label,
            "app_spec": None,
            "features": [],
            "stats": {"total": 0, "passing": 0, "pending": 0, "in_progress": 0}
        }

        # Load app_spec.txt
        spec_path = self.project_dir / "prompts" / "app_spec.txt"
        if spec_path.exists():
            try:
                context["app_spec"] = spec_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read app_spec.txt: {e}")

        # Load features from database
        try:
            from api.database import Feature, create_database

            _, session_maker = create_database(self.project_dir)
            session = session_maker()
            try:
                features = session.query(Feature).all()
                context["features"] = [
                    {
                        "id": f.id,
                        "name": f.name,
                        "category": f.category,
                        "description": f.description,
                        "passes": f.passes,
                        "label": f.label
                    }
                    for f in features
                ]

                # Calculate stats
                context["stats"]["total"] = len(features)
                context["stats"]["passing"] = sum(1 for f in features if f.passes)
                context["stats"]["in_progress"] = sum(1 for f in features if f.in_progress)
                context["stats"]["pending"] = context["stats"]["total"] - context["stats"]["passing"] - context["stats"]["in_progress"]
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Failed to load features: {e}")

        return context

    async def start(self) -> AsyncGenerator[dict, None]:
        """
        Initialize session and get initial greeting from Claude.

        Yields message chunks as they stream in.
        """
        # Load the add-features skill
        skill_path = ROOT_DIR / ".claude" / "commands" / "add-features.md"

        if not skill_path.exists():
            yield {
                "type": "error",
                "content": f"Add features skill not found at {skill_path}"
            }
            return

        try:
            skill_content = skill_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skill_content = skill_path.read_text(encoding="utf-8", errors="replace")

        # Load project context
        context = self._load_project_context()

        # Build context section for the system prompt
        context_section = f"""
# PROJECT CONTEXT

**Project Name:** {context['project_name']}
**Wave Label:** {context['wave_label']} (use this label when creating features)

## Current Stats
- Total Features: {context['stats']['total']}
- Passing: {context['stats']['passing']}
- Pending: {context['stats']['pending']}
- In Progress: {context['stats']['in_progress']}

## Existing Features
{self._format_existing_features(context['features'])}

## App Specification
```
{context['app_spec'] or 'No app_spec.txt found'}
```

---
"""
        # Combine skill with context
        system_prompt = context_section + skill_content

        # Create security settings file
        security_settings = {
            "sandbox": {"enabled": False},
            "permissions": {
                "defaultMode": "acceptEdits",
                "allow": [
                    "Read(./**)",
                    "Write(./**)",
                    "Edit(./**)",
                    "Glob(./**)",
                ],
            },
        }
        settings_file = self.project_dir / ".claude_settings.json"
        with open(settings_file, "w") as f:
            json.dump(security_settings, f, indent=2)

        # Build MCP servers config for feature server
        mcp_servers = {
            "features": {
                "command": sys.executable,  # Use the same Python that's running this script
                "args": ["-m", "mcp_server.feature_mcp"],
                "env": {
                    # Inherit parent environment (PATH, ANTHROPIC_API_KEY, etc.)
                    **os.environ,
                    # Add custom variables
                    "PROJECT_DIR": str(self.project_dir.resolve()),
                    "PYTHONPATH": str(ROOT_DIR.resolve()),
                },
            },
        }

        # Create Claude SDK client with feature MCP server
        system_cli = shutil.which("claude")
        try:
            self.client = ClaudeSDKClient(
                options=ClaudeAgentOptions(
                    model="claude-opus-4-5-20251101",
                    cli_path=system_cli,
                    system_prompt=system_prompt,
                    allowed_tools=[
                        "Read",
                        "Write",
                        "Edit",
                        "Glob",
                        "mcp__features__feature_create_bulk",
                        "mcp__features__feature_get_existing",
                        "mcp__features__feature_get_stats",
                        "mcp__features__feature_get_labels",
                    ],
                    permission_mode="acceptEdits",
                    max_turns=100,
                    cwd=str(self.project_dir.resolve()),
                    settings=str(settings_file.resolve()),
                    mcp_servers=mcp_servers,
                )
            )
            await self.client.__aenter__()
            self._client_entered = True
        except Exception as e:
            logger.exception("Failed to create Claude client")
            yield {
                "type": "error",
                "content": f"Failed to initialize Claude: {str(e)}"
            }
            return

        # Start the conversation
        try:
            async for chunk in self._query_claude("Begin helping the user add new features."):
                yield chunk
            yield {"type": "response_done"}
        except Exception as e:
            logger.exception("Failed to start add features chat")
            yield {
                "type": "error",
                "content": f"Failed to start conversation: {str(e)}"
            }

    def _format_existing_features(self, features: list[dict]) -> str:
        """Format existing features as a readable list."""
        if not features:
            return "No existing features."

        # Group by category
        by_category: dict[str, list[dict]] = {}
        for f in features:
            cat = f.get("category", "Uncategorized")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)

        lines = []
        for category, cat_features in sorted(by_category.items()):
            lines.append(f"\n### {category}")
            for f in cat_features:
                status = "✅" if f.get("passes") else "⏳"
                label = f.get("label") or "Initial"
                lines.append(f"- {status} [{f['id']}] {f['name']} (label: {label})")

        return "\n".join(lines)

    async def send_message(
        self,
        user_message: str,
        attachments: list[ImageAttachment] | None = None
    ) -> AsyncGenerator[dict, None]:
        """
        Send user message and stream Claude's response.
        """
        if not self.client:
            yield {
                "type": "error",
                "content": "Session not initialized. Call start() first."
            }
            return

        self.messages.append({
            "role": "user",
            "content": user_message,
            "has_attachments": bool(attachments),
            "timestamp": datetime.now().isoformat()
        })

        try:
            async for chunk in self._query_claude(user_message, attachments):
                yield chunk
            yield {"type": "response_done"}
        except Exception as e:
            logger.exception("Error during Claude query")
            yield {
                "type": "error",
                "content": f"Error: {str(e)}"
            }

    async def _query_claude(
        self,
        message: str,
        attachments: list[ImageAttachment] | None = None
    ) -> AsyncGenerator[dict, None]:
        """
        Internal method to query Claude and stream responses.

        Tracks:
        - feature_create_bulk calls (features_created message)
        - Write/Edit to app_spec.txt (spec_updated message)
        """
        if not self.client:
            return

        # Build the message content
        if attachments and len(attachments) > 0:
            content_blocks = []
            if message:
                content_blocks.append({"type": "text", "text": message})
            for att in attachments:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": att.mimeType,
                        "data": att.base64Data,
                    }
                })
            await self.client.query(_make_multimodal_message(content_blocks))
            logger.info(f"Sent multimodal message with {len(attachments)} image(s)")
        else:
            await self.client.query(message)

        current_text = ""
        pending_spec_write = None  # Track app_spec.txt write

        async for msg in self.client.receive_response():
            msg_type = type(msg).__name__

            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        text = block.text
                        if text:
                            current_text += text
                            yield {"type": "text", "content": text}
                            self.messages.append({
                                "role": "assistant",
                                "content": text,
                                "timestamp": datetime.now().isoformat()
                            })

                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input = getattr(block, "input", {})
                        tool_id = getattr(block, "id", "")

                        # Track feature_create_bulk calls
                        if tool_name == "mcp__features__feature_create_bulk":
                            features_list = tool_input.get("features", [])
                            label = tool_input.get("label", self.wave_label)
                            logger.info(f"feature_create_bulk called with {len(features_list)} features, label={label}")

                        # Track app_spec.txt writes
                        if tool_name in ("Write", "Edit"):
                            file_path = tool_input.get("file_path", "")
                            if "app_spec.txt" in str(file_path):
                                pending_spec_write = {"tool_id": tool_id, "path": file_path}
                                logger.info(f"{tool_name} tool called for app_spec.txt: {file_path}")

            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__
                    if block_type == "ToolResultBlock":
                        is_error = getattr(block, "is_error", False)
                        tool_use_id = getattr(block, "tool_use_id", "")
                        content = getattr(block, "content", "")

                        if is_error:
                            logger.warning(f"Tool error: {content}")
                            if pending_spec_write and tool_use_id == pending_spec_write.get("tool_id"):
                                pending_spec_write = None
                        else:
                            # Check for successful feature_create_bulk
                            if isinstance(content, str) and "created" in content:
                                try:
                                    result = json.loads(content)
                                    if "created" in result:
                                        count = result["created"]
                                        label = result.get("label", self.wave_label)
                                        self.features_created += count
                                        logger.info(f"Created {count} features with label {label}")
                                        yield {
                                            "type": "features_created",
                                            "count": count,
                                            "label": label
                                        }
                                except json.JSONDecodeError:
                                    pass

                            # Check for successful spec write
                            if pending_spec_write and tool_use_id == pending_spec_write.get("tool_id"):
                                file_path = pending_spec_write["path"]
                                full_path = Path(file_path) if Path(file_path).is_absolute() else self.project_dir / file_path
                                if full_path.exists():
                                    logger.info(f"app_spec.txt updated at: {full_path}")
                                    yield {
                                        "type": "spec_updated",
                                        "path": str(file_path)
                                    }
                                pending_spec_write = None

    def is_complete(self) -> bool:
        """Check if feature addition is complete."""
        return self.complete

    def get_messages(self) -> list[dict]:
        """Get all messages in the conversation."""
        return self.messages.copy()

    def get_wave_label(self) -> str:
        """Get the wave label for this session."""
        return self.wave_label


# Session registry with thread safety
_sessions: dict[str, AddFeaturesSession] = {}
_sessions_lock = threading.Lock()


def get_add_features_session(project_name: str) -> Optional[AddFeaturesSession]:
    """Get an existing session for a project."""
    with _sessions_lock:
        return _sessions.get(project_name)


async def create_add_features_session(project_name: str, project_dir: Path) -> AddFeaturesSession:
    """Create a new session for a project, closing any existing one."""
    old_session: Optional[AddFeaturesSession] = None

    with _sessions_lock:
        old_session = _sessions.pop(project_name, None)
        session = AddFeaturesSession(project_name, project_dir)
        _sessions[project_name] = session

    if old_session:
        try:
            await old_session.close()
        except Exception as e:
            logger.warning(f"Error closing old session for {project_name}: {e}")

    return session


async def remove_add_features_session(project_name: str) -> None:
    """Remove and close a session."""
    session: Optional[AddFeaturesSession] = None

    with _sessions_lock:
        session = _sessions.pop(project_name, None)

    if session:
        try:
            await session.close()
        except Exception as e:
            logger.warning(f"Error closing session for {project_name}: {e}")


def list_add_features_sessions() -> list[str]:
    """List all active session project names."""
    with _sessions_lock:
        return list(_sessions.keys())


async def cleanup_all_add_features_sessions() -> None:
    """Close all active sessions. Called on server shutdown."""
    sessions_to_close: list[AddFeaturesSession] = []

    with _sessions_lock:
        sessions_to_close = list(_sessions.values())
        _sessions.clear()

    for session in sessions_to_close:
        try:
            await session.close()
        except Exception as e:
            logger.warning(f"Error closing session {session.project_name}: {e}")
