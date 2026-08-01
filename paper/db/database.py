import os

from sqlmodel import create_engine, Session
from sqlmodel import SQLModel
from sqlalchemy import event
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Override with QUANTRUN_DB_PATH when running in another environment.
DATABASE_PATH = Path(os.getenv("QUANTRUN_DB_PATH", str(DATA_DIR / "paper_trading.db")))
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

db_url = f"sqlite:///{DATABASE_PATH}"

connect_args = {
    'check_same_thread': False,
    'timeout': 15  # Wait up to 15s for DB lock before throwing "database is locked"
}

# Increase pool size to handle burst of concurrent requests 
# (threads in asyncio.to_thread trying to access the DB at once)
engine = create_engine(
    db_url, 
    connect_args=connect_args,
    pool_size=20,
    max_overflow=50,
    pool_timeout=30
)

# Enable WAL mode for better concurrency in SQLite (allows concurrent reads while writing)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

# The existing trading tables are retained for compatibility. Agent tables are
# additive and are created automatically on first startup. Import all models
# here too because the hourly runner imports this module before the package
# facade has loaded them.
from paper.db import models as _models  # noqa: F401,E402

SQLModel.metadata.create_all(engine)

async def get_db():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
