import asyncio
import datetime

from lexicon import lexicon

from database.db import User, Lexicon
from services.db_func import get_today_users, get_all_users

from config_data.config import LOGGING_CONFIG
import logging.config

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')


def find_users_to_send() -> list[tuple[str, User, str]]:
    """
    Находит список юзеров, которым сегодня нужна рассылка.
    :return: [('date1', User, text), ]
    """
    today_date = datetime.date.today()
    users_to_send = get_today_users(today_date)
    """{'date1': [3. 585896156 AlexxxNik82, ...], 'date2': [], 'date3': [],
     'date4': [], 'date5': [], 'date6': [], 'day1': []...
     }"""
    tasks_to_send = []  # (date_num, user, text)
    for column_name, users in users_to_send.items():
        for user in users:
            if user:
                print(f'{column_name}_text')
                text = Lexicon.get(
                    f'{column_name}_text') or 'Текст отсутствует'
                tasks_to_send.append((column_name, user, text))
    return tasks_to_send


def find_10days_users() -> list[tuple[str, User, str]]:
    """
    Находит список новеньких юзеров 10 дней, которым сегодня нужна рассылка.
    :return: [('day1', User, text), ]
    """
    today_date = datetime.date.today()
    users_to_send = get_today_users(today_date)
    tasks_to_send = []  # (date_num, user, text)
    for date_num, users in users_to_send.items():
        for user in users:
            if user:
                text = Lexicon.get(
                    f'{date_num}_text') or 'Текст отсутствует'
                tasks_to_send.append((date_num, user, text))
    return tasks_to_send


def find_users_to_send_report() -> list[User]:
    """
    Находит список юзеров, которым нужна рассылка статистики.
    :return:
    """
    users_to_send = get_all_users()
    logger.info(f'Пользователи для рассылки репорта: {users_to_send}')
    return users_to_send

# x = find_users_to_send()
# print(x)