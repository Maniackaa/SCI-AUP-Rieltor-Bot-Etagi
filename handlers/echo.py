import asyncio
import re

from aiogram import Router, F, Bot
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message, CallbackQuery, Chat

from config_data.config import conf
from services.db_func import get_all_lexicon
from services.func import get_or_create_user, write_log, check_user
from services.google_func import add_log_to_gtable


class IsAuthorized(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message, event_from_user, bot: Bot, *args, **kwargs) -> bool:
        if isinstance(message, CallbackQuery):
            message = message.message
        user = check_user(event_from_user.id)
        if user and user.rieltor_code:
            return True
        return False


router: Router = Router()

GROUP_ID = conf.tg_bot.GROUP_ID
GROUP_TYPE = conf.tg_bot.GROUP_TYPE


# Копия сообщения из бота в группу
@router.message(F.chat.type == 'private', F.text)
async def send_message_to_group(message: Message, bot: Bot):
    print('send_message_to_group')
    print(message)
    if len(message.text) > 4000:
        return await message.reply(text='123')
    user = get_or_create_user(message.from_user)
    await bot.send_message(
        chat_id=GROUP_ID,
        # chat_id='EtagiManagers',
        text=(
            f'{message.text}\n\n'
            f'#id{message.from_user.id}\n'
            f'{user.fio}'
        ),
        parse_mode='HTML'
    )
    log_text = f'{message.from_user.username or message.from_user.id} {user.rieltor_code} написал в чат: {message.text}'
    write_log(user.id, log_text)
    await add_log_to_gtable(user, log_text)


def extract_user_id(message: Message) -> int:
    if message.text:
        text = message.text
    else:
        text = message.caption
    # user_id = int(text.split(sep='#id')[-1])
    user_id = re.findall(r'#id(\d+).*', text)[0]
    print('extract_user_id:', user_id)
    return user_id


@router.message(Command(commands="info"),
                F.chat.type == GROUP_TYPE,
                F.reply_to_message)
async def get_user_info(message: Message, bot: Bot):
    print('get_user_info')
    def get_name(chat: Chat):
        if not chat.first_name:
            return ""
        if not chat.last_name:
            return chat.first_name
        return f"{chat.first_name} {chat.last_name}"

    try:
        user_id = extract_user_id(message.reply_to_message)
    except ValueError as err:
        return await message.reply(str(err))

    try:
        user = await bot.get_chat(user_id)
    except TelegramAPIError as err:
        await message.reply(
            text=(f'Невозможно найти пользователя с таки Id. Текст ошибки:\n'
                  f'{err.message}')
        )
        return

    username = f"@{user.username}" if user.username else "отсутствует"
    await message.reply(text=f'Имя: {get_name(user)}\n'
                             f'Id: {user.id}\n'
                             f'username: {username}')

# Перехват ответа в группе и пересылка пользователю
@router.message(F.chat.type == GROUP_TYPE, F.reply_to_message)
async def send_message_answer(message: Message, bot: Bot):
    print('send_message_answer')
    print('message.chat:', message.chat)
    print('chat.id:', message.chat.id)
    print(message)
    print('reply text:', message.reply_to_message.text)
    print('msg text:', message.text)
    print('message_thread_id:', message.message_thread_id)
    try:
        chat_id = extract_user_id(message.reply_to_message)
        # await message.copy_to(chat_id)

        text = message.reply_to_message.text
        part = re.findall(r'(#id\d+).*', text)[0]
        reply_text = text.partition(part)[0]
        await bot.send_message(chat_id=chat_id,
                               text=f'{message.text}\n\n'
                                    f'<code>Ваш вопрос:\n{reply_text}</code>'
                               )
        user = check_user(chat_id)
        log_text = f'{message.text}  {user.rieltor_code}'
        write_log(user.id, log_text)
        await add_log_to_gtable(user, log_text)

    except ValueError as err:
        await message.reply(text=f'Не могу извлечь Id.  Возможно он '
                                 f'некорректный. Текст ошибки:\n'
                                 f'{str(err)}')


class SupportedMediaFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        print('__call__')
        return message.content_type in (
            ContentType.ANIMATION, ContentType.AUDIO, ContentType.DOCUMENT,
            ContentType.PHOTO, ContentType.VIDEO, ContentType.VOICE
        )


@router.message(SupportedMediaFilter(), F.chat.type == 'private')
async def supported_media(message: Message):
    print('supported_media')
    if message.caption and len(message.caption) > 1000:
        return await message.reply(text='Слишком длинное описание. Описание '
                                        'не может быть больше 1000 символов')
    else:
        await message.copy_to(
            chat_id=GROUP_ID,
            caption=((message.caption or "") +
                     f"\n\n#id{message.from_user.id}"),
            parse_mode="HTML"
        )
        user = get_or_create_user(message.from_user)
        log_text = f'{message.caption}'
        write_log(user.id, log_text)

        await add_log_to_gtable(user, log_text)


# Последний эхо-фильтр
@router.message()
async def send_echo(message: Message):
    print('echo message:', message)

@router.callback_query()
async def send_echo(callback: CallbackQuery):
    print('echo callback:', callback.data)


