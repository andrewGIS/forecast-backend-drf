import datetime
import logging
import io

import numpy as np
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D
from typing import Tuple, Dict, Optional, List, Union, Literal, Type

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



logger = logging.getLogger(__name__)


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
    # TODO сделать через фильтры
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
    logger.debug(srcString)
    return srcString


def create_forecast(
        forecastType: Literal['00', '12'],
        date: datetime.datetime,
        groupName: str,
):
    """
    Расчет прогноза для одного конкретного срока для одной группы явлений
    Все расчеты ведем в UTC time
    :param forecastType: Тип прогноза оз полночи или от полудня
    :param date: Точная дата прогноза с часом в UTC
    :param groupName: Имя группы явлений для расчета (шторм, смерч и т.д.)
    :return:
    """

    forecastGroup = ForecastGroup.objects.get(name=groupName)
    forecastGroupCalculations: List[Calculation] = Calculation.objects.filter(forecast_group=forecastGroup)
    forecastModel = forecastGroupCalculations[0].model  # каждый
    fullDateUTC = date.strftime(f'%Y%m%d{forecastType}.0%H')  # получаем дату с часов прогноза -> 2021072100.003
    hourForecast = date.strftime('0%H')  # час прогноза -> 003, 012 так представлено в исходных растрах

    # На всякий слуачай проверяем что час пронгоза есть в нашем перечне
    hourDB = date.strftime('%H')  # час прогноза -> 03, 12 так представляем в базе
    # assert (hourDB in InfoMixin.FORECAST_UTC_HOURS_CHOICES,
    #         f'Неизвестный час {hourDB}, известные {InfoMixin.FORECAST_UTC_HOURS_CHOICES}')

    # Расчет значений для всех уровней опасности для одной группы (например для всех уровней опасности для
    # шторма)
    levels = []
    for calculation in forecastGroupCalculations:
        calculated = perform_calculation(
            forecastType=forecastType,
            hourForecast=hourForecast,
            forecastModel=forecastModel,
            calculation=calculation,
            date=date,
            save_index_rasters=False
        )
        levels.append(calculated)

    # select most danger group for each pixel
    result = np.stack(levels, axis=2)
    # все в одноканальном растре выбран саммый высокий риск опасности
    result = np.ma.masked_equal(result, 0)
    result = result.min(axis=2)
    result = result.filled(fill_value=0)

    logger.debug(f'''
        Расчет для группы {forecastGroup} - модель {forecastModel.name} закончен. 
        Результат растр формой {result.shape}'''
    )


    # Обязательно формируем итоговую дату после выполнения расчетов, потому что дата на которую прогнозируем
    # может быть другая ( пример gfs.2022041412.021.cape_surface.tif -> 20220415.009)
    # тут добавляем смещение потому что в прогнозе от 12 часов прогноз делаем уже
    # на следущий день и дата меняется
    if forecastType == '12':
        shiftedDate = date.replace(hour=12) + datetime.timedelta(hours=int(hourDB))
        logger.warning(
            f'Преобразование даты (т.к. тип прогноза -  {forecastType}): '+
            f'исходная дата {date} будет записана в БД как {shiftedDate}'
        )
        date = shiftedDate
        fullDateUTC = shiftedDate.strftime(f'%Y%m%d{forecastType}.0%H')  # получаем дату с часов прогноза -> 2021072100.003
        hourDB = shiftedDate.strftime('%H')  # час прогноза -> 03, 12 так представляем в базе

    # Общие атрибуты для прогнозов
    # Обязательно размещать после того расчет сделан, потому что даты источника,
    # и итоговая дата прогноза могут измениться смотри чуть выше
    generalOptions = {
        'model': forecastModel,
        'forecast_group': forecastGroup,
        'date_UTC_full': fullDateUTC,
        'forecast_date': date,
        'forecast_type': forecastType,
        'forecast_datetime_utc': date,
        'forecast_hour_utc': hourDB
    }

    # save raster forecast to db
    save_forecast_raster(result, forecastModel, **generalOptions)

    # Векторизация
    raster2dbvector(result, forecastModel, **generalOptions)


def perform_calculation(
        forecastType: Literal['00', '12'],
        hourForecast: Literal['00', '03', '06', '09', '12', '15', '18', '21', '24'],
        forecastModel: Type[ForecastModel],
        calculation: Calculation,
        date: datetime.datetime,
        save_index_rasters: bool,
) -> np.array:
    """
    Выполняем расчет одного полного выражения
    :param save_index_rasters: Сохрнаять ли промежуточные растры из вычислений
    :param date: Дата расчета
    :param forecastModel:
    :param hourForecast: час для которого вычисляем
    :param forecastType: тип прогноза который считаем
    :param calculation: выражение для вычисления
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

        if save_index_rasters:

            save_remote_raster_to_db(
                modelName=forecastModel.name,
                indexName=d.index_name,
                forecastType=forecastType,
                date=date,
            )

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
    del data
    return calculated


def save_forecast_raster(inArrayData: np.array, forecastModel: Type[ForecastModel], **kwargs):
    """

    :param inArrayData: Входной одномерный массив, где пиксель уровень риска
    :param forecastModel:
    :param kwargs: Общие параметры прогноза дата, время и т.д (InfoMixin)
    :return:
    """

    # Итоговый растр
    outRaster = GDALRaster({
        'nr_of_bands': 1,
        'width': forecastModel.rasterWidth,
        'height': forecastModel.rasterHeight,
        'srid': 4326,
        'datatype': 1,
        'bands': [{
            'data': inArrayData.astype(np.uint8),  # без приведения значения неправильные записывались
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


def raster2dbvector(inArrayData: np.array, forecastModel: Type[ForecastModel], **kwargs):
    """

    :param forecastModel:
    :param inArrayData: Входной одномерный массив, где пиксель уровень риска
    :param kwargs:
        'model': forecastModel,
        'forecast_group': forecastGroup,
        'date_UTC_full': fullDateUTC,
        'forecast_date': date,
        'forecast_type': forecastType,
        'forecast_datetime_utc': date,
        'forecast_hour_utc': hourDB
    :return:
    """

    # Растр для векторизации
    logger.debug(' '.join([
        f"Векторизация растра дата - {kwargs.get('forecast_date')}",
        f"время - {kwargs.get('forecast_hour_utc')}"
    ]))
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
    band = dstDs.GetRasterBand(1)
    gdal.Polygonize(band, band, outLayer, 0, [], callback=None)

    # Записываем каждую отдельную фичу
    for feature in outLayer:
        geom = feature.GetGeometryRef().ExportToWkt()
        v = VectorForecast(
            mpoly=GEOSGeometry(geom, srid=4326),
            level_code=feature.GetField("level_risk"),
            **kwargs
        )
        v.save()

    outLayer.ResetReading()  # по моему для следующей нормальной векторизации

    outDataSource.Destroy()
    dstDs = None
    inRaster = None


def save_remote_raster_to_db(modelName: str, indexName: str, forecastType: Literal['00', '12'], date: datetime.datetime):
    """
    Get remote raster and save to db
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
        'index_name': indexName
    }
    indexRaster = IndexRaster(raster=rst, **options)
    indexRaster.save()


def get_remote_raster(modelName: str, indexName: str, forecastType: Literal['00', '12'], hour: str, date: datetime.datetime):
    """
    Sample how to return raster for leaflet tif
    https://ihcantabria.github.io/Leaflet.CanvasLayer.Field/dist/leaflet.canvaslayer.field.js
    :return:
    """
    model = ForecastModel.objects.get(name=modelName)
    srcString = calc_path(
        indexName=indexName,
        hour=hour,
        forecastType=forecastType,
        modelName=model.name,
        date=date
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
