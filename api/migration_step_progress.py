"""
Step Progress Migration
=======================

Migration to create step_progress table and populate from Feature.steps JSON array.
"""

import json
from sqlalchemy import text


def migrate_add_step_progress_table(engine) -> None:
    """Create step_progress table and populate from Feature.steps JSON array.

    This migration:
    1. Checks if step_progress table already exists
    2. Creates the table if it doesn't exist
    3. Populates it from existing features with batch inserts for performance

    Args:
        engine: SQLAlchemy engine instance
    """
    from api.database import StepProgress

    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='step_progress'"
        ))
        if result.fetchone():
            print("  step_progress table already exists, skipping migration")
            return  # Already migrated

        print("  Creating step_progress table...")

        # Create table using SQLAlchemy model
        StepProgress.__table__.create(engine)

        # Populate from existing features (batch insert for performance)
        print("  Populating step_progress from Feature.steps...")
        features = conn.execute(text("SELECT id, steps FROM features")).fetchall()

        if not features:
            print("  No features found, migration complete")
            conn.commit()
            return

        batch = []
        total_steps = 0

        for feature_id, steps_json in features:
            try:
                steps = json.loads(steps_json)
                for step_index, step_text in enumerate(steps):
                    batch.append({
                        "feature_id": feature_id,
                        "step_index": step_index,
                        "step_text": step_text,
                        "completed": False,
                    })
                    total_steps += 1

                    # Insert in batches of 1000 for performance
                    if len(batch) >= 1000:
                        conn.execute(
                            text(
                                "INSERT INTO step_progress (feature_id, step_index, step_text, completed) "
                                "VALUES (:feature_id, :step_index, :step_text, :completed)"
                            ),
                            batch
                        )
                        print(f"    Inserted {len(batch)} steps (total: {total_steps})...")
                        batch = []
            except (json.JSONDecodeError, TypeError) as e:
                print(f"  Warning: Failed to parse steps for feature {feature_id}: {e}")
                continue

        # Insert remaining
        if batch:
            conn.execute(
                text(
                    "INSERT INTO step_progress (feature_id, step_index, step_text, completed) "
                    "VALUES (:feature_id, :step_index, :step_text, :completed)"
                ),
                batch
            )

        conn.commit()
        print(f"  Migration complete: created step_progress table with {total_steps} steps from {len(features)} features")
