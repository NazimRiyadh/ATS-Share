import os
from celery import Celery
from .config import settings

# Get Redis URL from environment or default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ats_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.worker"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker configuration
    worker_concurrency=2,  # Limit concurrency to avoid overloading LLM/DB
    worker_prefetch_multiplier=1, # Ensure fair distribution for long tasks
)

if __name__ == "__main__":
    celery_app.start()
