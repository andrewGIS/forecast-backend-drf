import datetime

from django.contrib.gis.gdal import GDALRaster

from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from informer_app.tasks import send_notifications
from .models import (
    ForecastModel,
    Calculation, InfoMixin, VectorForecast, ForecastGroup,
)
from .serializers import ForecastModelSerializer, CalculationSerializer, VectorForecastDatesSerializer, LegendSerializer

from django.http import HttpResponse, JsonResponse
from .services import create_forecast, find_forecast, get_remote_raster, save_remote_raster_to_db


@api_view(['GET'])
def models(request):
    forecastModels = ForecastModel.objects.all()
    serializer = ForecastModelSerializer(forecastModels)
    return Response(serializer.data)


@api_view(['GET'])
def forecast_groups(request):
    modelName = request.GET.get('model', default=None)
    calculations = Calculation.objects.filter(model__name=modelName).distinct('forecast_group__name')
    serializer = CalculationSerializer(calculations, many=True)
    return Response({"groups": serializer.data})


@api_view(['GET'])
def get_forecast_by_filter(request):
    modelName = request.GET.get('model', None)
    date = request.GET.get('date', None)
    hour = request.GET.get('hour', None)
    group = request.GET.get('group', None)
    dataType = request.GET.get('dataType', 'vector')

    if not any([date, hour]):
        return Response(status=status.HTTP_204_NO_CONTENT)

    params = [modelName, date, hour, group]
    params = [p for p in params if p]
    outFileName = '.'.join(params)
    if not outFileName:
        outFileName = 'data'

    if date:
        date = datetime.datetime.strptime(date, '%Y%m%d')

    responseData = find_forecast(
        modelName=modelName,
        forecastGroup=group,
        date=date,
        hour=hour,
        dataType=dataType
    )

    fileExtension = '.geojson'
    contentType = 'application/json'
    if dataType == 'raster':
        responseData = responseData.vsi_buffer
        contentType = 'image/tiff'
        fileExtension = '.tif'

    response = HttpResponse(
        responseData,
        content_type=contentType,
    )
    outFileName = outFileName + fileExtension
    response['Content-Disposition'] = f'attachment; filename="{outFileName}"'
    return response


@api_view(['GET'])
def get_dates(request):
    modelName = request.GET.get('model', None)
    if not modelName:
        return JsonResponse({"dates": []})
    data = VectorForecast.objects.filter(model__name=modelName)
    data = data.distinct('forecast_date')
    # data = data.annotate(
    #     formatted_date=Func(
    #         F('forecast_date'),
    #         Value('YYYY-MM-DD'),
    #         function='to_char',
    #         output_field=CharField()
    #     )
    # )
    # dates = data.values_list('formatted_date', flat=True)
    s = VectorForecastDatesSerializer(data, many=True)
    return JsonResponse(s.data, safe=False)
    # return JSONRenderer().render(dates)


@api_view(['GET'])
def get_indexes(request):
    modelName = request.GET.get('model', None)
    data = ForecastModel.objects.get(name=modelName)
    indexes = [str(i) for i in  data.indexes[1:-1].split(',')]
    return JsonResponse({'indexes': indexes}, safe=False)


@api_view(['GET'])
def get_legend(request):
    modelName = request.GET.get('model', None)
    group = request.GET.get('group', None)
    data = Calculation.objects.filter(model__name=modelName, forecast_group__name=group).order_by('code')
    s = LegendSerializer(data, many=True)
    return JsonResponse(s.data, safe=False)


@api_view(['GET'])
def get_raster(request):
    response = HttpResponse(get_remote_raster().vsi_buffer)
    response['Content-Disposition'] = f'attachment; filename="test.tif"'
    return response


def web_app(request):
    # TODO sample how to transfer some data to template
    context = {"value": "Hello Django", "message": "Welcome to Python"}
    return render(request, 'forecast_app/index.html', context)


def get_forecast_by_xy(request):
    testCoordinates = (56.43, 61.53)
    return HttpResponse(
        find_forecast(coordinates=testCoordinates),
        content_type='application/json'
    )


def debug_create_forecast(request):
    #send_notifications()
    #return HttpResponse('ok')
    # base = datetime.datetime(2022, 3, 13)
    # date_list = [base - datetime.timedelta(days=x) for x in range(1)]
    date_list = [datetime.datetime(2022, 4, 14)]
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


def debug_save_index(request):
    # base = datetime.datetime(2022, 4, 15)
    # date_list = [base - datetime.timedelta(days=x) for x in range(1)]
    date_list = [datetime.datetime(2022, 4, 14)]
    for date in date_list:
        for hour, hour in InfoMixin.FORECAST_UTC_HOURS_CHOICES:
            for fType in ['00', '12']:
                date = date.replace(hour=int(hour))
                save_remote_raster_to_db(
                    modelName='gfs',
                    indexName='dls',
                    forecastType=fType,
                    date=date
                )
    return HttpResponse('ok')


def debug_periodic_task(request):
    from forecast_app.tasks import create_forecast_for_model
    create_forecast_for_model('gfs', '00')
    return HttpResponse('ok')
