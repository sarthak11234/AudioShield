import os
import shutil
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.database import async_session
from app.models.task import Task
from app.core.config import get_settings
from app.core.celery import celery_app

logger = logging.getLogger("audioshield.cleanup")
settings = get_settings()

async def cleanup_expired_tasks():
    """
    Background task to delete expired files:
    1. Completed/failed tasks older than file_ttl_hours (based on processed_at or created_at)
    2. Stale tasks stuck in queued/processing for > 3 hours (revoking Celery task first)
    """
    while True:
        try:
            # Run every 15 minutes
            await asyncio.sleep(15 * 60)

            async with async_session() as db:
                now = datetime.utcnow()
                ttl_cutoff = now - timedelta(hours=settings.file_ttl_hours)
                stale_cutoff = now - timedelta(hours=max(settings.file_ttl_hours * 2, 3))

                # 1. Tasks that finished and exceeded TTL
                finished_query = select(Task).where(
                    (Task.status.in_(["completed", "failed"])) &
                    (Task.created_at < ttl_cutoff)
                )
                res_finished = await db.execute(finished_query)
                expired_finished = res_finished.scalars().all()

                # 2. Abandoned/stuck tasks
                stuck_query = select(Task).where(
                    (Task.status.in_(["queued", "processing"])) &
                    (Task.created_at < stale_cutoff)
                )
                res_stuck = await db.execute(stuck_query)
                stuck_tasks = res_stuck.scalars().all()

                for task in stuck_tasks:
                    try:
                        celery_app.control.revoke(str(task.id), terminate=True)
                    except Exception as e:
                        logger.warning("Failed to revoke Celery task %s: %s", task.id, e)
                    task.error_message = "Task abandoned due to processing timeout."

                all_expired = expired_finished + stuck_tasks

                for task in all_expired:
                    task_dir = os.path.join(settings.upload_dir, str(task.id))
                    if os.path.exists(task_dir):
                        logger.info("[Cleanup] Deleting storage directory %s for task %s", task_dir, task.id)
                        shutil.rmtree(task_dir, ignore_errors=True)

                    task.status = "expired"
                    task.file_path = ""
                    task.output_path = ""

                if all_expired:
                    await db.commit()
                    logger.info("[Cleanup] Successfully cleaned up %d tasks.", len(all_expired))

        except asyncio.CancelledError:
            logger.info("[Cleanup] Task cancelled.")
            break
        except Exception as e:
            logger.error("[Cleanup] Error in cleanup loop: %s", e, exc_info=True)
            await asyncio.sleep(60)
