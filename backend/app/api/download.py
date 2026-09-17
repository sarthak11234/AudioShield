import os
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.task import Task
from app.models.user import User

router = APIRouter(prefix="/api", tags=["download"])

@router.get("/download/{task_id}")
async def download_protected(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Query task ensuring ownership verification to prevent information leakage
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    if task.status in ("queued", "processing"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is still processing. Current status: {task.status}"
        )

    if task.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task processing failed: {task.error_message or 'Internal worker error'}"
        )

    if task.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Task has expired and audio files were automatically deleted."
        )

    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is not ready for download. Status: {task.status}"
        )

    if not task.output_path or not os.path.exists(task.output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Protected file not found on storage"
        )

    base_name = os.path.splitext(task.original_name)[0]
    filename = f"{base_name}_protected.wav"

    return FileResponse(
        task.output_path,
        media_type="audio/wav",
        filename=filename
    )
