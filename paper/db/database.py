from sqlmodel import create_engine, Session
from sqlalchemy import event
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

db_url = f"sqlite:///{BASE_DIR}/quantrun/db.sqlite3"

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

async def get_db():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()