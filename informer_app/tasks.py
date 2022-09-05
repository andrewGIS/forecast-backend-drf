import os
from datetime import datetime, timedelta
from typing import List, Tuple

from telethon import TelegramClient
import asyncio

from auth_app.models import Person
from celery_app import app
from forecast_app.models import VectorForecast, ForecastModel
from informer_app.models import InfoPoint
from informer_app.utils import AdminMessageCreator, UserMessageCreator


async def main(telegramLogin='@antar93',  message='Testing telethon'):
    app_id = int(os.getenv('NOTIFICATION_APP_ID', None))
    api_hash = os.getenv('NOTIFICATION_APP_HASH', None)
    bot_id = os.getenv('NOTIFICATION_BOT_TOKEN', None)
    client = TelegramClient('anon', app_id, api_hash)
    await client.start(bot_token=bot_id)
    await client.send_message(telegramLogin, message)
    await client.disconnect()

async def send_messages(data:List[Tuple]):
    """
    :param data: List[(Account, message for telegram account)]
    :return:
    """
    app_id = int(os.getenv('NOTIFICATION_APP_ID', None))
    api_hash = os.getenv('NOTIFICATION_APP_HASH', None)
    bot_id = os.getenv('NOTIFICATION_BOT_TOKEN', None)
    client = TelegramClient('anon', app_id, api_hash)
    await client.start(bot_token=bot_id)
    for login, message in data:
        await client.send_message(login, message)
    await client.disconnect()

def run_butch_sending_messages(data:List[Tuple]):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(send_messages(data))
    loop.close()

@app.task(name="send_notification")
def send_test_message():
    asyncio.run(main(
        "antar93",
        'По текущему прогнозу для вашей области интереса опасных явлений не обнаружено'
    ))
    # return HttpResponse('ok')

@app.task(name="send_notifications")
def send_notifications(modelName, forecastType, filterDate=None):
    """
    Отправка оповещений всем пользователям с логином по интересующей точке
    :return:
    """
    BUFFER_SIZE = 20000 # расстояние от точки в метрах
    # TODO пока оповещение можно делать по gfs модели
    accountsWithLogins = Person.objects.filter(telegram_login__isnull=False)
    usedForecastModel = ForecastModel.objects.get(name=modelName)
    # TODO добавить смещение пользователя в UTC
    if not filterDate:
        filterDate = datetime.now().date()

    if forecastType == '12':
        # Если прогноз от 12 часов дня (полудня) уже интресен прогноз на следующую дату
        filterDate = filterDate + timedelta(days=1)

    data = []
    for account in accountsWithLogins:
        allUserPoints = InfoPoint.objects.filter(user=account.user)
        if allUserPoints.count() == 0:
            continue

        # TODO пока берем только одну точку у пользователя
        targetPoint = allUserPoints[0]
        messenger = UserMessageCreator(userPoint=targetPoint)

        # TODO проверить логику надо ли так делать?
        if forecastType == '12':
            # Если прогноз от 12 часов дня (полудня) уже интресен прогноз на следующую дату
            filterDate = datetime.now().date() + timedelta(days=1)

        userForecasts = VectorForecast.objects.filter(
            forecast_date=filterDate,
            model=usedForecastModel,
            forecast_type=forecastType,
            #mpoly__distance_lte=(targetPoint.point, D(m=BUFFER_SIZE))
        )
        userForecasts = userForecasts.order_by('forecast_datetime_utc')
        userForecasts = userForecasts.distinct('level_code', 'model', 'forecast_datetime_utc')

        data.append((
            account.telegram_login,
            messenger.get_message(filterDate, userForecasts)
        ))

    run_butch_sending_messages(data)

@app.task(name="send_notifications_admin")
def send_notifications_admin(modelName, forecastType, filterDate=None):
    """
    Отправка оповещений админам суммарную информацию
    :return:
    """
    # TODO может рассылать по группе
    # TODO пока оповещение можно делать по gfs модели
    adminWithLogins = Person.objects.filter(telegram_login__isnull=False, user__is_staff=True)
    usedForecastModel = ForecastModel.objects.get(name=modelName)
    messenger = AdminMessageCreator(forecastType=forecastType, modelName=modelName)

    if not filterDate:
        filterDate = datetime.now().date()
    if forecastType == '12':
        # Если прогноз от 12 часов дня (полудня) уже интресен прогноз на следующую дату
        filterDate = filterDate + timedelta(days=1)

    todayForecasts = VectorForecast.objects.filter(
        forecast_date=filterDate,
        model=usedForecastModel,
        forecast_type=forecastType
    )

    data = []
    for account in adminWithLogins:
        data.append((
            account.telegram_login,
            messenger.get_message(filterDate, todayForecasts)
        ))

    run_butch_sending_messages(data)
