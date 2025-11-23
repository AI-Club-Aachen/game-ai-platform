from collections.abc import Generator

from sqlmodel import Session

from app.db.connection import engine


def get_session() -> Generator[Session, None, None]:
    """Database session dependency"""
    with Session(engine) as session:
        yield session
