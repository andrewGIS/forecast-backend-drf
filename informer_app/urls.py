from django.urls import path
from .views import CreateNotificationView, InfoPointsList, check_intersection

urlpatterns = [
    path('order', CreateNotificationView.as_view(), name='order_notification'),
    path('send_test', check_intersection, name='send_test'),
    path('list_points', InfoPointsList.as_view(), name='user_info_points')
]
