import datetime
from typing import Literal

from celery_app import app

from .models import InfoMixin, ForecastModel, Calculation
from .services import create_forecast
from informer_app.tasks import send_notifications
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


@app.task(name="create_forecast_for_model")
def create_forecast_for_model(
        forecastModelName: str,
        forecastType: Literal['00', '12'],
):
    """
    Вычисление для модели для сегодняшнего дня для всех часов для всех групп
    :param forecastModelName: Модель для расчета
    :param forecastType: 00 и 12 от какого срока прогноз
    :return:
    """

    forecastModel = ForecastModel.objects.get(name=forecastModelName)
    # Это получение моделей только для одной группы
    calculations = Calculation.objects.filter(model=forecastModel)
    dateToday = datetime.datetime.now().date()
    logger.info(
        f'Create daily forecast: model - {forecastModelName}, date - {dateToday}, type -  {forecastType}'
    )
    date = datetime.datetime(dateToday.year, dateToday.month, dateToday.day)  # для того чтобы можно заменить час
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

    send_notifications(forecastModelName, forecastType)
