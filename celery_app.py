import os
from celery import Celery
# Set the default Django settings module for the 'celery' program.

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

app = Celery('app_drf')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.broker_url = 'redis://localhost:6379/0'
app.loader.override_backends['django-db'] = 'django_celery_results.backends.database:DatabaseBackend'

# Load task modules from all registered Django apps.
# django-raster cause problem so i comment it
# app.autodiscover_tasks()
# app.tasks.register(forecast_app.tasks.test)
app.conf.beat_schedule = {
    'add-every-30-seconds': {
        'task': 'testTask',
        'schedule': 30.0,
        'args': (16, 16)
    },
}
