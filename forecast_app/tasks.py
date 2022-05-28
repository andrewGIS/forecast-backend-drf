import datetime
from typing import Literal

from celery_app import app

from .models import InfoMixin, ForecastModel, Calculation
from .services import create_forecast


@app.task(name="create_forecast_for_model")
def create_forecast_for_model(forecastModelName: str, forecastType: Literal['00', '12']):
    """
    Вычисление для модели для сегодняшнего дня для всех часов для всех групп
    :param forecastModelName: Модель для расчета
    :param forecastType: 00 и 12 от какого срока прогноз
    :return:
    """
    forecastModel = ForecastModel.objects.get(name=forecastModelName)
    # Это получение моделей только для одной группы
    calculations = Calculation.objects.filter(model=forecastModel)
    date_today = datetime.datetime.now().date()
    date = datetime.datetime(date_today.year, date_today.month, date_today.day)  # для того чтобы можно заменить час

    # Получаем какие у нас группы есть для текущей группы (штормы, смерчи и т.д.)
    # группы можем получить только из вычислений, которые привязаны к модели
    for calculation in calculations:
        # расчеты для каждого часа
        for hour, hour in InfoMixin.FORECAST_UTC_HOURS_CHOICES:
            date = date.replace(hour=int(hour))

            create_forecast(
                    forecastType=forecastType,
                    date=date,
                    groupName=calculation.forecast_group.name
                )

    send_notifications()
