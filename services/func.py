import asyncio
import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from database.db import Session, User, Menu, History
from config_data.config import LOGGING_CONFIG, conf

import logging.config

from services.db_func import delete_user_from_tg_id
from services.google_func import add_log_to_gtable

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')


def check_user(id):
    """Возвращает найденных пользователей по tg_id"""
    logger.debug(f'Ищем юзера {id}')
    with Session() as session:
        user: User = session.query(User).filter(User.tg_id == str(id)).first()
        logger.debug(f'Результат: {user}')
        return user


def get_or_create_user(user) -> User:
    """Из юзера ТГ возвращает сущестующего User ли создает его"""
    try:
        tg_id = user.id
        username = user.username
        logger.debug(f'username {username}')
        old_user = check_user(tg_id)
        if old_user:
            logger.debug('Пользователь есть в базе')
            return old_user
        logger.debug('Добавляем пользователя')
        with Session() as session:
            new_user = User(tg_id=tg_id,
                            username=username,
                            register_date=datetime.datetime.now()
                            )
            session.add(new_user)
            session.commit()
            logger.debug(f'Пользователь создан: {new_user}')
        return new_user
    except Exception as err:
        err_log.error('Пользователь не создан', exc_info=True)


def update_user(tg_id, rieltor_code, g_user):
    """
    заполняем user при авторизации
    :g_user: {'123456': {'phone': '79236396010', 'fio': 'Тестовый Админ Админыч', 'date1': datetime.datetime(2024, 1, 8, 0, 0), 'is_delete': False, 'city': ''}}
    """
    try:
        logger.debug(f'Обновляем user {(tg_id, rieltor_code, g_user)}')
        session = Session()
        with session:
            user: User = session.query(User).filter(User.tg_id == str(tg_id)).first()
            user.rieltor_code = rieltor_code
            for key, val in g_user.items():
                setattr(user, key, val)
            # Обновляем date2, date3....
            date1 = g_user['date1']
            day_delta = [1, 7, 9, 14, 34, 56]
            for day_num, val in enumerate(day_delta, 2):
                setattr(user, f'date{day_num}', date1 + datetime.timedelta(days=val))

            day_delta = [0, 14, 21, 42, 49]
            # Обновляем даты опросов da1, day2....
            for day_num, val in enumerate(day_delta, 1):
                setattr(user, f'day{day_num}', date1 + datetime.timedelta(days=val))
            logger.debug(f'Юзер обновлен {user}')
            session.commit()
    except Exception as err:
        logger.error(f'Ошибка обновления юзера: {err}')


def get_menu_from_index(index) -> Menu:
    session = Session()
    with session:
        menu: Menu = session.query(Menu).filter(Menu.index == index).first()
        return menu


def get_index_menu_from_text(text) -> str:
    """Достает индекс из меню по тексту"""
    if text == '⇤ Назад':
        return '0'
    session = Session()
    with session:
        menu: Menu = session.query(Menu).filter(Menu.text == text).first()
        return menu.index


def write_log(user_id, text):
    session = Session()
    with session:
        history: History = History(user_id=user_id, text=text, time=datetime.datetime.now())
        session.add(history)
        session.commit()


def get_history(limit):
    session = Session()
    with session:
        historys = session.query(History).order_by(History.id.desc()).limit(limit).all()
        logger.debug(historys)
        return historys


async def send_message_to_manager(bot, user, text_msg):
    await bot.send_message(
        chat_id=config.tg_bot.GROUP_ID,
        # chat_id='EtagiManagers',
        text=(
            f'{text_msg}\n\n'
            f'#id{user.tg_id}\n'
            f'{user.fio}'
        ),
        parse_mode='HTML'
    )


async def send_report_to_users(users_to_send: list[User], bot: Bot):
    user_stats = await read_stats_from_table()
    for user in users_to_send:
        try:
            if user.rieltor_code in user_stats:
                logger.debug(f'Стата пользователя {user} найдена')
                text = format_user_sats(user_stats[user.rieltor_code],
                                        user_stats['date'])
                if text != '*показатели обновляются раз в неделю по понедельникам':
                    await bot.send_message(user.tg_id, text)
                    await asyncio.sleep(0.1)
                    logger.info(f'Сообщение пользователю {user.fio or user.tg_id} отправлено')
        except TelegramForbiddenError as err:
            logger.warning(f'Ошибка отправки сообщения для {user}: {err}')
            logger.info('Удаляем пользователя из базы')
            delete_user_from_tg_id(user.tg_id)
            log_text = f'Пользователь {user} удален из базы из-за {err}'
            logger.info(log_text)
            write_log(user.id, log_text)
            await add_log_to_gtable(user, log_text)
        except Exception as err:
            # await bot.send_message(config.tg_bot.admin_ids[0], 'Сообщение пользователю {user.fio or user.tg_id} НЕ отправлено')
            logger.error(f'ошибка отправки сообщения пользователю {user}: {err}', exc_info=False)
            err_log.error(f'ошибка отправки сообщения пользователю {user}: {err}', exc_info=True)
