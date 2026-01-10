"""
Database Models and Connection
==============================

SQLite database schema for feature storage using SQLAlchemy.
"""

from pathlib import Path
from typing import Optional

from sqlalchemy import Boolean, Column, Integer, String, Text, create_engine
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


def create_database(project_dir: Path) -> tuple:
    """
    Create database and return engine + session maker.

    Args:
        project_dir: Directory containing the project

    Returns:
        Tuple of (engine, SessionLocal)
    """
    db_url = get_database_url(project_dir)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    # Migrate existing databases to add new columns
    _migrate_add_in_progress_column(engine)
    _migrate_add_label_column(engine)
    _migrate_add_type_column(engine)

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
