from sqlmodel import create_engine, Session
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

db_url = f"sqlite:///{BASE_DIR}/quantrun/db.sqlite3"

connect_args = {
    'check_same_thread': False
}

engine = create_engine(db_url, connect_args=connect_args)


def get_db():
    with Session(engine) as session:
        yield session