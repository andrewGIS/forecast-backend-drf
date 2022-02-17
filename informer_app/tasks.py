from telethon import TelegramClient
import asyncio
from celery_app import app


async def main(message='Testing telethon'):
    app_id = 17386428;
    api_hash = '53007e6795449acea2e68919f1e89a17'
    bot_id = '5157309405:AAHnxLw2PHyVcQgO8qamEJbcM_y28XcqSwE'
    async with TelegramClient(bot_id, app_id, api_hash) as client:
        await client.send_message('@antar93', message)


@app.task(name="send_notification")
def run_main(message):
    asyncio.run(main(message))
    #return HttpResponse('ok')