import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

app = Celery('app_drf')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

#app.conf.broker_url = 'redis://localhost:6379/0' # когда разрабатываем локально редиску может не увидеть
app.conf.broker_url = 'redis://redis:6379'
app.loader.override_backends['django-db'] = 'django_celery_results.backends.database:DatabaseBackend'

# Load task modules from all registered Django apps.
# django-raster cause problem so i comment it
# app.autodiscover_tasks()
# app.tasks.register(forecast_app.tasks.test)
# TODO время по Пермскому времени как сервер
app.conf.beat_schedule = {
    'get-forecast-gfs-00': {
        'task': 'create_forecast_for_model',
        'schedule': crontab(hour=15, minute=30),
        'args': ('gfs', '00')
    },
    'get-forecast-gfs-12': {
        'task': 'create_forecast_for_model',
        'schedule': crontab(hour=15, minute=30),
        'args': ('gfs', '12')
    },
    'get-forecast-icon-00': {
        'task': 'create_forecast_for_model',
        'schedule': crontab(hour=15, minute=30),
        'args': ('icon', '00')
    },
    'get-forecast-icon-12': {
        'task': 'create_forecast_for_model',
        'schedule': crontab(hour=15, minute=30),
        'args': ('icon', '12')
    },
}
