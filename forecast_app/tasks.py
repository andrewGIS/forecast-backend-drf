import datetime

import numpy as np

from celery_app import app

from .models import InfoMixin, ForecastModel, Calculation
from .services import perform_calculation, save_forecast_raster, raster2vector


@app.task(name="create_forecast_today")
def create_forecast_for_model(forecastModelName, forecastType):
    """
    Вычисление для модели для сегодняшнего дня для всех часов для всех групп
    :param forecastModelName:
    :param forecastType:
    :param date:
    :return:
    """
    forecastModel = ForecastModel.objects.get(name=forecastModelName)
    # Это получение моделей только для одной группы
    calculations = Calculation.objects.filter(model=forecastModel)
    date_today = datetime.datetime.now().date()
    date = datetime.datetime(date_today.year, date_today.month, date_today.day)  # для того чтобы можно заменить час

    # На всякий слуачай проверяем что час пронгоза есть в нашем перечне

    # assert (hourDB in InfoMixin.FORECAST_UTC_HOURS_CHOICES,
    #         f'Неизвестный час {hourDB}, известные {InfoMixin.FORECAST_UTC_HOURS_CHOICES}')

    # Получаем какие у нас группы есть для текущей группы
    for forecastGroup in [q.forecast_group for q in calculations]:

        # расчеты для каждого часа
        for hour, hour in InfoMixin.FORECAST_UTC_HOURS_CHOICES:
            date = date.replace(hour=int(hour))
            hourDB = date.strftime('%H')  # час прогноза -> 03, 12 так представляем в базе
            hourForecast = date.strftime('0%H')  # час прогноза -> 003, 012 так представлено в исходных растрах
            fullDateUTC = date.strftime(f'%Y%m%d{forecastType}.0%H')  # получаем дату с часов прогноза -> 2021072100.003
            levels = []
            for calculation in calculations.filter(forecast_group=forecastGroup):
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
                # Расчет значений для всех уровней опасности для
                # одной группы и выбранной модели(например для всех
                # уровней опасности для шторма)
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
                save_forecast_raster(
                    inArrayData=result,
                    forecastModel=forecastModel,
                    **generalOptions
                )

                # Векторизация
                raster2vector(
                    inArrayData=result,
                    forecastModel=forecastModel,
                    **generalOptions
                )