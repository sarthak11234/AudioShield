import asyncio
import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime
from app.main import app
from app.models.user import User
from app.models.task import Task
from app.core.database import engine, Base, async_session
from app.core.auth import hash_password

async def seeder():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as db:
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("password")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        task1 = Task(
            id=uuid4(),
            user_id=user.id,
            original_name="test1.wav",
            file_path="/tmp/test1.wav",
            status="completed"
        )
        task2 = Task(
            id=uuid4(),
            user_id=user.id,
            original_name="test2.wav",
            file_path="/tmp/test2.wav",
            status="failed"
        )
        db.add_all([task1, task2])
        await db.commit()
        
@pytest.mark.asyncio
async def test_vault_tasks():
    await seeder()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Login
        response = await ac.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Get tasks
        response = await ac.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        print("Vault tasks test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_vault_tasks())
