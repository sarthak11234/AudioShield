import logging
from typing import List, Optional
import os
import shutil
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.celery import celery_app
from app.core.auth import get_current_user
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskResponse, TaskStatus
from app.core.config import get_settings

logger = logging.getLogger("audioshield.api.status")
router = APIRouter(prefix="/api", tags=["status"])


async def sync_task_with_celery(task: Task, db: AsyncSession) -> tuple:
    """
    Syncs task status with Celery state machine:
    QUEUED -> PROCESSING -> COMPLETED
    QUEUED / PROCESSING -> FAILED
    Durable source of truth is PostgreSQL.
    """
    if task.status in ("completed", "failed", "expired"):
        return task.status, None, task.error_message

    current_status = task.status or "queued"
    progress = None
    error_message = task.error_message

    try:
        async_result = celery_app.AsyncResult(str(task.id))
        state = async_result.state

        if state == "SUCCESS":
            result_data = async_result.result
            if isinstance(result_data, dict):
                if result_data.get("status") == "failed":
                    current_status = "failed"
                    task.status = "failed"
                    task.error_message = result_data.get("error", "Unknown worker error")
                    error_message = task.error_message
                    task.processed_at = datetime.utcnow()
                    await db.commit()
                else:
                    current_status = "completed"
                    task.status = "completed"
                    task.processed_at = datetime.utcnow()
                    if result_data.get("output_path"):
                        task.output_path = result_data.get("output_path")
                    await db.commit()
            else:
                current_status = "completed"
                task.status = "completed"
                task.processed_at = datetime.utcnow()
                await db.commit()

        elif state == "FAILURE":
            current_status = "failed"
            task.status = "failed"
            err_msg = str(async_result.result) if async_result.result else "Celery worker failure"
            task.error_message = err_msg
            error_message = err_msg
            task.processed_at = datetime.utcnow()
            await db.commit()

        elif state in ("PROCESSING", "PROGRESS", "STARTED"):
            current_status = "processing"
            meta = async_result.info or {}
            if isinstance(meta, dict):
                progress = meta.get("step")
            if task.status != "processing":
                task.status = "processing"
                await db.commit()

        elif state == "PENDING":
            current_status = task.status or "queued"

    except Exception as e:
        logger.warning("Failed to query Celery state for task %s: %s", task.id, e)

    return current_status, progress, error_message


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

    status, progress, error_message = await sync_task_with_celery(task, db)

    return TaskStatus(
        id=task.id,
        status=status,
        progress=progress,
        error_message=error_message,
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

    await sync_task_with_celery(task, db)
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

    for task in tasks:
        if task.status in ("queued", "processing"):
            await sync_task_with_celery(task, db)

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
