from typing import List
import os
import shutil
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.celery import celery_app
from app.core.auth import get_current_user
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskResponse, TaskStatus
from datetime import datetime

router = APIRouter(prefix="/api", tags=["status"])

@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Check Celery for actual task status
    progress = None
    celery_status = task.status
    
    try:
        async_result = celery_app.AsyncResult(str(task_id))
        if async_result.state == "SUCCESS":
            result_data = async_result.result
            if result_data and result_data.get("status") == "completed":
                celery_status = "completed"
                task.status = "completed"
                task.processed_at = datetime.utcnow()
                await db.commit()
            elif result_data and result_data.get("status") == "failed":
                celery_status = "failed"
                task.status = "failed"
                task.error_message = result_data.get("error", "Unknown error")
                await db.commit()
        elif async_result.state == "PROCESSING":
            celery_status = "processing"
            meta = async_result.info or {}
            progress = meta.get("step")
        elif async_result.state == "PENDING":
            celery_status = "queued"
    except Exception:
        pass
    
    return TaskStatus(
        id=task.id,
        status=celery_status,
        progress=progress
    )

@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(404, "Task not found")
    
    return task

@router.get("/tasks", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task)
        .where(Task.user_id == current_user.id)
        .order_by(Task.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks

@router.delete("/task/{task_id}")
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(404, "Task not found")
        
    from app.core.config import get_settings
    settings = get_settings()
    
    task_dir = os.path.join(settings.upload_dir, str(task.id))
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)
        
    await db.delete(task)
    await db.commit()
    return {"status": "success", "message": "Task deleted"}
