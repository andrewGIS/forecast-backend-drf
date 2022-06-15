from django.contrib.gis.db import models
from django.contrib.auth.models import User


class InfoPoint(models.Model):
    point = models.PointField(srid=4326)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.TextField(max_length=150)
    pointFromUTCOffset = models.IntegerField(default=0)

    def __str__(self):
        return  f'{self.user.get_full_name()} : {self.name}' if self.user.get_full_name() else self.name
