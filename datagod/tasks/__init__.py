"""
DataGod Celery Task Configuration
Async task processing for scrapers, ML, and background jobs
"""

import os
from celery import Celery

# Configure Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "datagod",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "datagod.tasks.scraper_tasks",
        "datagod.tasks.ml_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,         # 1 hour hard limit
    task_soft_time_limit=3000,    # 50 min soft limit
    worker_prefetch_multiplier=1, # Fair scheduling
    worker_max_tasks_per_child=50,  # Restart workers periodically
    task_acks_late=True,          # Re-deliver on worker crash
    task_reject_on_worker_lost=True,
    result_expires=86400,         # Results expire after 24 hours
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "check-data-quality-daily": {
        "task": "datagod.tasks.ml_tasks.check_data_quality",
        "schedule": 86400.0,  # 24 hours
    },
    "run-anomaly-scan-hourly": {
        "task": "datagod.tasks.ml_tasks.run_anomaly_scan",
        "schedule": 3600.0,  # 1 hour
    },
}
