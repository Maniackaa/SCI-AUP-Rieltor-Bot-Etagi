import asyncio

from aiogram import Dispatcher, types, Router, Bot, F
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart, Text, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, URLInputFile

from aiogram.fsm.context import FSMContext

from database.db import Lexicon

from keyboards.keyboards import csi_kb, yes_no_kb

from config_data.config import LOGGING_CONFIG, conf
import logging.config

from services.db_func import save_csi, save_csi_comment, report
from services.func import get_or_create_user, write_log
from services.google_func import add_log_to_gtable

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')

router: Router = Router()


class FSMCSI(StatesGroup):
    CSI_comment_yes_no = State()
    CSI_comment = State()


async def send_text_to_users(bot: Bot, tasks, type_date):
    """
    Функция отправки утреннего сообщения
    :param bot:
    :param tasks: [('date1', User, text), ]
    :param type_date: 'day' / 'date'
    :return:
    """
    for task in tasks:
        date_num = task[0]
        user = task[1]
        text = task[2]
        if date_num.startswith(type_date):
            try:
                await bot.send_message(user.tg_id, text.format(user.fio.split()[1]))
                await asyncio.sleep(0.1)
                logger.info(f'Утреннее сообщение {date_num}  для {user} отправлено')
            except TelegramForbiddenError:
                logger.warning(f'Утреннее сообщение {date_num}  для {user} НЕ отправлено, так как пользователь заблокировал бота')
            except Exception as err:
                err_log.error(f'Утреннее сообщение {date_num}  для {user} не отправлено', exc_info=True)


async def send_csi_to_users(bot: Bot, tasks, type_date):
    """
    Функция отправки анкеты CSI через бота
    :param bot:
    :param tasks: [('date1', User, text), ]
    :param type_date: 'day' / 'date'
    :return:
    """
    for task in tasks:
        date_num = task[0]
        user = task[1]
        text = task[2]
        if date_num.startswith(type_date):
            try:
                await bot.send_message(user.tg_id, text.format(user.fio.split()[1]),
                                       reply_markup=csi_kb(1, date_num))
                await asyncio.sleep(0.1)
                logger.info(f'Сообщение CSI {date_num}  для {user} отправлено')
            except TelegramForbiddenError:
                logger.warning(f'Сообщение CSI {date_num}  для {user} НЕ отправлено, так как пользователь заблокировал бота')
            except Exception as err:
                err_log.error(f'Сообщение CSI {date_num}  для {user} не отправлено', exc_info=True)


@router.callback_query(Text(startswith='CSI_answer:'))
async def csi_answer(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатываем оценку CSI
    :param callback:
    :return:
    """
    user = get_or_create_user(callback.from_user)
    name = user.fio.split()[1]
    message_text = callback.message.text
    date_num = callback.data.split(':')[1]
    csi_point = int(callback.data.split(':')[2])
    await callback.message.edit_text(message_text + f'\nВаша оценка: {csi_point}')
    if csi_point >= 4:
        await callback.message.answer(Lexicon.get('csi_4_5_text').format(name))
    elif csi_point < 4:
        await callback.message.answer(Lexicon.get('csi_1_3_text').format(name))
    save_csi(date_num, user, csi_point)
    log_text = f'{user.fio}. Проведена оценка недели {date_num}: {csi_point}'
    write_log(user.id, log_text)
    # await callback.message.answer('Желаете оставить комментрий к вашей оценке?', reply_markup=yes_no_kb(2))
    # await state.update_data(user=user, date_num=date_num)
    # await state.set_state(FSMCSI.CSI_comment_yes_no)
    await add_log_to_gtable(user, log_text)
    await report()


# Обработка yes/no
@router.callback_query(StateFilter(FSMCSI.CSI_comment_yes_no))
async def csi_answer(callback: CallbackQuery, state: FSMContext):
    if callback.data == 'yes':
        await callback.message.answer('Напишите ваш комментарий:')
        await callback.message.delete()
        await state.set_state(FSMCSI.CSI_comment)
    else:
        await callback.message.delete()
        await state.clear()


# Сохраняем комментарий
@router.message(StateFilter(FSMCSI.CSI_comment), F.content_type == ContentType.TEXT)
async def process_menu(message: Message, state: FSMContext):
    comment = message.text
    data = await state.get_data()
    user = data['user']
    date_num = data['date_num']
    save_csi_comment(date_num, user, comment)
    log_text = f'Оставлен комментарий: {comment}'
    write_log(user.id, log_text)
    await state.clear()
    await message.answer('Спасибо!')
    await add_log_to_gtable(user, log_text)
    await report()
