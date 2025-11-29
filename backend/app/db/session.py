from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

# Disable verbose SQL logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

engine = create_async_engine(
    str(settings.DATABASE_URL), 
    echo=False,  # Disable SQL echo
    future=True
)

# Session maker for creating sessions outside of request context (e.g., background tasks)
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

