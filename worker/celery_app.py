from celery import Celery
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "audioshield",
    broker=redis_url,
    backend=redis_url,
    include=["tasks.protect"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_pool="solo",  # Single GPU job at a time
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
