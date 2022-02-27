from django.contrib.auth.models import User
from django.db import models


class Person(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    telegram_login = models.CharField(name='telegram_login', max_length=150)
