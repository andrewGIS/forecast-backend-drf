from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.forms import TextInput
from django.db import models

from forecast_app.models import (
    RasterForecast,
    ForecastModel, Calculation,
    Variable,
    ForecastGroup,
    VectorForecast
)


# Register your models here.
@admin.register(RasterForecast, ForecastModel, Variable, ForecastGroup, VectorForecast)
class ForecastAppAdmin(GISModelAdmin):
    pass


class CalculationModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '200'})},
    }


admin.site.register(Calculation, CalculationModelAdmin)
