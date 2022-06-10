from django.urls import path
from .views import (
    models,
    forecast_groups,
    debug_create_forecast,
    get_forecast_by_filter, get_forecast_by_xy, get_dates, get_indexes, get_legend, get_raster
)

urlpatterns = [
    path('models/', models, name='models'),
    path('event_groups/', forecast_groups, name='event_groups'),
    path('test_forecast/', debug_create_forecast, name='test_forecast'),
    path('test_intersect/', get_forecast_by_xy, name='test_intersect'),
    path('get_forecast/', get_forecast_by_filter, name='get_forecast'),
    path('get_dates/', get_dates, name='get_dates'),
    path('indexes/', get_indexes, name='get_indexes'),
    path('get_legend/', get_legend, name='get_legend'),
    path('get_raster/', get_raster, name='get_raster'),
]
