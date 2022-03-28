from datetime import date

from telethon import TelegramClient
import asyncio

from auth_app.models import Person
from celery_app import app
from forecast_app.models import VectorForecast


async def main(message='Testing telethon'):
    app_id = 17386428;
    api_hash = '53007e6795449acea2e68919f1e89a17'
    bot_id = '5157309405:AAHnxLw2PHyVcQgO8qamEJbcM_y28XcqSwE'
    async with TelegramClient(bot_id, app_id, api_hash) as client:
        await client.send_message('@antar93', message)


@app.task(name="send_notification")
def run_main(message):
    asyncio.run(main(message))
    # return HttpResponse('ok')


@app.task(name="send_notifications")
def send_notifications():
    from forecast_app.services import find_forecast
    from informer_app.models import InfoPoint
    accountsWithLogins = Person.objects.filter(telegram_login__isnull=False)
    for account in accountsWithLogins:
        # TODO пока берем только одну точку
        targetPoint = InfoPoint.objects.filter(user=account.user)[0]
        userForecasts = VectorForecast.objects.filter(
            forecast_date=date(2021, 5, 15),
            # mpoly__intercests=targetPoint.point
        )
        userForecasts = userForecasts.order_by('forecast_datetime_utc')
        userForecasts = userForecasts.distinct('level_code', 'model', 'forecast_datetime_utc')

        level_codes = set(userForecasts.values_list('level_code', flat=True))
        message = ''
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
                        f" Явление -  {f.forecast_group.alias};" +
                        f" Модель - {f.model.name} \n"
                )

        asyncio.run(main(message))
        return message
