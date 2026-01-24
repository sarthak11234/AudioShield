from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "audioshield",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

def queue_protect_task(task_id: str, input_path: str, output_path: str):
    """Queue audio protection task to Celery worker."""
    celery_app.send_task(
        "protect_audio",
        args=[task_id, input_path, output_path],
    )
