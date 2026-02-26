import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_settings

settings = get_settings()

# For SQLite, create the data directory if it doesn't exist
if "sqlite" in settings.database_url:
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Create engine - check_same_thread=False needed for SQLite with FastAPI
connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Helps with database connection reliability
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations(engine):
    """Run manual migrations for SQLite (add new columns if they don't exist)."""
    from sqlalchemy import text, inspect

    inspector = inspect(engine)

    # Migration: Add design_type and reference_hat_path to designs table
    if 'designs' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('designs')]

        with engine.connect() as conn:
            if 'design_type' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN design_type VARCHAR(50) DEFAULT 'ai_generated' NOT NULL"
                ))
                conn.commit()
                print("Migration: Added design_type column to designs table")

            if 'reference_hat_path' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN reference_hat_path VARCHAR(500)"
                ))
                conn.commit()
                print("Migration: Added reference_hat_path column to designs table")

            if 'crown_color' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN crown_color VARCHAR(100)"
                ))
                conn.commit()
                print("Migration: Added crown_color column to designs table")

            if 'visor_color' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN visor_color VARCHAR(100)"
                ))
                conn.commit()
                print("Migration: Added visor_color column to designs table")

            if 'structure' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN structure VARCHAR(50)"
                ))
                conn.commit()
                print("Migration: Added structure column to designs table")

            if 'closure' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN closure VARCHAR(50)"
                ))
                conn.commit()
                print("Migration: Added closure column to designs table")

            if 'logo_path' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN logo_path VARCHAR(500)"
                ))
                conn.commit()
                print("Migration: Added logo_path column to designs table")

            if 'selected_version_id' not in columns:
                conn.execute(text(
                    "ALTER TABLE designs ADD COLUMN selected_version_id VARCHAR(36)"
                ))
                conn.commit()
                print("Migration: Added selected_version_id column to designs table")

    # Migration: Add batch_number and is_selected to design_versions table
    if 'design_versions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('design_versions')]

        with engine.connect() as conn:
            if 'batch_number' not in columns:
                conn.execute(text(
                    "ALTER TABLE design_versions ADD COLUMN batch_number INTEGER"
                ))
                conn.commit()
                print("Migration: Added batch_number column to design_versions table")

            if 'is_selected' not in columns:
                conn.execute(text(
                    "ALTER TABLE design_versions ADD COLUMN is_selected BOOLEAN DEFAULT 0 NOT NULL"
                ))
                conn.commit()
                print("Migration: Added is_selected column to design_versions table")


def init_db():
    """Initialize database tables."""
    from . import models  # Import models to register them
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
