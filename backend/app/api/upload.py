import os
import shutil
import uuid
import aiofiles
import soundfile as sf
import torchaudio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import get_settings
from app.core.celery import queue_protect_task
from app.core.auth import get_current_user
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/api", tags=["upload"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac"}
MAX_SIZE = settings.max_file_size_mb * 1024 * 1024
CHUNK_SIZE = 65536  # 64 KB buffer for streaming


def validate_audio_magic_bytes(header: bytes, ext: str) -> bool:
    """Validate file signatures against declared extension."""
    if ext == ".wav":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    elif ext == ".flac":
        return len(header) >= 4 and header[:4] == b"fLaC"
    elif ext == ".mp3":
        if len(header) >= 3 and header[:3] == b"ID3":
            return True
        if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
            return True
        return False
    return False


@router.post("/upload", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio(
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    # 1. Extension validation
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Prepare isolated storage path (UUID directory + fixed safe filename)
    task_id = uuid.uuid4()
    upload_dir = os.path.abspath(os.path.join(settings.upload_dir, str(task_id)))
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, f"input{ext}")
    output_path = os.path.join(upload_dir, "output_protected.wav")

    total_bytes = 0

    # 3. Stream to disk in 64 KB chunks, enforcing size and magic bytes
    try:
        async with aiofiles.open(file_path, "wb") as f:
            # Read first chunk to validate magic bytes
            first_chunk = await file.read(CHUNK_SIZE)
            if not first_chunk:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")

            if not validate_audio_magic_bytes(first_chunk, ext):
                raise HTTPException(
                    status_code=400,
                    detail=f"File content signature does not match declared audio format ({ext})."
                )

            total_bytes += len(first_chunk)
            if total_bytes > MAX_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File exceeds maximum allowed size ({settings.max_file_size_mb} MB)."
                )
            await f.write(first_chunk)

            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File exceeds maximum allowed size ({settings.max_file_size_mb} MB)."
                    )
                await f.write(chunk)

    except HTTPException:
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise
    except Exception as io_err:
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to stream upload to disk: {str(io_err)}")

    # 4. Content decodability and audio duration validation
    try:
        try:
            info = sf.info(file_path)
            duration = info.duration
        except Exception:
            meta = torchaudio.info(file_path)
            duration = meta.num_frames / meta.sample_rate if meta.sample_rate > 0 else 0.0

        if duration <= 0:
            raise ValueError("Audio stream has zero length or no decodable audio frames.")

        if duration > settings.max_duration_seconds:
            raise ValueError(
                f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit ({settings.max_duration_seconds}s)."
            )

    except Exception as decode_err:
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=f"Corrupted or invalid audio file: {str(decode_err)}"
        )

    # 5. Create database record (storing original_name only as metadata)
    task = Task(
        id=task_id,
        user_id=current_user.id,
        original_name=os.path.basename(file.filename),
        file_path=file_path,
        output_path=output_path,
        status="queued"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 6. Queue Celery job with synchronized task_id
    queue_protect_task(str(task_id), file_path, output_path)

    return task
