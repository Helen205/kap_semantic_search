from celery import Celery
from celery.schedules import crontab
from celery.signals import beat_init, worker_ready
from .config import config

celery_app = Celery(
    'kap_semantic_search',
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
    include=[
        'src.tasks.content_tasks',
        'src.tasks.table_tasks'
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1
)



celery_app.autodiscover_tasks()

@worker_ready.connect
def at_start(sender, **kwargs):
    with sender.app.connection() as conn:
        sender.app.send_task('process_content')
        sender.app.send_task('process_tables')
        crontab(minute=43, hour='*/2')
