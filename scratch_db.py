import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.user import User

async def main():
    engine = create_async_engine("postgresql+asyncpg://admin:audioshield123@localhost:5433/audioshield")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Total users in DB: {len(users)}")

asyncio.run(main())
