import asyncio
import datetime
import sys

from sqlalchemy import create_engine, ForeignKey, Date, String, DateTime, \
    Float, UniqueConstraint, Integer
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils.functions import database_exists, create_database


from config_data.config import conf
from lexicon.lexicon import LEXICON

db_url = f"postgresql+psycopg2://{conf.db.db_user}:{conf.db.db_password}@{conf.db.db_host}:{conf.db.db_port}/{conf.db.database}"
engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    tg_id: Mapped[str] = mapped_column(String(30))

    username: Mapped[str] = mapped_column(String(50), nullable=True)
    rieltor_code: Mapped[str] = mapped_column(String(50), nullable=True)
    register_date: Mapped[datetime.datetime] = mapped_column(DateTime(), nullable=True)
    fio: Mapped[str] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(50), nullable=True)
    date1: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    date2: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    date3: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    date4: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    date5: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    date6: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    date7: Mapped[datetime.date] = mapped_column(Date(), nullable=True)

    day1: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    day2: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    day3: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    day4: Mapped[datetime.date] = mapped_column(Date(), nullable=True)
    day5: Mapped[datetime.date] = mapped_column(Date(), nullable=True)

    day1_csi: Mapped[int] = mapped_column(Integer(), nullable=True)
    day2_csi: Mapped[int] = mapped_column(Integer(), nullable=True)
    day3_csi: Mapped[int] = mapped_column(Integer(), nullable=True)
    day4_csi: Mapped[int] = mapped_column(Integer(), nullable=True)
    day5_csi: Mapped[int] = mapped_column(Integer(), nullable=True)
    history = relationship(
        "History",
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )

    def __repr__(self):
        return f'{self.id}. {self.tg_id} {self.username or "-"} {self.fio}'


class Menu(Base):
    __tablename__ = 'menu_items'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    text: Mapped[str] = mapped_column(String(100), default='-')
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete='CASCADE'), default=None, nullable=True)
    is_with_children: Mapped[int] = mapped_column(
        Integer(), server_default='0', nullable=False)
    index: Mapped[str] = mapped_column(String(20))
    answer: Mapped[str] = mapped_column(String(4000), nullable=True)

    def __repr__(self):
        return f'{self.index}: {self.text} parent_id: {self.parent_id} is_with_children: {self.is_with_children}'

    def navigation(self):
        print(self.parent_id)
        session = Session()
        with session:
            parent_menu: Menu = session.query(Menu).filter(Menu.id == self.parent_id).one_or_none()
            print('parent_menu:', parent_menu)
        if parent_menu:
            return f'| {parent_menu.text} > {self.text}'
        else:
            return f'| {self.text}'

    @staticmethod
    def get_items(parent=None):
        _session = Session()
        with _session:
            if parent == 'all':
                _menu_items = session.query(Menu).filter().all()
            else:
                _menu_items = session.query(Menu).filter(Menu.parent_id == parent).all()
            return _menu_items


class History(Base):
    __tablename__ = 'history'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete='CASCADE'))
    user = relationship("User", back_populates="history")
    time: Mapped[datetime.datetime] = mapped_column(DateTime())
    text: Mapped[str] = mapped_column(String(250), nullable=True)

    def __repr__(self):
        return f'{str(self.time)[:-7]}: {self.text}'


class BotSettings(Base):
    __tablename__ = 'bot_settings'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    name: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(50), nullable=True, default='')
    description: Mapped[str] = mapped_column(String(255),
                                             nullable=True,
                                             default='')


class Lexicon(Base):
    __tablename__ = 'lexicon'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    name: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(String(4000))

    @staticmethod
    def get(key_name):
        _session = Session()
        try:
            with _session:
                lexicon = _session.query(Lexicon).filter(Lexicon.name == key_name).one_or_none()
                if lexicon:
                    value = lexicon.text
                    return value
        except Exception as err:
            raise err


if not database_exists(db_url):
    create_database(db_url)
Base.metadata.create_all(engine)


# Заполнение пустой базы
# [индекс, текст, ролитель, есть ли дети?, ответ]
start_menu_list = [
    ['1', 'Хочу задать вопрос', None, 0, """Запрос принят.
В ближайшее время оператор свяжется с вами, для уточнения деталей."""],
    ['2', 'Хочу поделиться обратной связью', None, 0, 'Заполните поле для обратной связи'],
    ['3', 'Полезные ссылки  ➡', None, 1, None],

        ['3_1', 'Страница "Адаптация АУП"', 3, 0, 'https://lp.etagi.com/adaptatia'],
        ['3_2', 'Бонусы для сотрудников', 3, 0, 'https://docs.google.com/presentation/d/1EbHV5buPIrh5a-kmQJueB7kEpdbqQ4Ft_3k1smtp630/edit#slide=id.p'],
        ['3_3', 'Сервис "Между нами"', 3, 0, 'https://feedback.etagi.com/'],
        ['3_4', 'Хочу порекомендовать сотрудника', 3, 0, 'Витрина вакансий: https://ecosystem.etagi.com/hr/jobshowcase             '],
        ['3_5', 'Ссылка на фотографирование', 3, 0, 'https://docs.google.com/presentation/d/1k5aG9vYSlM3eO8TExB5-bkeqcJNrQErse1A_hYVg4U0/edit#slide=id.p'],
        ['3_6', 'Ссылка для заказа бейджа', 3, 0, 'https://docs.google.com/forms/d/1N48LslOzT7UbiUW6nTJx-p4KyEMlXd4nruXkqTf_aS8/viewform?edit_requested=true'],
        ['3_7', 'Грабли HR', 3, 0, 'https://t.me/rabotaetagi'],

]

unauth_message = """Добро пожаловать в чат-бот по адаптации новых сотрудников! 🚀

Прежде всего, поздравляем тебя с присоединением к нашей команде! Мы готовы помочь вам с невероятным началом вашего пути в нашей компании.

Давай начнем с небольшой регистрации. Для авторизации поделись контактом через кнопку ниже.

Если у тебя есть какие-либо вопросы или ты нуждаешься в дополнительной информации, не стесняйся спрашивать. Мы здесь, чтобы твое введение в компанию было максимально комфортным и продуктивным!

С наилучшими пожеланиями,
HR-Департамент."""

first_message = """Чтобы твое пребывание в компании было максимально эффективным, перед началом работы обязательно пройди следующие этапы:
1) Изучи наш <a href="https://lp.etagi.com/adaptatia">сайт для адаптации</a> сотрудников, там ты найдешь информацию о компании, её офисах, а также ответы на часто задаваемые вопросы и множество полезных ссылок
2) Пройди регистрацию в корпоративной почте - <a href="https://docs.google.com/document/d/1CK1IQRADBBzfEmbBMDDQ64Jx2Jmx0UfkaTjVp7iqheY/edit#heading=h.gjdgxs">Инструкция</a>
3) В нашей компании прнят дресс-код, обязательно изучи его перед первым рабочим днём
4) Зарегистрируйся в корпоративном чат-боте, туда тебе будут приходить все важные уведомления - <a href="https://docs.google.com/presentation/d/1_d0-OQzMTFnidN0O-mJShA9-AwrrIhdCAr45PggW5lc/edit#slide=id.p">Инструкция</a>
5) Подпишись на телеграм-канал ""Грабли HR"" чтобы быть в курсе всех последних событий нашей насыщенной корпоративной жизни <a href="https://t.me/rabotaetagi">Ссылка</a>"""

date1_text = """
Мы  хотим чтобы твой первый день прошел максимально продуктивно и интересно, поэтому рекомендуем тебе выполнить несколько простых задач:

1. Познакомься с <a href="http://education.etagi.com/home">Учебным порталом</a> и изучи свою программу обучения.
2. Познакомься с организационной структурой тюменского офиса и компании в целом на нашей <a href="https://lp.etagi.com/adaptatia">адаптационной платформе</a>.
3. Совместно с руководителем ознакомься и разбери свой план адаптации  (необходимо запросить у руководителя).
4. Для сотрудников нашей компании разработана специальная бонусная программа, там есть скидки на различные категории от бизнес-ланчей до фитнес-клубов. <a href="https://docs.google.com/presentation/d/1EbHV5buPIrh5a-kmQJueB7kEpdbqQ4Ft_3k1smtp630/edit#slide=id.p">Подробнее по ссылке</a>Подробнее по ссылке.

Я знаю, что тебе уже не терпиться подписать договор. Чтобы получить подробную информацию по данному вопросу, свяжись с ответственными сотрудниками:
Мишина Алена - она работает по адресу ул. Ленина 38/1
Гебель Мария - она работает по адресу ул. Суходольская, д. 16.


А еще у нас есть для тебя подарок, чтобы забрать welcome-box отпишитесь hr-специалисту, который вас курирует."""

date2_text = """Привет, давай обсудим некоторые организационные вопросы.

1) Фотографирование
В телефонном справочнике компании можно найти каждого сотрудника по ФИО или номеру телефона. У каждого сотрудника в справочнике есть фотография.
Сфотографироваться в нашу внутреннюю систему необходимо в течении первых 2-х недель (<a href="http://education.etagi.com/home">график фотографирования</a>)

2) Рекомендуй и получай бонус
Вы можете порекомендовать сотрудника на любую вакантную должность в нашей компании и получить денежное вознаграждение за прием и успешную адаптацию сотрудника.
Информацию по открытым вакансиям и суммам бонуса можно узнать на <a href="https://ecosystem.etagi.com/hr/jobshowcase">Витрине вакансий</a>

3) Сервис ""Между нами""
Анонимный сервис отзывов и предложений для сотрудников и партнеров компании.
Хочешь поделиться мнением о работе в компании — <a href="https://feedback.etagi.com/">жми сюда</a>.

4)Заказ бейджа
Пластиковый бейдж изготавливается за счет компании не более 2-х шт. в год. Срок изготовления 3-5 рабочих дней
По готовности каждому сотруднику будет направлено уведомление на электронную почту.
Для новичков бейдж изготавливается по истечению месяца работы. 
Заказать бейдж можно <a href="https://docs.google.com/forms/d/1N48LslOzT7UbiUW6nTJx-p4KyEMlXd4nruXkqTf_aS8/viewform?edit_requested=true">по ссылке</a>"""

date3_text = """Привет, поздравляю тебя с первой неделей в компании. Поделись своими эмоциями и ощущениями от работы у нас пройдя небольшой <a href="https://forms.gle/xep3Mzhq7QKJvxQu7">опрос</a>."""

date4_text = """Напоминаю, что для всех новых сотрудников компании, hr-департамент проводит welcome-встречу. Мы уже добавилии ее в твой календарь, ознакомься с датой и временем проведения встречи и подтверди её. Если появились вопросы, обращайся к своему курирующему hr-специалисту."""

date5_text = """Рекомендуй и получай бонус.
Ты можешь порекомендовать сотрудника на любую вакантную должность в нашей компании и получить денежное вознаграждение за прием и успешную адаптацию сотрудника.
Информацию по открытым вакансиям и суммам бонуса можно узнать на Витрине вакансий."""

date6_text = """Ты с нами уже месяц! Пройди <a href="https://forms.gle/V5sVj5DroiCtNyKV8">опрос</a> и расскажи о своих успехах и переживаниях."""

date7_text = """Поздравляем, твоя адаптация успешно движется к логическому завершению. Поделись обратной связью в этом <a href="https://forms.gle/4sGRKwq4njGTkJPX7">опросе</a>."""


start_text = LEXICON['/start']

csi_question = """Расскажи как прошла твоя неделя.


5 - ОТЛИЧНО - все было отлично, сложностей нет 
4 - ХОРОШО - все было хорошо, но иногда возникали сложности, которые не сразу удавалось решить 
3 - НОРМАЛЬНО - не все процессы проходили по плану.
2 - НАД ЭТИМ СТОИТ ПОРАБОТАТЬ - не все прошло по плану и есть сложности, которые не удалось решить 
1 - ПРОЦЕСС НЕ ОРГАНИЗОВАН - процесс не организован, есть сложности """

day1_text = """Расскажи как прошел твой первый день.


5 - ОТЛИЧНО - все было отлично, сложностей нет 
4 - ХОРОШО - все было хорошо, но иногда возникали сложности, которые не сразу удавалось решить 
3 - НОРМАЛЬНО - не все процессы проходили по плану.
2 - НАД ЭТИМ СТОИТ ПОРАБОТАТЬ - не все прошло по плану и есть сложности, которые не удалось решить 
1 - ПРОЦЕСС НЕ ОРГАНИЗОВАН - процесс не организован, есть сложности """

day2_text = """Расскажи как прошла твоя неделя.


5 - ОТЛИЧНО - все было отлично, сложностей нет 
4 - ХОРОШО - все было хорошо, но иногда возникали сложности, которые не сразу удавалось решить 
3 - НОРМАЛЬНО - не все процессы проходили по плану.
2 - НАД ЭТИМ СТОИТ ПОРАБОТАТЬ - не все прошло по плану и есть сложности, которые не удалось решить 
1 - ПРОЦЕСС НЕ ОРГАНИЗОВАН - процесс не организован, есть сложности """


csi_1_3_text = """Спасибо за обратную связь! Скоро с тобой свяжется курирующий hr для уточнения деталей"""
csi_4_5_text = """Мы рады, что процесс адаптации идет успешно! Помни, что ты всегда можешь обратиться за помощью через командное меню.
Желаем успехов!"""

empty_base = {
    '/start': first_message,
    'unauth_message': unauth_message,
    'first_message': first_message,
    'phone_request_text': 'Для авторизации поделитесь контактом через кнопку ниже ↓',
    'welcome_message_phone_text': 'welcome_message_phone_text',
    'authorisation_error_phone_text': 'Номер телефона не найден, напишите ваш код сотрудника',
    'welcome_message_code_text': 'welcome_message_code_text',
    'authorisation_error_code_text': 'Код сотрудника не найден. Попробуйте вести код еще раз, или обратитесь к администратору',
    'menu_text': 'Главное меню',
    'menu_select': 'menu_select',

    'csi_question': csi_question,
    'csi_1_3_text': csi_1_3_text,
    'csi_4_5_text': csi_4_5_text,

    'date1_text': date1_text,
    'date2_text': date2_text,
    'date3_text': date3_text,
    'date4_text': date4_text,
    'date5_text': date5_text,
    'date6_text': date6_text,
    'date7_text': date7_text,

    'day1_text': day1_text,
    'day2_text': day2_text,
    'day3_text': day2_text,
    'day4_text': day2_text,
    'day5_text': day2_text,

}

session = Session()
with session:
    menu_items = session.query(Menu).all()
    print(menu_items)
    if not menu_items:
        for item_menu in start_menu_list:
            menu = Menu(
                index=item_menu[0],
                text=item_menu[1],
                parent_id=item_menu[2],
                is_with_children=item_menu[3],
                answer=item_menu[4]
                        )
            session.add(menu)
            session.commit()

    lexicon_items = session.query(Lexicon).all()
    print(lexicon_items)
    if not lexicon_items:
        for key in empty_base.keys():

            print(key, empty_base.get(key) or key)
            menu = Lexicon(name=key,
                           text=empty_base.get(key) or key)
            session.add(menu)
        session.commit()
