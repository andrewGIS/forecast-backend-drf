import json

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User
from rest_framework import status

from celery_app import app
from .models import InfoPoint
from django.contrib.gis.geos import Point
from forecast_app.models import VectorForecast
from .tasks import send_test_message, send_notifications


def create_notification(request):
    # TODO сделать через serialazer
    # TODO проверить что правильно приходит долгота и широта
    JWT_authenticator = JWTAuthentication()

    # authenitcate() verifies and decode the token
    # if token is invalid, it raises an exception and returns 401
    response = JWT_authenticator.authenticate(request)
    data = json.loads(request.body)
    if response is not None:
        # unpacking
        user, token = response
        user_id = token['user_id']
        user = User.objects.get(id=user_id)
        if not user:
            return Response(data="User not found", status=status.HTTP_400_BAD_REQUEST)
        # x -> долгота y-> широта
        pnt = Point(x=float(data['x']), y=float(data['y']), srid=4326)
        infoPoint = InfoPoint(
            user=user,
            point=pnt,
            name=data['name'],
        )
        infoPoint.save()

        return HttpResponse('ok')

    else:
        return HttpResponse('not ok')


def check_intersection(request):
    #send_notifications()
    send_test_message()
    return HttpResponse('ok')
