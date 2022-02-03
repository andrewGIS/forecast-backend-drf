from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from forecast_app.models import (
    RasterForecast,
    ForecastModel, Calculation,
    Variable,
    ForecastGroup,
    VectorForecast
)


# Register your models here.
@admin.register(RasterForecast, ForecastModel, Calculation, Variable, ForecastGroup, VectorForecast)
class ForecastAppAdmin(GISModelAdmin):
    pass
