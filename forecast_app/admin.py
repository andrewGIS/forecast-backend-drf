from django.contrib import admin
from forecast_app.models import RasterForecast, ForecastModel, Calculation, Variable, ForecastGroup


# Register your models here.
@admin.register(RasterForecast, ForecastModel, Calculation, Variable, ForecastGroup)
class ForecastAppAdmin(admin.ModelAdmin):
    pass
