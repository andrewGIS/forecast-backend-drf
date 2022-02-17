from django.urls import path
from .views import create_notification, check_intersection

urlpatterns = [
    path('order', create_notification, name='order_notification'),
    path('send_test', check_intersection, name='send_test')
]
