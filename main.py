import asyncio
import datetime

import aioschedule
from aiogram import Bot, Dispatcher

from config_data.config import LOGGING_CONFIG, conf
from handlers import user_handlers, echo, csi_handlers

import logging.config

from handlers.csi_handlers import send_csi_to_users, send_text_to_users
from lexicon.lexicon import LEXICON
from services.CSI import find_users_to_send
from services.db_func import delete_user_from_codes

from services.google_func import get_codes_to_delete

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')


async def day_job(bot):
    # Отправка утреннего текста
    tasks = find_users_to_send()
    logger.debug(f'Сегодня найдены пользовтаели для рассылки утреннего текста:\n{tasks}')
    await send_text_to_users(bot, tasks, 'date')


async def csi_day_job(bot):
    # Запрос анкетирования CSI
    users_to_send = find_users_to_send()
    logger.debug(f'Сегодня найдены пользовтаели для рассылки CSI day:\n{users_to_send}')
    await send_csi_to_users(bot, users_to_send, 'day')


async def delete_user(bot):
    logger.info('Удаляем польззователей')
    codes_to_del = await get_codes_to_delete()
    logger.debug(f'Найдено пользователей: {codes_to_del}')
    del_count = delete_user_from_codes(codes_to_del)
    logger.info(f'Удалено: {del_count}')


async def test(bot):
    await bot.send_message(chat_id=conf.tg_bot.GROUP_ID, text=str(datetime.datetime.now()))


async def shedulers(bot):
    # aioschedule.every(5).minutes.do(job, bot)
    time_start1 = '5:00'
    aioschedule.every().day.at(time_start1).do(day_job, bot)
    aioschedule.every().day.at('14:00').do(csi_day_job, bot)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def main():
    logger.info('Starting bot Etagi')
    bot: Bot = Bot(token=conf.tg_bot.token, parse_mode='HTML')
    dp: Dispatcher = Dispatcher()

    # Регистриуем
    dp.include_router(user_handlers.router)
    dp.include_router(csi_handlers.router)
    dp.include_router(echo.router)
    asyncio.create_task(shedulers(bot))
    # await day_job(bot)
    # await csi_day_job(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await bot.send_message(
            conf.tg_bot.admin_ids[0], f'Бот АУП Этажи запущен.')
    except Exception:
        err_log.critical(f'Не могу отравить сообщение {conf.tg_bot.admin_ids[0]}')
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot stopped!')
