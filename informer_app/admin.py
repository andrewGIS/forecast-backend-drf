from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from informer_app.models import InfoPoint


@admin.register(InfoPoint)
class InformerAppAdmin(GISModelAdmin):
    pass
