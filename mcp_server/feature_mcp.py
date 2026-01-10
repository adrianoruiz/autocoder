#!/usr/bin/env python3
"""
MCP Server for Feature Management
==================================

Provides tools to manage features in the autonomous coding system,
replacing the previous FastAPI-based REST API.

Tools:
- feature_get_stats: Get progress statistics
- feature_get_next: Get next feature to implement
- feature_get_for_regression: Get random passing features for testing
- feature_mark_passing: Mark a feature as passing
- feature_skip: Skip a feature (move to end of queue)
- feature_mark_in_progress: Mark a feature as in-progress
- feature_clear_in_progress: Clear in-progress status
- feature_create_bulk: Create multiple features at once (with optional label)
- feature_get_existing: Get existing features to avoid duplicates
- feature_get_labels: Get all unique labels/milestones with counts
"""

import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from sqlalchemy.sql.expression import func

# Add parent directory to path so we can import from api module
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import Feature, StepProgress, create_database
from api.migration import migrate_json_to_sqlite

# Configuration from environment
PROJECT_DIR = Path(os.environ.get("PROJECT_DIR", ".")).resolve()


# Pydantic models for input validation
class MarkPassingInput(BaseModel):
    """Input for marking a feature as passing."""
    feature_id: int = Field(..., description="The ID of the feature to mark as passing", ge=1)


class SkipFeatureInput(BaseModel):
    """Input for skipping a feature."""
    feature_id: int = Field(..., description="The ID of the feature to skip", ge=1)


class MarkInProgressInput(BaseModel):
    """Input for marking a feature as in-progress."""
    feature_id: int = Field(..., description="The ID of the feature to mark as in-progress", ge=1)


class ClearInProgressInput(BaseModel):
    """Input for clearing in-progress status."""
    feature_id: int = Field(..., description="The ID of the feature to clear in-progress status", ge=1)


class RegressionInput(BaseModel):
    """Input for getting regression features."""
    limit: int = Field(default=3, ge=1, le=10, description="Maximum number of passing features to return")


class FeatureCreateItem(BaseModel):
    """Schema for creating a single feature."""
    type: str = Field(default="feature", description="Feature type: 'feature' or 'bug'")
    category: str = Field(..., min_length=1, max_length=100, description="Feature category")
    name: str = Field(..., min_length=1, max_length=255, description="Feature name")
    description: str = Field(..., min_length=1, description="Detailed description")
    steps: list[str] = Field(..., min_length=1, description="Implementation/test steps")


class BulkCreateInput(BaseModel):
    """Input for bulk creating features."""
    features: list[FeatureCreateItem] = Field(..., min_length=1, description="List of features to create")


class FeatureUpdateInput(BaseModel):
    """Input for updating a feature."""
    feature_id: int = Field(..., description="The ID of the feature to update", ge=1)
    category: str | None = Field(None, min_length=1, max_length=100, description="Feature category")
    name: str | None = Field(None, min_length=1, max_length=255, description="Feature name")
    description: str | None = Field(None, min_length=1, description="Detailed description")
    steps: list[str] | None = Field(None, min_length=1, description="Implementation/test steps")


class FeatureDeleteInput(BaseModel):
    """Input for deleting a feature."""
    feature_id: int = Field(..., description="The ID of the feature to delete", ge=1)


# Global database session maker (initialized on startup)
_session_maker = None
_engine = None


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Initialize database on startup, cleanup on shutdown."""
    global _session_maker, _engine

    # Create project directory if it doesn't exist
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    _engine, _session_maker = create_database(PROJECT_DIR)

    # Run migration if needed (converts legacy JSON to SQLite)
    migrate_json_to_sqlite(PROJECT_DIR, _session_maker)

    yield

    # Cleanup
    if _engine:
        _engine.dispose()


# Initialize the MCP server
mcp = FastMCP("features", lifespan=server_lifespan)


def get_session():
    """Get a new database session."""
    if _session_maker is None:
        raise RuntimeError("Database not initialized")
    return _session_maker()


@mcp.tool()
def feature_get_stats() -> str:
    """Get statistics about feature completion progress.

    Returns the number of passing features, in-progress features, total features,
    and completion percentage. Use this to track overall progress of the implementation.

    Returns:
        JSON with: passing (int), in_progress (int), total (int), percentage (float)
    """
    session = get_session()
    try:
        total = session.query(Feature).count()
        passing = session.query(Feature).filter(Feature.passes == True).count()
        in_progress = session.query(Feature).filter(Feature.in_progress == True).count()
        percentage = round((passing / total) * 100, 1) if total > 0 else 0.0

        return json.dumps({
            "passing": passing,
            "in_progress": in_progress,
            "total": total,
            "percentage": percentage
        }, indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_get_next(
    agent_id: Annotated[str, Field(default="", description="Optional agent ID to filter out features being worked on by other agents")] = ""
) -> str:
    """Get the highest-priority pending feature to work on.

    Returns the feature with the lowest priority number that has passes=false
    and is not currently being worked on by another agent.
    Use this at the start of each coding session to determine what to implement next.

    NOTE: In parallel agent mode (AGENT_ID env var set), this automatically claims
    the feature to prevent race conditions with other agents.

    Args:
        agent_id: Optional agent ID. If provided, excludes features assigned to other agents.
                  Auto-detected from AGENT_ID environment variable if not provided.

    Returns:
        JSON with feature details (id, priority, category, name, description, steps, passes, in_progress, assigned_agent_id)
        or error message if all features are passing or assigned.
    """
    # Auto-detect agent_id from environment if not provided
    if not agent_id:
        agent_id = os.environ.get("AGENT_ID", "")

    session = get_session()
    try:
        query = session.query(Feature).filter(Feature.passes == False)

        # If agent_id provided, exclude features assigned to other agents
        if agent_id:
            query = query.filter(
                (Feature.assigned_agent_id == None) |
                (Feature.assigned_agent_id == agent_id)
            )

        feature = query.order_by(Feature.priority.asc(), Feature.id.asc()).first()

        if feature is None:
            return json.dumps({"error": "All features are passing or assigned to other agents! No more work to do."})

        # In parallel mode, automatically claim the feature to prevent race conditions
        if agent_id and not feature.in_progress:
            feature.in_progress = True
            feature.assigned_agent_id = agent_id
            session.commit()
            session.refresh(feature)

        return json.dumps(feature.to_dict(), indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_get_for_regression(
    limit: Annotated[int, Field(default=3, ge=1, le=10, description="Maximum number of passing features to return")] = 3
) -> str:
    """Get random passing features for regression testing.

    Returns a random selection of features that are currently passing.
    Use this to verify that previously implemented features still work
    after making changes.

    NOTE: This tool is disabled in YOLO mode. In YOLO mode, regression testing
    is skipped for faster prototyping.

    Args:
        limit: Maximum number of features to return (1-10, default 3)

    Returns:
        JSON with: features (list of feature objects), count (int)
        or error if called in YOLO mode
    """
    # Check if YOLO mode is enabled (the tool should be blocked by client.py in YOLO mode,
    # but we add a defense-in-depth check here as well)
    yolo_mode = os.environ.get("YOLO_MODE", "").lower() == "true"
    if yolo_mode:
        return json.dumps({
            "error": "Regression testing is disabled in YOLO mode",
            "features": [],
            "count": 0
        }, indent=2)

    session = get_session()
    try:
        features = (
            session.query(Feature)
            .filter(Feature.passes == True)
            .order_by(func.random())
            .limit(limit)
            .all()
        )

        return json.dumps({
            "features": [f.to_dict() for f in features],
            "count": len(features)
        }, indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_mark_passing(
    feature_id: Annotated[int, Field(description="The ID of the feature to mark as passing", ge=1)]
) -> str:
    """Mark a feature as passing after successful implementation.

    Updates the feature's passes field to true and clears the in_progress flag
    and agent assignment. Use this after you have implemented the feature and
    verified it works correctly.

    Args:
        feature_id: The ID of the feature to mark as passing

    Returns:
        JSON with the updated feature details, or error if not found.
    """
    session = get_session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()

        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        feature.passes = True
        feature.in_progress = False
        feature.assigned_agent_id = None  # Clear agent assignment on completion
        session.commit()
        session.refresh(feature)

        return json.dumps(feature.to_dict(), indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_skip(
    feature_id: Annotated[int, Field(description="The ID of the feature to skip", ge=1)]
) -> str:
    """Skip a feature by moving it to the end of the priority queue.

    Use this when a feature cannot be implemented yet due to:
    - Dependencies on other features that aren't implemented yet
    - External blockers (missing assets, unclear requirements)
    - Technical prerequisites that need to be addressed first

    The feature's priority is set to max_priority + 1, so it will be
    worked on after all other pending features. Also clears the in_progress
    flag so the feature returns to "pending" status.

    Args:
        feature_id: The ID of the feature to skip

    Returns:
        JSON with skip details: id, name, old_priority, new_priority, message
    """
    session = get_session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()

        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        if feature.passes:
            return json.dumps({"error": "Cannot skip a feature that is already passing"})

        old_priority = feature.priority

        # Get max priority and set this feature to max + 1
        max_priority_result = session.query(Feature.priority).order_by(Feature.priority.desc()).first()
        new_priority = (max_priority_result[0] + 1) if max_priority_result else 1

        feature.priority = new_priority
        feature.in_progress = False
        session.commit()
        session.refresh(feature)

        return json.dumps({
            "id": feature.id,
            "name": feature.name,
            "old_priority": old_priority,
            "new_priority": new_priority,
            "message": f"Feature '{feature.name}' moved to end of queue"
        }, indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_mark_in_progress(
    feature_id: Annotated[int, Field(description="The ID of the feature to mark as in-progress", ge=1)],
    agent_id: Annotated[str, Field(default="", description="Optional agent ID to assign this feature to")] = ""
) -> str:
    """Mark a feature as in-progress. Call immediately after feature_get_next().

    This prevents other agent sessions from working on the same feature.
    Use this as soon as you retrieve a feature to work on.

    Args:
        feature_id: The ID of the feature to mark as in-progress
        agent_id: Optional agent ID to assign this feature to

    Returns:
        JSON with the updated feature details, or error if not found or already in-progress by another agent.
    """
    session = get_session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()

        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        if feature.passes:
            return json.dumps({"error": f"Feature with ID {feature_id} is already passing"})

        # Check if already in progress by another agent
        if feature.in_progress and feature.assigned_agent_id and agent_id:
            if feature.assigned_agent_id != agent_id:
                return json.dumps({
                    "error": f"Feature with ID {feature_id} is already in-progress by agent {feature.assigned_agent_id}"
                })

        feature.in_progress = True
        if agent_id:
            feature.assigned_agent_id = agent_id
        session.commit()
        session.refresh(feature)

        return json.dumps(feature.to_dict(), indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_clear_in_progress(
    feature_id: Annotated[int, Field(description="The ID of the feature to clear in-progress status", ge=1)]
) -> str:
    """Clear in-progress status from a feature.

    Use this when abandoning a feature or manually unsticking a stuck feature.
    The feature will return to the pending queue.

    Args:
        feature_id: The ID of the feature to clear in-progress status

    Returns:
        JSON with the updated feature details, or error if not found.
    """
    session = get_session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()

        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        feature.in_progress = False
        feature.assigned_agent_id = None
        session.commit()
        session.refresh(feature)

        return json.dumps(feature.to_dict(), indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_claim_next(
    agent_id: Annotated[str, Field(description="The agent ID claiming the feature")]
) -> str:
    """Atomically get and claim the next available feature for an agent.

    This is the preferred method for parallel agents to avoid race conditions.
    It combines feature_get_next and feature_mark_in_progress into a single
    atomic operation.

    Args:
        agent_id: The agent ID claiming the feature

    Returns:
        JSON with the claimed feature details, or error if no features available.
    """
    session = get_session()
    try:
        # Find the next available feature not assigned to another agent
        # A feature is available if:
        # 1. Not in progress AND not assigned to anyone, OR
        # 2. Already assigned to this agent (allow re-claiming own feature)
        feature = (
            session.query(Feature)
            .filter(Feature.passes == False)
            .filter(
                ((Feature.in_progress == False) & (Feature.assigned_agent_id == None)) |
                (Feature.assigned_agent_id == agent_id)
            )
            .order_by(Feature.priority.asc(), Feature.id.asc())
            .with_for_update()  # Lock the row
            .first()
        )

        if feature is None:
            return json.dumps({"error": "No features available to claim. All are passing or assigned."})

        # Claim the feature
        feature.in_progress = True
        feature.assigned_agent_id = agent_id
        session.commit()
        session.refresh(feature)

        return json.dumps(feature.to_dict(), indent=2)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": f"Failed to claim feature: {str(e)}"})
    finally:
        session.close()


@mcp.tool()
def feature_release(
    feature_id: Annotated[int, Field(description="The ID of the feature to release", ge=1)],
    agent_id: Annotated[str, Field(default="", description="The agent ID releasing the feature")] = ""
) -> str:
    """Release a feature back to the queue without marking it as passing.

    Use this when an agent needs to stop working on a feature but hasn't
    completed it. The feature will be available for other agents to claim.

    Args:
        feature_id: The ID of the feature to release
        agent_id: Optional agent ID for verification

    Returns:
        JSON with the updated feature details, or error if not found.
    """
    session = get_session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()

        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        # Only release if the agent owns it or no agent specified
        if agent_id and feature.assigned_agent_id and feature.assigned_agent_id != agent_id:
            return json.dumps({
                "error": f"Feature is assigned to agent {feature.assigned_agent_id}, not {agent_id}"
            })

        feature.in_progress = False
        feature.assigned_agent_id = None
        session.commit()
        session.refresh(feature)

        return json.dumps({
            "released": True,
            "feature": feature.to_dict(),
            "message": f"Feature '{feature.name}' released back to queue"
        }, indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_create_bulk(
    features: Annotated[list[dict], Field(description="List of features to create, each with category, name, description, and steps")],
    label: Annotated[str | None, Field(default=None, description="Optional label/milestone for grouping features (e.g., 'Wave-2024-01-10-1430')")] = None
) -> str:
    """Create multiple features in a single operation.

    Features are assigned sequential priorities based on their order.
    All features start with passes=false.

    This is typically used by the initializer agent to set up the initial
    feature list from the app specification, or by the add-features assistant
    to add new features to an existing project.

    Args:
        features: List of features to create, each with:
            - type (str, optional): 'feature' or 'bug' (defaults to 'feature')
            - category (str): Feature category
            - name (str): Feature name
            - description (str): Detailed description
            - steps (list[str]): Implementation/test steps
        label: Optional label/milestone for grouping features (e.g., 'Wave-2024-01-10-1430')

    Returns:
        JSON with: created (int) - number of features created, label (str|null)
    """
    session = get_session()
    try:
        # Get the starting priority
        max_priority_result = session.query(Feature.priority).order_by(Feature.priority.desc()).first()
        start_priority = (max_priority_result[0] + 1) if max_priority_result else 1

        created_count = 0
        for i, feature_data in enumerate(features):
            # Validate required fields
            if not all(key in feature_data for key in ["category", "name", "description", "steps"]):
                return json.dumps({
                    "error": f"Feature at index {i} missing required fields (category, name, description, steps)"
                })

            # Get type from feature_data, default to 'feature'
            feature_type = feature_data.get("type", "feature")

            # Calculate priority with boost for bugs
            base_priority = start_priority + i
            if feature_type == "bug":
                priority = base_priority - 500  # Bugs get higher priority (lower number)
            else:
                priority = base_priority

            db_feature = Feature(
                priority=priority,
                type=feature_type,
                category=feature_data["category"],
                name=feature_data["name"],
                description=feature_data["description"],
                steps=feature_data["steps"],
                passes=False,
                label=label,
            )
            session.add(db_feature)
            created_count += 1

        session.commit()

        return json.dumps({"created": created_count, "label": label}, indent=2)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        session.close()


@mcp.tool()
def feature_get_existing() -> str:
    """Get all existing feature names to avoid creating duplicates.

    Returns a list of all feature names currently in the database.
    Use this before creating new features to check for duplicates.

    Returns:
        JSON with: features (list of {id, name, category, label, passes})
    """
    session = get_session()
    try:
        features = session.query(Feature).all()
        return json.dumps({
            "features": [
                {
                    "id": f.id,
                    "name": f.name,
                    "category": f.category,
                    "label": f.label,
                    "passes": f.passes
                }
                for f in features
            ],
            "count": len(features)
        }, indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_get_labels() -> str:
    """Get all unique labels/milestones with their feature counts.

    Returns:
        JSON with: labels (list of {label, count, passing, pending, in_progress})
    """
    session = get_session()
    try:
        # Get all features grouped by label
        features = session.query(Feature).all()

        label_stats: dict[str | None, dict] = {}
        for f in features:
            label_key = f.label  # None for "Initial"
            if label_key not in label_stats:
                label_stats[label_key] = {
                    "label": label_key,
                    "count": 0,
                    "passing": 0,
                    "pending": 0,
                    "in_progress": 0
                }

            label_stats[label_key]["count"] += 1
            if f.passes:
                label_stats[label_key]["passing"] += 1
            elif f.in_progress:
                label_stats[label_key]["in_progress"] += 1
            else:
                label_stats[label_key]["pending"] += 1

        # Sort: None (Initial) first, then by label name
        sorted_labels = sorted(
            label_stats.values(),
            key=lambda x: (x["label"] is not None, x["label"] or "")
        )

        return json.dumps({"labels": sorted_labels}, indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_create(
    category: Annotated[str, Field(description="Feature category", min_length=1, max_length=100)],
    name: Annotated[str, Field(description="Feature name", min_length=1, max_length=255)],
    description: Annotated[str, Field(description="Detailed description", min_length=1)],
    steps: Annotated[list[str], Field(description="Implementation/test steps", min_length=1)],
    type: Annotated[str, Field(default="feature", description="Feature type: 'feature' or 'bug'")] = "feature"
) -> str:
    """Create a single feature.

    Creates a new feature with the provided details. The feature is assigned
    a priority based on the current maximum priority in the database.

    Args:
        category: Feature category (e.g., "Authentication", "UI")
        name: Feature name (e.g., "Add login button")
        description: Detailed description of the feature
        steps: List of implementation/test steps
        type: Feature type ('feature' or 'bug')

    Returns:
        JSON with the created feature details, or error if creation failed.
    """
    session = get_session()
    try:
        # Get next priority
        max_priority_result = session.query(Feature.priority).order_by(Feature.priority.desc()).first()
        priority = (max_priority_result[0] + 1) if max_priority_result else 1

        # Apply priority boost for bugs
        if type == "bug":
            priority -= 500

        db_feature = Feature(
            priority=priority,
            type=type,
            category=category,
            name=name,
            description=description,
            steps=steps,
            passes=False,
        )

        session.add(db_feature)
        session.commit()
        session.refresh(db_feature)

        return json.dumps(db_feature.to_dict(), indent=2)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        session.close()


@mcp.tool()
def feature_update(
    feature_id: Annotated[int, Field(description="The ID of the feature to update", ge=1)],
    category: Annotated[str | None, Field(default=None, description="Feature category", min_length=1, max_length=100)] = None,
    name: Annotated[str | None, Field(default=None, description="Feature name", min_length=1, max_length=255)] = None,
    description: Annotated[str | None, Field(default=None, description="Detailed description", min_length=1)] = None,
    steps: Annotated[list[str] | None, Field(default=None, description="Implementation/test steps", min_length=1)] = None
) -> str:
    """Update a feature's editable fields.

    Updates one or more fields of an existing feature. All fields are optional -
    only provided fields will be updated. This allows partial updates.

    Args:
        feature_id: The ID of the feature to update
        category: New category (optional)
        name: New name (optional)
        description: New description (optional)
        steps: New list of steps (optional)

    Returns:
        JSON with the updated feature details, or error if not found.
    """
    session = get_session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()

        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        # Apply partial updates
        if category is not None:
            feature.category = category
        if name is not None:
            feature.name = name
        if description is not None:
            feature.description = description
        if steps is not None:
            feature.steps = steps

        session.commit()
        session.refresh(feature)

        return json.dumps(feature.to_dict(), indent=2)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        session.close()


@mcp.tool()
def feature_delete(
    feature_id: Annotated[int, Field(description="The ID of the feature to delete", ge=1)]
) -> str:
    """Delete a feature from backlog tracking.

    Removes a feature from the database. Note that if the feature has already
    been implemented (passes=true), the associated code will remain in the codebase.
    This tool only removes the feature from backlog tracking.

    If you need to remove completed feature code, create a new feature describing
    the removal work instead of using this tool.

    Args:
        feature_id: The ID of the feature to delete

    Returns:
        JSON with success message, or error if not found.
    """
    session = get_session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()

        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        feature_name = feature.name
        was_passing = feature.passes

        session.delete(feature)
        session.commit()

        result = {
            "success": True,
            "message": f"Feature '{feature_name}' deleted from backlog"
        }

        if was_passing:
            result["note"] = "Feature was marked passing - code remains in codebase. Create a removal feature if code cleanup is needed."

        return json.dumps(result, indent=2)
    except Exception as e:
        session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        session.close()


@mcp.tool()
def feature_step_mark_started(
    feature_id: Annotated[int, Field(description="The ID of the feature", ge=1)],
    step_index: Annotated[int, Field(description="The 0-based index of the step to mark as started", ge=0)]
) -> str:
    """Mark a specific step as started with a timestamp.

    Records when a step begins execution by setting the started_at timestamp.
    This allows tracking which step is currently being worked on.

    Args:
        feature_id: The ID of the feature containing the step
        step_index: The 0-based index of the step within the feature

    Returns:
        JSON with the updated step progress details, or error if not found.
    """
    session = get_session()
    try:
        step = (
            session.query(StepProgress)
            .filter(
                StepProgress.feature_id == feature_id,
                StepProgress.step_index == step_index
            )
            .first()
        )

        if step is None:
            return json.dumps({
                "error": f"Step {step_index} for feature {feature_id} not found"
            })

        step.started_at = datetime.utcnow()
        session.commit()
        session.refresh(step)

        return json.dumps(step.to_dict(), indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_step_mark_completed(
    feature_id: Annotated[int, Field(description="The ID of the feature", ge=1)],
    step_index: Annotated[int, Field(description="The 0-based index of the step to mark as completed", ge=0)],
    notes: Annotated[str | None, Field(default=None, description="Optional notes about the step completion")] = None
) -> str:
    """Mark a specific step as completed with a timestamp and optional notes.

    Records when a step is finished by setting completed=True, completed_at timestamp,
    and optionally storing notes about the implementation.

    Args:
        feature_id: The ID of the feature containing the step
        step_index: The 0-based index of the step within the feature
        notes: Optional notes about how the step was completed

    Returns:
        JSON with the updated step progress details, or error if not found.
    """
    session = get_session()
    try:
        step = (
            session.query(StepProgress)
            .filter(
                StepProgress.feature_id == feature_id,
                StepProgress.step_index == step_index
            )
            .first()
        )

        if step is None:
            return json.dumps({
                "error": f"Step {step_index} for feature {feature_id} not found"
            })

        step.completed = True
        step.completed_at = datetime.utcnow()
        if notes:
            step.notes = notes
        session.commit()
        session.refresh(step)

        return json.dumps(step.to_dict(), indent=2)
    finally:
        session.close()


@mcp.tool()
def feature_get_progress_details(
    feature_id: Annotated[int, Field(description="The ID of the feature to get progress details for", ge=1)]
) -> str:
    """Get detailed step-by-step progress for a feature.

    Returns all step progress records for a feature, including completion status,
    timestamps, and notes. Also includes summary statistics.

    Args:
        feature_id: The ID of the feature to get progress details for

    Returns:
        JSON with:
        - steps: List of step progress objects with status and timestamps
        - total_steps: Total number of steps in the feature
        - completed_steps: Number of completed steps
        - in_progress_steps: Number of steps that have started but not completed
        - pending_steps: Number of steps not yet started
        Or error if feature not found.
    """
    session = get_session()
    try:
        # Verify feature exists
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if feature is None:
            return json.dumps({"error": f"Feature with ID {feature_id} not found"})

        # Get all steps for this feature, ordered by step_index
        steps = (
            session.query(StepProgress)
            .filter(StepProgress.feature_id == feature_id)
            .order_by(StepProgress.step_index)
            .all()
        )

        # Calculate statistics
        total_steps = len(steps)
        completed_steps = sum(1 for s in steps if s.completed)
        in_progress_steps = sum(1 for s in steps if s.started_at and not s.completed)
        pending_steps = sum(1 for s in steps if not s.started_at)

        return json.dumps({
            "feature_id": feature_id,
            "feature_name": feature.name,
            "steps": [s.to_dict() for s in steps],
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "in_progress_steps": in_progress_steps,
            "pending_steps": pending_steps
        }, indent=2)
    finally:
        session.close()


if __name__ == "__main__":
    mcp.run()
