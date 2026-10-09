
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def create_database_engine() -> Engine:
    """Create a SQLAlchemy engine using the configured database URL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Please configure it in the .env file."
        )

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


engine = create_database_engine()

SessionFactory = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)