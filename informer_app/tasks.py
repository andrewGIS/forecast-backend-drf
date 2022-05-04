import os
from datetime import date, datetime

from telethon import TelegramClient
import asyncio

from auth_app.models import Person
from celery_app import app
from forecast_app.models import VectorForecast


async def main(telegramLogin='@antar93',  message='Testing telethon'):
    app_id = int(os.getenv('NOTIFICATION_APP_ID', None))
    api_hash = os.getenv('NOTIFICATION_APP_HASH', None)
    bot_id = os.getenv('NOTIFICATION_BOT_TOKEN', None)
    client = TelegramClient('anon', app_id, api_hash)
    await client.start(bot_token=bot_id)
    await client.send_message(telegramLogin, message)


@app.task(name="send_notification")
def run_main(message):
    asyncio.run(main(message))
    # return HttpResponse('ok')


@app.task(name="send_notifications")
def send_notifications():
    """
    Отправка оповещений всем пользователям с логином по интересующей точке
    :return:
    """
    # TODO пока оповещение можно делать по gfs модели
    from informer_app.models import InfoPoint
    accountsWithLogins = Person.objects.filter(telegram_login__isnull=False)
    for account in accountsWithLogins:
        # TODO пока берем только одну точку у пользователя
        targetPoint = InfoPoint.objects.filter(user=account.user)[0]
        # TODO брать буфер вокруг точки
        userForecasts = VectorForecast.objects.filter(
            forecast_date=datetime.now().date(),
            #forecast_date=date(2021, 5, 15),
            #mpoly__intercests=targetPoint.point
        )
        userForecasts = userForecasts.order_by('forecast_datetime_utc')
        userForecasts = userForecasts.distinct('level_code', 'model', 'forecast_datetime_utc')

        message = ''

        if userForecasts.count() == 0:
            asyncio.run(main(
                account.telegram_login,
                'По текущему прогнозу для вашей области интереса опасных явлений не обнаружено'
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
                message += (
                        f"Время - {f.forecast_datetime_utc.strftime('%H:%M')};"
                        f" Явление -  {f.forecast_group.alias}; \n"
                )

        asyncio.run(main(account.telegram_login, message))
        return message
