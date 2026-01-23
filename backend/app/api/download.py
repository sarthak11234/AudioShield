import os
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.task import Task

router = APIRouter(prefix="/api", tags=["download"])

@router.get("/download/{task_id}")
async def download_protected(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(404, "Task not found")
    
    if task.status != "completed":
        raise HTTPException(400, f"Task not ready. Status: {task.status}")
    
    if not task.output_path or not os.path.exists(task.output_path):
        raise HTTPException(404, "Protected file not found")
    
    filename = f"{os.path.splitext(task.original_name)[0]}_protected.wav"
    
    return FileResponse(
        task.output_path,
        media_type="audio/wav",
        filename=filename
    )
