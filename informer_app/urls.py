from django.urls import path
from auth_app.views import check_jwt
from informer_app.views import main
import asyncio

urlpatterns = [
    path('order', check_jwt, name='check_jwt'),
    #path('send_test', asyncio.run(main()), name='send_test')
]
