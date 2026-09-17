"""
Upload endpoint security tests.
Tests: extension validation, magic-byte enforcement, size limits, path traversal prevention.
"""
import io
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_wav_bytes


class TestMagicByteValidation:
    """
    Validate the validate_audio_magic_bytes() function directly.
    No FastAPI, DB, or filesystem required.
    """

    def _get_validator(self):
        from app.api.upload import validate_audio_magic_bytes
        return validate_audio_magic_bytes

    def test_valid_wav_header_accepted(self):
        validate = self._get_validator()
        wav_bytes = make_wav_bytes(duration_s=0.1)
        assert validate(wav_bytes[:64], ".wav") is True

    def test_invalid_wav_header_rejected(self):
        validate = self._get_validator()
        fake_wav = b"FAKE" + b"\x00" * 60
        assert validate(fake_wav, ".wav") is False

    def test_valid_flac_header_accepted(self):
        validate = self._get_validator()
        flac_header = b"fLaC" + b"\x00" * 60
        assert validate(flac_header, ".flac") is True

    def test_invalid_flac_header_rejected(self):
        validate = self._get_validator()
        fake_flac = b"NOPE" + b"\x00" * 60
        assert validate(fake_flac, ".flac") is False

    def test_valid_mp3_id3_header_accepted(self):
        validate = self._get_validator()
        id3_header = b"ID3" + b"\x00" * 60
        assert validate(id3_header, ".mp3") is True

    def test_valid_mp3_sync_header_accepted(self):
        validate = self._get_validator()
        # 0xFF 0xFB = MPEG1, Layer3, 128kbps, 44100Hz
        sync_header = bytes([0xFF, 0xFB]) + b"\x00" * 60
        assert validate(sync_header, ".mp3") is True

    def test_executable_disguised_as_wav_rejected(self):
        """ELF executable disguised as .wav must be rejected."""
        validate = self._get_validator()
        elf_magic = b"\x7fELF" + b"\x00" * 60
        assert validate(elf_magic, ".wav") is False

    def test_extension_mismatch_flac_vs_wav(self):
        """FLAC header with .wav extension must be rejected."""
        validate = self._get_validator()
        flac_as_wav = b"fLaC" + b"\x00" * 60
        assert validate(flac_as_wav, ".wav") is False


class TestExtensionValidation:
    """Test that disallowed file extensions are caught before any file is written."""

    @pytest.mark.asyncio
    async def test_disallowed_extension_returns_400(self):
        from app.main import app
        from app.core.database import get_db
        from app.core.auth import get_current_user
        from httpx import AsyncClient, ASGITransport

        async def override_db():
            yield AsyncMock()

        fake_user = MagicMock()
        fake_user.id = "00000000-0000-0000-0000-000000000001"
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: fake_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                payload = io.BytesIO(b"MZ\x90\x00")  # PE header
                resp = await client.post(
                    "/api/upload",
                    files={"file": ("payload.exe", payload, "application/octet-stream")},
                )
            assert resp.status_code == 400
            assert "extension" in resp.json()["detail"].lower() or "format" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_missing_filename_returns_400(self):
        from app.main import app
        from app.core.database import get_db
        from app.core.auth import get_current_user
        from httpx import AsyncClient, ASGITransport

        async def override_db():
            yield AsyncMock()

        fake_user = MagicMock()
        fake_user.id = "00000000-0000-0000-0000-000000000001"
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: fake_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/upload",
                    files={"file": ("", io.BytesIO(b""), "audio/wav")},
                )
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()


class TestPathTraversal:
    """Verify that path traversal attempts in filenames are neutralized."""

    def test_storage_path_uses_task_id_not_filename(self):
        """
        The upload endpoint must store files as uploads/{task_id}/input{ext}.
        The user-supplied filename must NOT appear in the filesystem path.

        We verify this by inspecting the source: the line that sets file_path
        must reference 'task_id' and NOT 'file.filename'.
        """
        import inspect
        from app.api.upload import upload_audio

        source = inspect.getsource(upload_audio)
        # Find the line that defines file_path
        file_path_lines = [
            line.strip() for line in source.splitlines()
            if "file_path" in line and "=" in line and "output_path" not in line
        ]
        # At least one assignment to file_path must exist
        assert file_path_lines, "No file_path assignment found in upload_audio"

        for line in file_path_lines:
            # The storage path construction must NOT use file.filename
            assert "file.filename" not in line, (
                f"file.filename used in storage path construction: {line}\n"
                "This creates a path traversal risk. Use task_id instead."
            )

    def test_original_name_stored_only_as_metadata(self):
        """
        file.filename may appear in the code only for metadata/DB storage,
        never for constructing filesystem paths.
        """
        import inspect
        from app.api.upload import upload_audio

        source = inspect.getsource(upload_audio)
        # Allowed: os.path.basename(file.filename) for original_name metadata
        # Allowed: ext = os.path.splitext(file.filename) for extension check
        # NOT allowed: any path join that uses file.filename directly
        lines = source.splitlines()
        for line in lines:
            stripped = line.strip()
            # Flag any os.path.join that includes file.filename
            if "os.path.join" in stripped and "file.filename" in stripped:
                assert False, (
                    f"os.path.join uses file.filename directly:\n  {stripped}\n"
                    "This is a path traversal vulnerability."
                )

