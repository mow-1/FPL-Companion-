import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('fpl_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ─── Periodic tasks ───────────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Full FPL data sync: daily at 6am UTC
    'full-fpl-sync-daily': {
        'task': 'fpl.tasks.task_full_sync',
        'schedule': crontab(hour=6, minute=0),
    },
    # Sync current GW fixtures every 30 min during GW window
    'sync-current-gw-fixtures': {
        'task': 'fpl.tasks.task_sync_current_gw_fixtures',
        'schedule': crontab(minute='*/30'),
    },
    # Run predictions after daily sync (6:30am)
    'run-predictions-daily': {
        'task': 'predictions.tasks.task_run_predictions_for_gw',
        'schedule': crontab(hour=6, minute=30),
    },
}
