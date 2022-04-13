import datetime
import io

import numpy as np
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D
from typing import Tuple, Dict, Optional, List, Union

from django.core.serializers import serialize
from osgeo import gdal, osr, ogr
from raster.algebra.parser import FormulaParser

from forecast_app.models import (
    VectorForecast,
    RasterForecast,
    ForecastGroup,
    Calculation,
    ForecastModel,
    IndexRaster
)


def find_forecast(
        coordinates: Optional[Tuple[float, float]] = None,
        level_code: Optional[int] = None,
        date: Optional[datetime.datetime] = None,
        forecastGroup: Optional[str] = None,
        modelName: Optional[str] = None,
        hour: Optional[str] = None,
        dataType: Optional[str] = None
) -> Union[Dict, GDALRaster]:
    """
    Выполняем поиск прогнозов c учетом разных фильтров
    :param dataType: Тип данных (растр, вектор)
    :param hour: Час для фильтрации
    :param modelName: Имя модели, для которой ищем прогноз
    :param forecastGroup: Имя группы опасных явлений
    :param coordinates: Координаты для поиска X , Y
    :param level_code: Дата для поиска, если не указана ищем по всем
    :param date: Дата для поиска, если не указана ищем по всем

    :return: Geojson как словарь или первый найденный растр
    """
    data = VectorForecast.objects if dataType == 'vector' else RasterForecast.objects

    # TODO координаты по растру нельзя запрашивать
    if coordinates:
        pnt_wkt = f'POINT({coordinates[0]} {coordinates[1]})'
        searchDistance = D(km=20)
        data = data.filter(mpoly__distance_lt=(pnt_wkt, searchDistance))

    if level_code:
        data = data.filter(code=level_code)

    if date:
        data = data.filter(forecast_date=date)

    if hour:
        data = data.filter(forecast_hour_utc=hour)

    if forecastGroup:
        fGroup = ForecastGroup.objects.get(name=forecastGroup)
        data = data.filter(forecast_group=fGroup)

    if modelName:
        fModel = ForecastModel.objects.get(name=modelName)
        data = data.filter(model=fModel)

    # пробуем выбрать более поздний прогноз
    # TODO неконсистеный вывод надо это как то в фильтр вывести
    forecastTypes = list(data.distinct('forecast_type').values_list('forecast_type', flat=True))
    if '12' in forecastTypes:
        data = data.filter(forecast_type='12')

    if dataType == 'raster':
        rst = GDALRaster({
            'name': '/vsimem/temporarymemfile',
            'driver': 'tif',
            'width': data[0].raster.width,
            'height': data[0].raster.height,
            'srid': 4326,
            'datatype': 1,
            'bands': [{'data': data[0].raster.bands[0].data()}]
        })
        rst.geotransform = data[0].raster.geotransform
        return rst

    # на фронте ждем поле level code для подписей
    return serialize('geojson', data, geometry_field='mpoly', fields=('level_code',))
    # return serialize('geojson', data, geometry_field='mpoly')
    # return serialize('geojson', data, geometry_field='mpoly')


def calc_path(
        indexName: str,
        hour: str,
        forecastType: str,
        date: datetime.datetime,
        modelName: str
):
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

    # return f'/vsizip//vsicurl/http://84.201.155.104/gfs-ural/2021082100.zip\\gfs.2021082100.015.{x}.tif'
    formattedDate = date.strftime("%Y%m%d")
    srcString = (
            f'/vsizip//vsicurl/http://84.201.155.104/' +
            f'{modelName}-ural/{formattedDate}{forecastType}.zip' +
            f'\\{modelName}.{formattedDate}{forecastType}.{hour}.{indexName}.tif'
    )
    print(srcString)
    return srcString


def create_forecast(
        forecastType: str,
        date: datetime.datetime,
        groupName: Optional[str] = None,
):
    """
    Расчет прогноза для одного конкретного срока
    Все расчеты ведем в UTC time
    :param forecastType:
    :param date: Точная дата прогноза с часом в UTC
    :param groupName:
    :return:
    """

    forecastGroup = ForecastGroup.objects.get(name=groupName) if groupName else ForecastGroup.objects.all()[0]
    forecastGroupCalculations: List[Calculation] = list(Calculation.objects.filter(forecast_group=forecastGroup))
    forecastModel = forecastGroupCalculations[0].model  # каждый уровень опасности рассчитывается для одной модели
    fullDateUTC = date.strftime(f'%Y%m%d{forecastType}.0%H')  # получаем дату с часов прогноза -> 2021072100.003
    hourForecast = date.strftime('0%H')  # час прогноза -> 003, 012 так представлено в исходных растрах

    # На всякий слуачай проверяем что час пронгоза есть в нашем перечне
    hourDB = date.strftime('%H')  # час прогноза -> 03, 12 так представляем в базе
    # assert (hourDB in InfoMixin.FORECAST_UTC_HOURS_CHOICES,
    #         f'Неизвестный час {hourDB}, известные {InfoMixin.FORECAST_UTC_HOURS_CHOICES}')

    # Общие атрибуты для прогнозов
    generalOptions = {
        'model': forecastModel,
        'forecast_group': forecastGroup,
        'date_UTC_full': fullDateUTC,
        'forecast_date': date,
        'forecast_type': forecastType,
        'forecast_datetime_utc': date,
        'forecast_hour_utc': hourDB
    }

    # Расчет значений для всех уровней опасности для одной группы (например для всех уровней опасности для
    # шторма)
    levels = []
    for calculation in forecastGroupCalculations:
        calculated = perform_calculation(
            forecastType=forecastType,
            hourForecast=hourForecast,
            forecastModel=forecastModel,
            calculation=calculation,
            date=date
        )
        levels.append(calculated)

    # select most danger group for each pixel
    result = np.stack(levels, axis=2)

    # save raster forecast to db
    save_forecast_raster(result, **generalOptions)

    # Векторизация
    raster2vector(result, forecastModel)


def perform_calculation(
        forecastType,
        hourForecast,
        forecastModel: ForecastModel,
        calculation: Calculation,
        date
) -> np.array:
    """
    Выполняем расчет одного выражения
    :param calculation:
    :return: результат вычисления
    """

    data = {}
    for d in calculation.variables.all():
        srcPath = calc_path(
            indexName=d.index_name,
            forecastType=forecastType,
            hour=hourForecast,
            date=date,
            modelName=forecastModel.name
        )
        data[d.variable] = GDALRaster(srcPath).bands[0].data()

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
    return calculated


def save_forecast_raster(inArrayData: np.array, forecastModel: ForecastModel, **kwargs):
    """

    :param inArrayData: Входные данные в виде массива, где каждый канал это уровень риска (1, 2, 3 ,4 )
    :param forecastModel:
    :param kwargs: Общие параметры InfoMixin
    :return:
    """

    # need mask for zero values
    result = np.ma.masked_equal(inArrayData, 0)
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
        **kwargs
    )
    r.save()


def raster2vector(inArrayData: np.array, forecastModel: ForecastModel, *args, **kwargs):
    """

    :param forecastModel:
    :param inArrayData:
    :param inRaster:
    :param args:
    :param kwargs: Общие параметры прогноза
    :return:
    """

    # Растр для векторизации
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326)
    driver = gdal.GetDriverByName("GTiff")
    dstDs = driver.Create(
        '/vsimem/tempRaster.tiff',  # временный растр имя не имеет значения
        forecastModel.rasterWidth,
        forecastModel.rasterHeight,
        1,
        gdal.GDT_Byte
    )
    dstDs.SetProjection(outSpatialRef.ExportToWkt())
    transform = forecastModel.geotransform
    dstDs.SetGeoTransform([float(i) for i in transform[1:-1].split(',')])
    dstDs.GetRasterBand(1).WriteArray(inArrayData.astype(np.uint8))

    # Создание вектора
    driver = ogr.GetDriverByName("Memory")
    outDataSource = driver.CreateDataSource('memory')
    newField = ogr.FieldDefn('level_risk', ogr.OFTInteger)
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(4326)
    outLayer = outDataSource.CreateLayer(f"mask", srs=sr)
    outLayer.CreateField(newField)

    # Polygonize
    band = inRaster.GetRasterBand(1)
    gdal.Polygonize(band, band, outLayer, 0, [], callback=None)

    # Записываем каждую отдельную фичу
    for feature in outLayer:
        geom = feature.GetGeometryRef().ExportToWkt()
        v = VectorForecast(
            mpoly=GEOSGeometry(geom, srid=4326),
            code=feature.GetField("level_risk"),
            **kwargs
        )
        v.save()

    outLayer.ResetReading()  # по моему для следующей нормальной векторизации

    outDataSource.Destroy()
    inRaster = None


def save_remote_raster_to_db(modelName, indexName, forecastType, date: datetime.datetime):
    """
    Batch get raster and save to db
    """
    forecastModel = ForecastModel.objects.get(name=modelName)
    fullDateUTC = date.strftime(f'%Y%m%d{forecastType}.0%H')  # получаем дату с часов прогноза -> 2021072100.003
    hourForecast = date.strftime('0%H')  # час прогноза -> 003, 012 так представлено в исходных растрах

    srcString = calc_path(
        indexName=indexName,
        hour=hourForecast,
        forecastType=forecastType,
        modelName=modelName,
        date=date
    )

    data = GDALRaster(srcString).bands[0].data()
    rst = GDALRaster({
        'nr_of_bands': 1,
        'width': forecastModel.rasterWidth,
        'height': forecastModel.rasterHeight,
        'srid': 4326,
        'bands': [{'data': data}]
    })
    gt = forecastModel.geotransform
    rst.geotransform = [float(i) for i in gt[1:-1].split(',')]

    options = {
        'model': forecastModel,
        'date_UTC_full': fullDateUTC,
        'forecast_date': date,
        'forecast_type': forecastType,
        'forecast_datetime_utc': date,
        'forecast_hour_utc': int(hourForecast),
        # 'raster': rst
    }
    indexRaster = IndexRaster(raster=rst, **options)
    indexRaster.save()


def get_remote_raster():
    """
    Sample how to return raster for leaflet tif
    https://ihcantabria.github.io/Leaflet.CanvasLayer.Field/dist/leaflet.canvaslayer.field.js
    :return:
    """
    modelName = 'gfs'
    model = ForecastModel.objects.get(name=modelName)
    srcString = calc_path(
        indexName='dls',
        hour='009',
        forecastType='00',
        modelName='gfs',
        date=datetime.date(2021, 5, 15)
    )
    data = GDALRaster(srcString).bands[0].data()
    rst = GDALRaster({
        'name': '/vsimem/temporarymemfile',
        'driver': 'tif',
        'width': model.rasterWidth,
        'height': model.rasterHeight,
        'srid': 4326,
        'bands': [{'data': data}]
    })
    gt = model.geotransform
    rst.geotransform = [float(i) for i in gt[1:-1].split(',')]
    return rst
