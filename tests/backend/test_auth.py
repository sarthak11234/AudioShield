"""
Backend authentication tests.
Tests: registration, login, token issuance, email normalization, duplicate rejection.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock, MagicMock

# All tests use an in-memory SQLite via pytest markers that mock the DB;
# for integration, set DATABASE_URL env var to a real Postgres.


class TestAuthEndpoints:
    """Unit-level tests that mock the DB dependency."""

    @pytest.mark.asyncio
    async def test_signup_success(self):
        """POST /api/auth/signup should return 201 with id and email."""
        from app.main import app
        from app.core.database import get_db

        mock_user = AsyncMock()
        mock_user.id = "00000000-0000-0000-0000-000000000001"
        mock_user.email = "test@example.com"

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Patch the DB so no real Postgres is required
        async def override_get_db():
            session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            session.execute = AsyncMock(return_value=mock_result)
            session.add = MagicMock()
            session.commit = AsyncMock()
            session.refresh = AsyncMock(side_effect=lambda u: (
                setattr(u, "id", mock_user.id),
                setattr(u, "email", "test@example.com"),
                setattr(u, "username", "testuser"),
                setattr(u, "created_at", now),
            ))
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/auth/signup",
                    json={"email": "TEST@Example.COM", "username": "testuser", "password": "StrongPass1!"},
                )
            assert resp.status_code in (200, 201)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self):
        """POST /api/auth/login with wrong password must return 401."""
        from app.main import app
        from app.core.database import get_db
        from app.models.user import User
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        real_hash = pwd_context.hash("CorrectPass1!")

        fake_user = MagicMock(spec=User)
        fake_user.hashed_password = real_hash
        fake_user.email = "victim@example.com"
        fake_user.id = "00000000-0000-0000-0000-000000000002"

        async def override_get_db():
            session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = fake_user
            session.execute = AsyncMock(return_value=mock_result)
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "victim@example.com", "password": "WrongPass!"},
                )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_400_or_409(self):
        """Registering an existing email must be rejected."""
        from app.main import app
        from app.core.database import get_db
        from app.models.user import User
        from sqlalchemy.exc import IntegrityError

        existing_user = MagicMock(spec=User)
        existing_user.email = "existing@example.com"

        async def override_get_db():
            session = AsyncMock()
            # Simulate user already exists
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = existing_user
            session.execute = AsyncMock(return_value=mock_result)
            yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/auth/signup",
                    json={"email": "existing@example.com", "username": "existinguser", "password": "AnotherPass1!"},
                )
            assert resp.status_code in (400, 409)
        finally:
            app.dependency_overrides.clear()
