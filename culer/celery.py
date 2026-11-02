import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module for celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'culer.settings')

app = Celery('culer')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Scheduled Automation Configuration
app.conf.beat_schedule = {
    # 03:00 UTC daily fixture sync
    'sync-barca-fixtures-daily': {
        'task': 'matches.tasks.sync_barca_fixtures_task',
        'schedule': crontab(hour=3, minute=0),
    },
    # Smart matchday window monitor every 15 minutes (exits <10ms if no match is live)
    'smart-matchday-window-monitor': {
        'task': 'matches.tasks.smart_matchday_window_monitor_task',
        'schedule': crontab(minute='*/15'),
    },
    # Mondays at 04:00 UTC weekly squad sync
    'sync-barca-squad-weekly': {
        'task': 'matches.tasks.sync_barca_squad_task',
        'schedule': crontab(hour=4, minute=0, day_of_week='mon'),
    },
    # Sundays at 02:00 UTC editorial maintenance audit
    'editorial-maintenance-audit': {
        'task': 'analysis.tasks.editorial_maintenance_audit_task',
        'schedule': crontab(hour=2, minute=0, day_of_week='sun'),
    },
}


@app.task(bind=True, name='culer.ping_task')
def ping_task(self):
    """Debug task to verify Celery worker connectivity."""
    return "pong"
