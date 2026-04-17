import os
import shutil
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, update
from app.core.database import async_session
from app.models.task import Task
from app.core.config import get_settings

settings = get_settings()

async def cleanup_expired_tasks():
    """Background task to delete files older than 1 hour and update DB."""
    while True:
        try:
            # Run every 15 minutes
            await asyncio.sleep(15 * 60)
            
            async with async_session() as db:
                # Find tasks older than 1 hour (from created_at or processed_at)
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                
                query = select(Task).where(
                    (Task.status.in_(["completed", "failed", "queued", "processing"])) &
                    (Task.created_at < one_hour_ago)
                )
                result = await db.execute(query)
                expired_tasks = result.scalars().all()
                
                for task in expired_tasks:
                    # Delete folder and contents
                    task_dir = os.path.join(settings.upload_dir, str(task.id))
                    if os.path.exists(task_dir):
                        print(f"[Cleanup] Deleting directory {task_dir} for task {task.id}")
                        shutil.rmtree(task_dir, ignore_errors=True)
                    
                    # Update status to expired
                    task.status = "expired"
                    task.file_path = ""
                    task.output_path = ""
                
                if expired_tasks:
                    await db.commit()
                    print(f"[Cleanup] Cleaned up {len(expired_tasks)} expired tasks.")
                    
        except asyncio.CancelledError:
            print("[Cleanup] Task cancelled.")
            break
        except Exception as e:
            print(f"[Cleanup] Error in cleanup task: {e}")
            await asyncio.sleep(60) # Wait a minute before retrying on error
