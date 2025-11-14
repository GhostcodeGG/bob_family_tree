"""Database session and engine setup."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url, echo=False, future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
