from django.urls import path
from .views import NotificationView, test_sending

urlpatterns = [
    path('order', NotificationView.as_view(), name='order'),
    path('order/<int:pk>', NotificationView.as_view(), name='order'),
    path('send_test', test_sending, name='send_test'),
    path('list_points', NotificationView.as_view(), name='user_info_points')
]
