import datetime

from django.contrib.gis.gdal import GDALRaster

from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    ForecastModel,
    Calculation, InfoMixin,
)
from .serializers import ForecastModelSerializer, CalculationSerializer

from django.http import HttpResponse
from .services import create_forecast, find_forecast


@api_view(['GET'])
def models(request):
    forecastModels = ForecastModel.objects.all()
    serializer = ForecastModelSerializer(forecastModels)
    return Response(serializer.data)


@api_view(['GET'])
def forecast_groups(request, model_name):
    calculations = Calculation.objects.filter(model__name=model_name).distinct('forecast_group__name')
    serializer = CalculationSerializer(calculations, many=True)
    return Response({"groups": serializer.data})


def web_app(request):
    context = {"value": "Hello Django", "message": "Welcome to Python"}
    return render(request, 'forecast_app/index.html', context)


def get_forecast_by_xy(request):
    testCoordinates = (56.43, 61.53)
    return HttpResponse(
        find_forecast(coordinates=testCoordinates),
        content_type='application/json'
    )


def debug_create_forecast(request):
    base = datetime.datetime(2021, 5, 4)
    date_list = [base - datetime.timedelta(days=x) for x in range(1)]
    for date in date_list:
        for hour, hour in InfoMixin.FORECAST_UTC_HOURS_CHOICES:
            for fType in ['00', '12']:
                date = date.replace(hour=int(hour))
                create_forecast(
                    groupName='squall',
                    forecastType=fType,
                    date=date,
                )
    return HttpResponse('ok')


def get_forecast_by_date(request):
    modelName = request.GET.get('model', None)
    date = request.GET.get('date', None)
    hour = request.GET.get('hour', None)
    group = request.GET.get('group', None)
    dataType = request.GET.get('dataType', 'vector')

    if date:
        date = datetime.datetime.strptime(date, '%Y%m%d')

    if dataType == 'raster':
        rst = find_forecast(
            modelName=modelName,
            forecastGroup=group,
            date=date,
            hour=hour,
            dataType='raster'
        )
        response = HttpResponse(rst.vsi_buffer, content_type='image/tiff')
        #response['Content-Disposition'] = 'attachment;filename="foo.tif"'

        return response

    return HttpResponse(
        find_forecast(
            modelName=modelName,
            forecastGroup=group,
            date=date,
            hour=hour
        ),
        content_type='application/json',
    )
