"""
Database Models and Connection
==============================

SQLite database schema for feature storage using SQLAlchemy.
"""

from pathlib import Path
from typing import Optional

from sqlalchemy import Boolean, Column, Integer, String, Text, create_engine, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.types import JSON

Base = declarative_base()


class Feature(Base):
    """Feature model representing a test case/feature to implement."""

    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    priority = Column(Integer, nullable=False, default=999, index=True)
    type = Column(String(20), nullable=False, default='feature', index=True)  # 'feature' or 'bug'
    category = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    steps = Column(JSON, nullable=False)  # Stored as JSON array
    passes = Column(Boolean, default=False, index=True)
    in_progress = Column(Boolean, default=False, index=True)
    label = Column(String(100), nullable=True, default=None, index=True)  # Wave/milestone label
    assigned_agent_id = Column(String(50), nullable=True, index=True)  # Agent working on this feature

    def to_dict(self) -> dict:
        """Convert feature to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "priority": self.priority,
            "type": self.type,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "passes": self.passes,
            "in_progress": self.in_progress,
            "label": self.label,
            "assigned_agent_id": self.assigned_agent_id,
        }


class StepProgress(Base):
    """Step-level progress tracking for features."""

    __tablename__ = "step_progress"

    id = Column(Integer, primary_key=True, index=True)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False)  # 0-based position
    step_text = Column(Text, nullable=False)  # Denormalized from Feature.steps
    completed = Column(Boolean, default=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)  # Agent's notes about the step

    __table_args__ = (
        UniqueConstraint('feature_id', 'step_index', name='_feature_step_uc'),
    )

    def to_dict(self) -> dict:
        """Convert step progress to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "feature_id": self.feature_id,
            "step_index": self.step_index,
            "step_text": self.step_text,
            "completed": self.completed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
        }


def get_database_path(project_dir: Path) -> Path:
    """Return the path to the SQLite database for a project."""
    return project_dir / "features.db"


def get_database_url(project_dir: Path) -> str:
    """Return the SQLAlchemy database URL for a project.

    Uses POSIX-style paths (forward slashes) for cross-platform compatibility.
    """
    db_path = get_database_path(project_dir)
    return f"sqlite:///{db_path.as_posix()}"


def _migrate_add_in_progress_column(engine) -> None:
    """Add in_progress column to existing databases that don't have it."""
    from sqlalchemy import text

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(features)"))
        columns = [row[1] for row in result.fetchall()]

        if "in_progress" not in columns:
            # Add the column with default value
            conn.execute(text("ALTER TABLE features ADD COLUMN in_progress BOOLEAN DEFAULT 0"))
            conn.commit()


def _migrate_add_label_column(engine) -> None:
    """Add label column to existing databases that don't have it."""
    from sqlalchemy import text

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(features)"))
        columns = [row[1] for row in result.fetchall()]

        if "label" not in columns:
            # Add the column with default NULL
            conn.execute(text("ALTER TABLE features ADD COLUMN label VARCHAR(100) DEFAULT NULL"))
            conn.commit()


def _migrate_add_type_column(engine) -> None:
    """Add type column to existing databases that don't have it."""
    from sqlalchemy import text

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(features)"))
        columns = [row[1] for row in result.fetchall()]

        if "type" not in columns:
            # Add the column with default 'feature'
            conn.execute(text("ALTER TABLE features ADD COLUMN type VARCHAR(20) DEFAULT 'feature' NOT NULL"))
            # Create index for better query performance
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_features_type ON features (type)"))
            except Exception:
                pass  # Index might already exist
            conn.commit()


def _migrate_add_assigned_agent_id_column(engine) -> None:
    """Add assigned_agent_id column to existing databases that don't have it."""
    from sqlalchemy import text

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(features)"))
        columns = [row[1] for row in result.fetchall()]

        if "assigned_agent_id" not in columns:
            # Add the column (nullable, no default)
            conn.execute(text("ALTER TABLE features ADD COLUMN assigned_agent_id VARCHAR(50)"))
            conn.commit()


def create_database(project_dir: Path) -> tuple:
    """
    Create database and return engine + session maker.

    Args:
        project_dir: Directory containing the project

    Returns:
        Tuple of (engine, SessionLocal)
    """
    from api.migration_step_progress import migrate_add_step_progress_table

    db_url = get_database_url(project_dir)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    # Migrate existing databases to add new columns
    _migrate_add_in_progress_column(engine)
    _migrate_add_label_column(engine)
    _migrate_add_type_column(engine)
    _migrate_add_assigned_agent_id_column(engine)

    # Migrate to add step_progress table
    migrate_add_step_progress_table(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


# Global session maker - will be set when server starts
_session_maker: Optional[sessionmaker] = None


def set_session_maker(session_maker: sessionmaker) -> None:
    """Set the global session maker."""
    global _session_maker
    _session_maker = session_maker


def get_db() -> Session:
    """
    Dependency for FastAPI to get database session.

    Yields a database session and ensures it's closed after use.
    """
    if _session_maker is None:
        raise RuntimeError("Database not initialized. Call set_session_maker first.")

    db = _session_maker()
    try:
        yield db
    finally:
        db.close()
