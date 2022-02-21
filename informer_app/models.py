from django.contrib.gis.db import models
from django.contrib.auth.models import User


class InfoPoint(models.Model):
    point = models.PointField(srid=4326)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
