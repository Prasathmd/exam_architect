"""Async database session for PostgreSQL."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config.settings import get_settings

Base = declarative_base()
_settings = get_settings()
Base.metadata.schema = _settings.database_schema
engine = create_async_engine(
    _settings.database_url,
    echo=False,
    connect_args={
        "server_settings": {"search_path": _settings.database_schema},
    },
)
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_settings.database_schema}"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                f"""
                ALTER TABLE IF EXISTS {_settings.database_schema}.jobs
                ADD COLUMN IF NOT EXISTS subject VARCHAR(64) DEFAULT ''
                """
            )
        )
        await conn.execute(
            text(
                f"""
                ALTER TABLE IF EXISTS {_settings.database_schema}.jobs
                ADD COLUMN IF NOT EXISTS class_name VARCHAR(32) DEFAULT ''
                """
            )
        )
        await conn.execute(
            text(
                f"""
                ALTER TABLE IF EXISTS {_settings.database_schema}.jobs
                ADD COLUMN IF NOT EXISTS term VARCHAR(32) DEFAULT ''
                """
            )
        )
        await conn.execute(
            text(
                f"""
                ALTER TABLE IF EXISTS {_settings.database_schema}.jobs
                ADD COLUMN IF NOT EXISTS uploaded_by VARCHAR(128) DEFAULT ''
                """
            )
        )
