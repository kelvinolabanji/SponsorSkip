from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class VideoSegments(Base):
    __tablename__ = "video_segments"

    video_id: Mapped[str] = mapped_column(String, primary_key=True)
    # Each item: {"start": float, "end": float, "label": str, "reason": str}
    segments: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db() -> None:
    """Create the tables if they do not exist yet."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a database session."""
    async with SessionLocal() as session:
        yield session
