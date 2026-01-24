import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import get_settings
from app.core.celery import queue_protect_task
from app.models.task import Task
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/api", tags=["upload"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac"}
MAX_SIZE = settings.max_file_size_mb * 1024 * 1024

@router.post("/upload", response_model=TaskResponse)
async def upload_audio(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}")
    
    # Validate size
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"File too large. Max: {settings.max_file_size_mb}MB")
    
    # Save file with absolute paths (so worker can find them)
    task_id = uuid.uuid4()
    upload_dir = os.path.abspath(os.path.join(settings.upload_dir, str(task_id)))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    output_path = os.path.join(upload_dir, f"{os.path.splitext(file.filename)[0]}_protected.wav")
    
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    # Create task record
    task = Task(
        id=task_id,
        original_name=file.filename,
        file_path=file_path,
        output_path=output_path,
        status="queued"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Queue Celery job
    queue_protect_task(str(task_id), file_path, output_path)
    
    return task

