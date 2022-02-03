from django.urls import path
from .views import (
    models,
    forecast_groups,
    debug_create_forecast,
    get_forecast_by_date, get_forecast_by_xy
)

urlpatterns = [
    path('models/', models, name='models'),
    path('event_groups/<str:model_name>/', forecast_groups, name='event_groups'),
    path('test_forecast/', debug_create_forecast, name='test_forecast'),
    path('test_intersect/', get_forecast_by_xy, name='test_intersect'),
    path('get_forecast/', get_forecast_by_date, name='get_forecast')
]
