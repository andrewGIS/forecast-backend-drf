import datetime
from typing import List

import numpy as np
from django.contrib.gis.gdal import GDALRaster
from rest_framework import viewsets

from forecast_app.models import RasterForecast, Calculation, ForecastGroup

# Create your views here.
from django.http import HttpResponse, FileResponse
from forecast_app.models import IndexRaster, ForecastModel
from raster.algebra.parser import RasterAlgebraParser, FormulaParser


def calc_path(x: str):
    # Пример доступа к данным без загрузки
    # zipFile = r"D:\Work\_new_features\forecast\app_drf\forecast_app\2021072100.zip"
    # filename = 'gfs.2021072100.003.cape_180-0.tif'
    # rst = GDALRaster(f'/vsizip//{zipFile}\\{filename}')
    # rst = GDALRaster(f'/vsizip//vsicurl/http://84.201.155.104/gfs-ural/2022012100.zip//{filename}')

    # One calculation sample with online raster
    # rst = GDALRaster(
    #     f'/vsizip//vsicurl/http://84.201.155.104/gfs-ural/2022012100.zip\\gfs.2022012100.003.cape_180-0.tif'
    # )
    # data = dict(zip(['x'], [rst]))

    return f'/vsizip//vsicurl/http://84.201.155.104/gfs-ural/2021082100.zip\\gfs.2021082100.015.{x}.tif'


def test_saving(request, groupName=None):

    forecastGroup = ForecastGroup.objects.get(name=groupName) if groupName else ForecastGroup.objects.all()[0]
    forecastGroupCalculations: List[Calculation] = list(Calculation.objects.filter(forecast_group=forecastGroup))
    forecastModel = forecastGroupCalculations[0].model   # каждый уровень опасности рассчитывается для одной модели

    # Расчет значений
    levels = []
    for calculation in forecastGroupCalculations:
        data = {}
        for s in calculation.variables.all():
            data[s.variable] = GDALRaster(
                calc_path(s.index_name)
            ).bands[0].data()

        # Используем Formula Parser, потому что RasterAlgebraParse не правильно
        # записывает значения когда получаются логические значения
        # при ипользовании FormulaParser можно привести к определленному типу
        # parser = RasterAlgebraParser()
        # calculated = parser.evaluate_raster_algebra(data, squall.expression)
        # но приходится тянуть дополнительные метаданные модели
        parser = FormulaParser()
        calculated = (parser.evaluate(data, calculation.expression)).astype(np.uint8)

        # заменяем код на уровень риска
        calculated = np.where(calculated == 0, 0, calculation.code)
        levels.append(calculated)

    # select most danger group for each pixel
    result = np.stack(levels, axis=2)

    # need mask for zero values
    result = np.ma.masked_equal(result, 0)
    result = result.min(axis=2)
    result = result.filled(fill_value=0)

    # Итоговый растр
    outRaster = GDALRaster({
        'nr_of_bands': 1,
        'width': forecastModel.rasterWidth,
        'height': forecastModel.rasterHeight,
        'srid': 4326,
        'datatype': 1,
        'bands': [{
            'data': result.astype(np.uint8),  # без приведения значения неправильные записывались
            'nodata_value': 255
        }]
    })
    # указать после создания растра, в конструкторе не подхватывается
    # строку (34.875, 0.25, 0.0, 65.125, 0.0, -0.25) в питоновский объект список
    # через eval не стал делать
    transform = forecastModel.geotransform
    outRaster.geotransform = [float(i) for i in transform[1:-1].split(',')]


    r = RasterForecast(
        raster=outRaster,
        model=ForecastModel.objects.get(name='gfs'),
        forecast_group=ForecastGroup.objects.get(name='squall'),
        date_UTC_full='2021072100.003',
        forecast_date=datetime.datetime(2021, 7, 21),
        forecast_type='00',
        forecast_datetime_utc=datetime.datetime(2021, 7, 21, 3),
    )
    r.save()

    return HttpResponse('ok')


def download(request):
        """
        Return a specific raster.
        """

        import io


        # rst = GDALRaster({
        #      'name': '/vsimem/temporarymemfile',
        #      'driver': 'tif',
        #      'width': 161, 'height': 61, 'srid': 4326,
        #      'bands': [{'data': RasterForecast.objects.all()[1].raster.bands[0].data()}]
        # })

        rst = GDALRaster({
             'name': '/vsimem/temporarymemfile',
             'driver': 'tif',
             'width': 161, 'height': 61, 'srid': 4326,
             'bands': [{'data': IndexRaster.objects.all()[0].raster.bands[0].data()}]
        })

        file = io.BytesIO()
        file.write(rst.vsi_buffer)
        file.seek(0)

        # sending response
        response = HttpResponse(rst.vsi_buffer, content_type='image/tiff')
        response['Content-Disposition'] = 'attachment;filename="foo.tif"'

        #return HttpResponse(rst.vsi_buffer, 'image/tiff')
        return response
        #return FileResponse(rst.vsi_buffer, filename='test.tif')


def run_calculation(request):

    parser = RasterAlgebraParser()
    querySet = RasterRisk.objects.all()
    rast1 = querySet[0].raster
    rast2 = querySet[1].raster
    data = dict(zip(['x', 'y'], [rast1, rast2]))
    rst = parser.evaluate_raster_algebra(data, 'x + y')

    new_rst = GDALRaster({
        'name': '/vsimem/temporarymemfile',
        'driver': 'tif',
        'width': 161,
        'height': 61,
        'srid': 4326,
        'datatype': 6,
        'bands': [{'data': rst.bands[0].data()}]
    })

    return HttpResponse(new_rst.vsi_buffer, 'image/tiff')

