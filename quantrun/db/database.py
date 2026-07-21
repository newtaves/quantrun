from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from quantrun.config import DB_URL

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    pool_size=10,
    echo=False,
)


def init_db() -> None:
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Return a new database session."""
    return Session(engine)
