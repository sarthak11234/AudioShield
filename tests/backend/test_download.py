"""
Download endpoint security tests.
Tests: authentication required, ownership validation, status-based gating.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


class TestDownloadSecurity:

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self):
        """GET /api/download/{id} without Authorization header must return 401."""
        from app.main import app
        from httpx import AsyncClient, ASGITransport

        task_id = uuid4()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/download/{task_id}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_other_users_task_returns_404(self):
        """
        A user requesting another user's task must receive 404 (not 403)
        to prevent leaking task existence.
        """
        from app.main import app
        from app.core.database import get_db
        from app.core.auth import get_current_user
        from httpx import AsyncClient, ASGITransport

        owner_id = uuid4()
        attacker_id = uuid4()
        task_id = uuid4()

        attacker = MagicMock()
        attacker.id = attacker_id

        async def override_db():
            session = AsyncMock()
            # When queried with attacker_id, task is not found (ownership mismatch)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute = AsyncMock(return_value=mock_result)
            yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: attacker

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/download/{task_id}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_in_progress_task_returns_409(self):
        """Downloading a task that is still processing must return 409 Conflict."""
        from app.main import app
        from app.core.database import get_db
        from app.core.auth import get_current_user
        from app.models.task import Task
        from httpx import AsyncClient, ASGITransport

        user_id = uuid4()
        task_id = uuid4()

        fake_user = MagicMock()
        fake_user.id = user_id

        fake_task = MagicMock(spec=Task)
        fake_task.id = task_id
        fake_task.user_id = user_id
        fake_task.status = "processing"

        async def override_db():
            session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = fake_task
            session.execute = AsyncMock(return_value=mock_result)
            yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: fake_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/download/{task_id}")
            assert resp.status_code == 409
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_failed_task_returns_400(self):
        """Downloading a failed task must return 400."""
        from app.main import app
        from app.core.database import get_db
        from app.core.auth import get_current_user
        from app.models.task import Task
        from httpx import AsyncClient, ASGITransport

        user_id = uuid4()
        task_id = uuid4()

        fake_user = MagicMock()
        fake_user.id = user_id

        fake_task = MagicMock(spec=Task)
        fake_task.id = task_id
        fake_task.user_id = user_id
        fake_task.status = "failed"
        fake_task.error_message = "CUDA OOM"

        async def override_db():
            session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = fake_task
            session.execute = AsyncMock(return_value=mock_result)
            yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: fake_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/download/{task_id}")
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()
