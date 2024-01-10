import asyncio
import datetime

import gspread
import gspread_asyncio
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials


from config_data.config import BASE_DIR, conf
from database.db import User, History


from config_data.config import LOGGING_CONFIG
import logging.config

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')


def get_creds():
    # To obtain a service account JSON file, follow these steps:
    # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
    json_file = BASE_DIR / 'credentials.json'
    creds = Credentials.from_service_account_file(json_file)
    scoped = creds.with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    return scoped


async def load_range_values(url=conf.tg_bot.USER_TABLE_URL, sheets_num=0, diap='А:А'):
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    url = url
    sheet = await agc.open_by_url(url)
    table = await sheet.get_worksheet(sheets_num)
    values = await table.get_values(diap)
    return values


async def read_user_from_table():
    json_file = BASE_DIR / 'credentials.json'
    gc = gspread.service_account(filename=json_file)
    url = conf.tg_bot.USER_TABLE_URL
    sheet = gc.open_by_url(url)
    table = sheet.get_worksheet(0)
    # values = table.get_values('A:D')[2:]
    values = await load_range_values(diap="A:F")
    values = values[1:]
    # logger.debug(f'values: {values}')
    users = {}

    for row in values:
        try:
            # logger.debug(f'row: {row}')
            rieltor_code = row[0]
            phone = row[1] or '-'
            fio = row[2] or '-'
            first_day = row[3] or '01.01.1999'
            first_day = datetime.datetime.strptime(first_day, '%d.%m.%Y')
            city = row[4]
            is_delete = bool(row[5])
            users[rieltor_code] = {
                'phone': phone,
                'fio': fio,
                'date1': first_day,
                'is_delete': is_delete,
                'city': city
            }

        except Exception as err:
            err_log.error(f'Ошибка при чтении строки {row}: {err}')
    return users


async def write_to_table(rows: list[list], start_row=1, from_start=False, url=conf.tg_bot.USER_TABLE_URL,
                          sheets_num=0, delta_col=0):
    """
    Запись строк в гугл-таблицу
    :param rows: список строк для вставки
    :param start_row: Номер первой строки
    :from_start: Вписывать в начало?
    :param url: адрес таблицы
    :param sheets_num: номер листа
    :param delta_col: смещение по столбцам
    :return:
    """
    try:
        if not rows:
            return
        logger.debug(f'Добавляем c {start_row}: {rows}')
        agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
        agc = await agcm.authorize()
        sheet = await agc.open_by_url(url)
        table = await sheet.get_worksheet(sheets_num)
        # await table.append_rows(rows)
        num_rows = len(rows)
        num_col = len(rows[0])

        if from_start:
            logger.debug(f'Вписываем в начало: {len(rows)} строк')
            await table.insert_rows(values=rows[::-1], row=2)
        else:
            logger.debug(
                f'{rowcol_to_a1(start_row, 1 + delta_col)}:{rowcol_to_a1(start_row + num_rows, num_col + delta_col)}')
            result = await table.batch_update([{
                'range': f'{rowcol_to_a1(start_row, 1 + delta_col)}:{rowcol_to_a1(start_row + num_rows, num_col + delta_col)}',
                'values': rows,
            }])
            # logger.debug(f'{result}')
        return True
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)
        raise err


async def write_stats_from_table(rows):
    """
    Экспортирует данные пользователей User в таблицу сбор CSI
    :param rows:
    :return:
    """
    # logger.debug(f'Добавляем {rows}')
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    agc = await agcm.authorize()
    url = conf.tg_bot.USER_TABLE_URL
    sheet = await agc.open_by_url(url)
    table = await sheet.get_worksheet(1)
    # await table.append_rows(rows)
    num_rows = len(rows)
    num_col = len(rows[0])
    logger.debug(f'{rowcol_to_a1(2 , 1)}:{rowcol_to_a1(1 + num_rows, num_col)}')
    await table.batch_update([{
        'range': f'{rowcol_to_a1(2 , 1)}:{rowcol_to_a1(1 + num_rows, num_col)}',
        'values': rows,
    }])


async def add_log_to_gtable(user: User, text: str):
    """
    Сохраняет движения пользователя в таблицу Логи
    :param user:
    :param text:
    :return:
    """
    logger.debug(f'Добавляем history в таблицу: {text}')
    return
    # try:
    #     logger.debug(f'Добавляем history в таблицу: {text}')
    #     agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    #     agc = await agcm.authorize()
    #     url = conf.tg_bot.USER_TABLE_URL
    #     sheet = await agc.open_by_url(url)
    #     table = await sheet.get_worksheet(2)
    #     await table.append_row([
    #         datetime.datetime.now().isoformat(sep=' ')[:-7],
    #         user.username,
    #         text])
    # except Exception as err:
    #     logger.debug(err)


async def get_codes_to_delete() -> set[str]:
    # Если в столбце AZ есть значение, считаем что удалять
    all_users = await load_range_values(diap='A:AZ')
    all_users = all_users[2:]
    codes_to_delete = set()
    for user in all_users:
        if user[-1]:
            codes_to_delete.add(user[0])
    return codes_to_delete


async def main():
    x = await read_user_from_table()
    print(x)
    for key, val in x.items():
        print(key, val)
        if key == '1245785663':
            print(val)

if __name__ == '__main__':
    asyncio.run(main())
