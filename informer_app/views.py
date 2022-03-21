from django.http import HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User

from celery_app import app
from .models import InfoPoint
from django.contrib.gis.geos import Point
from forecast_app.models import VectorForecast
from .tasks import run_main


def create_notification(request):
    JWT_authenticator = JWTAuthentication()

    # authenitcate() verifies and decode the token
    # if token is invalid, it raises an exception and returns 401
    response = JWT_authenticator.authenticate(request)
    if response is not None:
        # unpacking
        user, token = response
        #print(user, token['user_id'])
        user_id = token['user_id']
        user = User.objects.get(id=user_id)
        # x -> долгота y-> широта
        pnt = Point(x=56.229443, y=58.010455, srid=4326)
        infoPoint = InfoPoint(
            user=user,
            point=pnt
        )
        infoPoint.save()

        return HttpResponse('ok')


def check_intersection(request):
    pnt = InfoPoint.objects.all()[0].point
    dates = [
        p.forecast_date.strftime("%Y%M%d") for p in VectorForecast.objects.filter(mpoly__intersects=pnt)
    ]
    for d in dates:
        run_main.delay(d)
    return HttpResponse('ok')
