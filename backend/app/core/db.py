from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """SQLite returns naive values (stored as UTC); aware ones are converted, never relabelled."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=(
    {'options': '-c timezone=UTC'} if settings.database_url.startswith('postgresql') else {}))
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """Unit of work of one HTTP request; commits before the response is sent (scope="function")."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


DB = Annotated[Session, Depends(get_db, scope='function')]
