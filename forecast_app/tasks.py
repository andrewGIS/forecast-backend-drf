# from celery.schedules import crontab
from celery_app import app
from celery import Task


def test(arg):
    print(arg)


@app.task(name="testTask")
def add(x, y):
    z = x + y
    print(z)
