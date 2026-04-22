"""Create or drop all SQLAlchemy tables from models metadata."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.engine import Connection, Engine

from app.core.database import engine
from app.models import Base


def create_db_tables(bind: Engine | Connection) -> None:
    Base.metadata.create_all(bind=bind)


def drop_db_tables(bind: Engine | Connection) -> None:
    Base.metadata.drop_all(bind=bind)


def main() -> None:
    create_db_tables(bind=engine)
    print("All tables were created from SQLAlchemy metadata.")


if __name__ == "__main__":
    main()
