import os
from datetime import datetime,timedelta

from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.measure import D
from django.db.models.query import QuerySet
from telethon import TelegramClient
import asyncio

from auth_app.models import Person
from celery_app import app
from forecast_app.models import VectorForecast, ForecastModel
from informer_app.models import InfoPoint


async def main(telegramLogin='@antar93',  message='Testing telethon'):
    app_id = int(os.getenv('NOTIFICATION_APP_ID', None))
    api_hash = os.getenv('NOTIFICATION_APP_HASH', None)
    bot_id = os.getenv('NOTIFICATION_BOT_TOKEN', None)
    client = TelegramClient('anon', app_id, api_hash)
    await client.start(bot_token=bot_id)
    await client.send_message(telegramLogin, message)
    await client.disconnect()


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

    for account in accountsWithLogins:
        allUserPoints = InfoPoint.objects.filter(user=account.user)
        if allUserPoints.count() == 0:
            continue

        # TODO пока берем только одну точку у пользователя
        targetPoint = allUserPoints[0]

        # TODO проверить логику надо ли так делать?
        if forecastType == '12':
            # Если прогноз от 12 часов дня (полудня) уже интресен прогноз на следующую дату
            filterDate = datetime.now().date() + timedelta(days=1)

        userForecasts = VectorForecast.objects.filter(
            forecast_date=filterDate,
            model=usedForecastModel,
            forecast_type=forecastType,
            mpoly__distance_lte=(targetPoint.point, D(m=BUFFER_SIZE))
        )
        userForecasts = userForecasts.order_by('forecast_datetime_utc')
        userForecasts = userForecasts.distinct('level_code', 'model', 'forecast_datetime_utc')

        message = f'Прогноз по модели **{modelName}**, тип - {forecastType}'
        message += '\n'
        message += '\n'
        message += f'Дата прогноза - на {filterDate}'
        message += '\n'

        if userForecasts.count() == 0:
            message += '\n'
            message += 'По текущему прогнозу для вашей области интереса опасных явлений не обнаружено'
            asyncio.run(main(
                account.telegram_login,
                message
            ))
            return 'Not event founded'

        # какие вообще уровни есть для нашего пользователя
        level_codes = set(userForecasts.values_list('level_code', flat=True))
        for level_code in sorted(level_codes):
            message += '\n'
            emoji = None
            count = 2
            if level_code == 1:
                emoji = "😱"*count
            if level_code == 2:
                emoji = "😬"*count
            if level_code == 3:
                emoji = "☹"*count
            if level_code == 4:
                emoji = "🙁"*count

            message += f"{emoji} ** Уровень опасности {level_code}** {emoji} \n"
            message += '\n'
            for f in userForecasts.filter(level_code=level_code):
                pntDatetime = f.forecast_datetime_utc - timedelta(hours=targetPoint.pointFromUTCOffset)
                message += (
                        f"Время - {pntDatetime.strftime('%H:%M')};"
                        f" Явление -  {f.forecast_group.alias}; \n"
                )

        asyncio.run(main(account.telegram_login, message))
        return message

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

    message = f'Прогноз по модели **{modelName}**, тип - {forecastType}'
    message += '\n'
    message += '\n'
    message += f'Дата прогноза - на {filterDate}'
    message += '\n'
    message += '\n'
    message += 'Обнаруженные ОЯ:'
    message += '\n'

    summary = todayForecasts.distinct('level_code', 'forecast_group_id').order_by('level_code')

    for row in summary:
        message += '\n'
        emoji = None
        count = 1
        if row.level_code == 1:
            emoji = "😱" * count
        if row.level_code == 2:
            emoji = "😬" * count
        if row.level_code == 3:
            emoji = "☹" * count
        if row.level_code == 4:
            emoji = "🙁" * count

        subquery = todayForecasts.filter(level_code=row.level_code, forecast_group_id=row.forecast_group.id)
        area = calc_area(subquery)
        message += "".join([
            f"{emoji} - Уровень  - **{row.level_code}**, ",
            f"Явление - **{row.forecast_group.alias}**, ",
            f"Площадь -{area:.2f} км.кв, ",
            f"Количество объектов- {subquery.count()}; \n"
        ])

    for account in adminWithLogins:
        if todayForecasts.count() != 0 :
            message += '\n'
            message += f'Посмотреть {os.getenv("NOTIFICATION_FRONT_ADDRESS", default="http://ogs.psu.ru:5003")}'
        asyncio.run(main(account.telegram_login, message))
        return message


def calc_area(data: QuerySet):
    wgs84 = SpatialReference('WGS84')
    # коническая альберса
    albersConic = '+proj=eqdc +lat_0=0 +lon_0=0 +lat_1=15 +lat_2=65 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m no_defs'
    albersConic = SpatialReference(albersConic)
    ct = CoordTransform(wgs84, albersConic)
    # В в квадратных километрах, важно копировать геометрию иначе на месте изменяется
    area = sum([f.mpoly.transform(ct=ct, clone=True).area for f in list(data.all())])/1000000
    return area
