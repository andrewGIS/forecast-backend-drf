celery -A celery_app  worker --pool=solo -l INFO

celery -A forecast_app.tasks.app  beat --loglevel=info
