import asyncio
import datetime
import logging

from sqlalchemy import func, update, delete, select

from database.db import User, Session, Lexicon

from config_data.config import LOGGING_CONFIG
import logging.config

from services.google_func import write_stats_from_table

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')


def get_today_users(day) -> dict[str, list[User | None]]:
    """
    Возвращает словарь date1-date7 со списком юзеров
     у которых сегодня дата опроса.
    :param day: сегодняшний день
    :return: {'date1': [3. 585896156 AlexxxNik82], 'date2': [], 'date3': [],
     'date4': [], 'date5': [], 'date6': [], 'day1': []...
     }
    """

    user_days_dict = {}
    session = Session()
    with session:
        # user_days_dict['date1'] = session.query(User).filter(User.date1 == day).all()
        # user_days_dict['date2'] = session.query(User).filter(User.date2 == day).all()
        # user_days_dict['date3'] = session.query(User).filter(User.date3 == day).all()
        # user_days_dict['date4'] = session.query(User).filter(User.date4 == day).all()
        # user_days_dict['date5'] = session.query(User).filter(User.date5 == day).all()
        # user_days_dict['date6'] = session.query(User).filter(User.date6 == day).all()
        for i in range(1, 8):
            user_days_dict[f'date{i}'] = session.query(User).filter(getattr(User, f'date{i}') == day).filter(User.date1.is_not(None)).all()
        for i in range(1, 6):
            user_days_dict[f'day{i}'] = session.query(User).filter(getattr(User, f'day{i}') == day).filter(User.date1.is_not(None)).all()
    return user_days_dict

# print(get_today_users(datetime.datetime.now().date()))

# def get_10days_users(day: datetime.date) -> dict[str, list[User | None]]:
#     """
#     Возвращает словарь date1-date6 со списком юзеров
#      у которых сегодня дата опроса.
#     :param day: сегодняшний день
#     :return: {'date1': [3. 585896156 AlexxxNik82], 'date2': [], 'date3': [],
#      'date4': [], 'date5': [], 'date6': []
#      }
#     """
#     logger.debug(f'Ищем 10 days за {str(day)}')
#     user_days_dict = {}
#     session = Session()
#     with session:
#         for i in range(1, 11):
#             user_days_dict[f'day{i}'] = session.query(User).filter(User.date1 == day + datetime.timedelta(days=14 - i)).all()
#             for user in user_days_dict[f'day{i}']:
#                 print(i)
#                 print(user, user.date1)
#             print()
#     logger.debug(user_days_dict)
#     return user_days_dict
#
# print(get_10days_users(datetime.datetime.now().date()))

def get_all_users() -> list[User]:
    session = Session()
    with session:
        users = session.query(User).filter(User.rieltor_code.is_not(None)).all()
        return users


def save_csi(date_num, user, csi_point):
    """
    Сохранение CSI полльзователя
    :param date_num:
    :param user:
    :param csi_point:
    :return:
    """
    logger.debug(f'Сохраняем оценку пользователя {user}: {date_num} - {csi_point}')
    session = Session()
    with session:
        user_db = session.query(User).filter(User.id == user.id).first()
        setattr(user_db, f'{date_num}_csi', int(csi_point))
        session.commit()


def save_csi_comment(date_num, user, comment):
    """
    Сохраняет комментарий к CSI
    :param date_num:
    :param user:
    :param comment:
    :return:
    """
    logger.debug(f'Сохраняем коммент пользователя {user}: {date_num} - {comment}')
    session = Session()
    with session:
        user_db = session.query(User).filter(User.id == user.id).first()
        setattr(user_db, f'{date_num}_comment', comment)
        session.commit()


def get_users_to_send_message() -> list[User]:
    """Достает всех юзеров с базы"""
    session = Session()
    with session:
        user_db = session.query(User).filter(User.rieltor_code.is_not(None)).all()
    return user_db


def get_un_users() -> list[User]:
    """Достает Неавторизованных пользователей"""
    session = Session()
    with session:
        user_db = session.query(User).filter(User.rieltor_code.is_(None)).all()
    return user_db


async def report():
    """
    Выгрузка отчета с User в виде строк.
    :return:
    """
    session = Session()
    with session:
        all_users = session.query(User).all()
    report_key = ['tg_id', 'username', 'rieltor_code', 'fio']
    for i in range(1, 6):
        report_key.extend((f'date{i}', f'day{i}_csi'))

    report_rows = []
    for user in all_users:
        row = []
        for key in report_key:
            value = getattr(user, str(key), '----') or '----'
            if isinstance(value, datetime.date):
                value = value.strftime('%Y-%m-%d')
            row.append(value)
        report_rows.append(row)
    await write_stats_from_table(report_rows)
    return report_rows


def get_user_from_rieltor_code(rieltor_code) -> User:
    """Находит юзера по коду риалтора"""
    try:
        logger.debug(f'Ищем rieltor_code  {rieltor_code}')
        rieltor_code = str(rieltor_code)
        with Session() as session:
            user = session.query(User).filter(User.rieltor_code == rieltor_code).first()
            logger.debug(f'Найдено: {user}')
        return user
    except Exception as err:
        logger.error(err)


def get_user_from_rieltor_codes(rieltor_codes: list | set) -> list[User]:
    """Находит юзера по сиписку кодов риалторов"""
    try:
        logger.debug(f'Ищем rieltor_code  {rieltor_codes}')
        rieltor_codes = [str(val) for val in rieltor_codes]
        logger.debug(rieltor_codes)
        with Session() as session:
            users = session.query(User).filter(User.rieltor_code.in_(rieltor_codes)).all()
            logger.debug(f'Найдено: {users}')
        return users
    except Exception as err:
        logger.error(err)


def read_lexicon_from_db():
    session = Session()
    with session:
        all_rows = session.query(Lexicon).order_by(Lexicon.id).all()
        return all_rows


def clear_rieltor_code(rieltor_codes: list | set):
    """Очищает rieltor_code в user"""
    try:
        session = Session()
        commands = {'rieltor_code': None, 'fio': None}
        for i in range(1, 7):
            commands[f'date{i}'] = None
        for i in range(1, 11):
            commands[f'day{i}'] = None
        with session:
            # users = session.query(User).filter(User.rieltor_code.in_(rieltor_codes)).all()
            result = session.query(User).where(User.rieltor_code.in_(rieltor_codes)).update(commands)
            session.commit()
            return result
    except Exception as err:
        logger.error(err)


def delete_user_from_codes(rieltor_codes: list | set):
    """Удаляет пользователей из базы"""
    try:
        session = Session()
        commands = {'rieltor_code': None, 'fio': None}
        for i in range(1, 7):
            commands[f'date{i}'] = None
        for i in range(1, 11):
            commands[f'day{i}'] = None
        with session:
            # users = session.query(User).filter(User.rieltor_code.in_(rieltor_codes)).all()
            # result = session.query(User).where(User.rieltor_code.in_(rieltor_codes)).update(commands)
            # result = session.query(User).where(User.rieltor_code.in_(rieltor_codes)).delete()
            users = select(User).where(User.rieltor_code.in_(rieltor_codes))

            res = session.execute(users).scalars().all()
            logger.debug(f'Удаляем пользователей: {res}')
            stmt = delete(User).where(User.rieltor_code.in_(rieltor_codes))
            session.execute(stmt)
            session.commit()
            return len(res)
    except Exception as err:
        logger.error(err)


def delete_user_from_tg_id(tg_id):
    """Удаляем пользователя из базы"""
    try:
        session = Session()
        tg_id = str(tg_id)
        with session:
            logger.debug(f'Удаляем пользователя c tg_id: {tg_id}')
            stmt = delete(User).where(User.tg_id == tg_id)
            session.execute(stmt)
            session.commit()
            logger.debug(f'Пользователь {tg_id} удален из базы')
            return True
    except Exception as err:
        logger.error(f'Ошибка удаления пользователя: {err}')

if __name__ == '__main__':
    asyncio.run(report())
    # clear_rieltor_code(['1241424124124124124124'])
    # x = delete_user_from_codes(['55022', '1231215807', '1231217761', '1231221311'])
    # print(x)
    pass

