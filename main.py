import logging
import sqlite3
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from aiogram.utils import executor

# Создаем ссылку на менеджера
manager_username = "@123"
manager_link = f'<a href="tg://user?id={manager_username}">{manager_username}</a>'

# инициализируем бота и хранилище состояний
bot = Bot("TOKEN", parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# инициализируем базу данных
DATABASE = 'orders.db'

# Определяем кнопки
price_btn = KeyboardButton('Узнать стоимость в рублях💰')
contact_btn = KeyboardButton('Связаться с менеджером📞')
order_btn = KeyboardButton('Сделать заказ📦')

# menu_btn = KeyboardButton('Вернуться в меню')

# Создаем объект ReplyKeyboardMarkup и добавляем кнопки
markup = ReplyKeyboardMarkup(
    keyboard=[
        [
            price_btn,
            order_btn
        ],
        [
            contact_btn
        ]
    ],
    resize_keyboard=True
)  # menu_btn


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR, user_id INTEGER, price DECIMAL, article TEXT)')
    conn.commit()
    conn.close()


def save_order(username, user_id, price, article):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (username, user_id, price, article) VALUES (?, ?, ?, ?)',
                   (username, user_id, price, article))
    conn.commit()
    conn.close()


# создаем класс формы заказа
class OrderForm(StatesGroup):
    price = State()
    article = State()
    payment = State()


# создаем обработчик команды /start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.answer('Приветствую! Это тестовый бот для заказа товаров. '
                         'Нажмите кнопку <b>"Сделать заказ"</b>, чтобы начать оформление заказа.', reply_markup=markup, parse_mode='HTML')


# # Создаем обработчик для кнопки "Вернуться в меню"
# @dp.message_handler(Text(equals='Вернуться в меню'))
# async def return_to_menu(message: types.Message):
#     # Отправляем сообщение со всеми доступными кнопками
#     await message.answer(
#         "Выберите действие:",
#         reply_markup=ReplyKeyboardMarkup(
#             keyboard=[
#                 [
#                     KeyboardButton(text="Узнать стоимость"),
#                     KeyboardButton(text="Связаться с менеджером"),
#                 ],
#                 [
#                     KeyboardButton(text="Сделать заказ"),
#                 ],
#             ],
#             resize_keyboard=True,
#         ),
#     )


# Создаем обработчик для кнопки "Связаться с менеджером"
@dp.message_handler(Text(equals='Связаться с менеджером📞'))
async def ask_price(message: types.Message):
    await message.answer(
        f"Если у вас возникли какие-нибудь вопросы, то можете задать их нашему менеджеру <b>{manager_link}</b>",
        parse_mode='HTML'
    )


# создаем обработчик кнопки заказа
@dp.message_handler(Text(equals='Сделать заказ📦'))
async def process_order_command(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(types.KeyboardButton('Отмена'))
    await message.answer('Введите цену товара <b>в юанях:</b>', reply_markup=markup, parse_mode='HTML')

    # устанавливаем состояние "цена"
    await OrderForm.price.set()


# создаем обработчик кнопки "Отмена"
@dp.message_handler(Text(equals='Отмена', ignore_case=True), state='*')
async def process_cancel_command(message: types.Message, state: StatesGroup):  # state: FSMContext
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    await state.finish()

    # удалить клавиатуру
    # markup = types.ReplyKeyboardRemove()
    await message.answer('Отменено. Нажмите кнопку <b>"Сделать заказ"</b>, чтобы начать оформление заказа.',
                         reply_markup=markup, parse_mode='HTML')


# создаем обработчик состояния "цена"
@dp.message_handler(lambda message: not message.text.isdigit(), state=OrderForm.price)
async def process_order_step1_invalid(message: types.Message):
    await message.answer('Цена должна быть числом. Попробуйте еще раз.')


@dp.message_handler(lambda message: message.text.isdigit(), state=OrderForm.price)
async def process_order_step1(message: types.Message, state: StatesGroup):
    async with state.proxy() as data:
        data['price'] = round(int(message.text) * 12.7, 2)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(types.KeyboardButton('Отмена'))
    await message.answer('Введите артикул товара:', reply_markup=markup)

    # устанавливаем состояние "артикул"
    await OrderForm.article.set()


# создаем обработчик состояния "артикул"
@dp.message_handler(state=OrderForm.article)
async def process_order_step2(message: types.Message, state: StatesGroup):
    async with state.proxy() as data:
        data['article'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(types.KeyboardButton('Оплатить'))
    markup.add(types.KeyboardButton('Отмена'))
    await message.answer('Вы заказываете товар за <b>{price} рублей</b>, с артикулом <b>{article}</b>. '
                         'Нажмите кнопку "Оплатить", чтобы перейти к оплате.'
                         .format(price=round(data['price'], 2), article=data['article']),
                         reply_markup=markup, parse_mode='HTML')

    # устанавливаем состояние "оплата"
    await OrderForm.payment.set()


# создаем обработчик кнопки "Оплатить"
@dp.message_handler(Text(equals='Оплатить', ignore_case=True), state=OrderForm.payment)
async def process_order_step3(message: types.Message, state: StatesGroup):  # state: FSMContext
    # async with state.proxy() as data:
    #     price = data['price']
    #     article = data['article']

    await bot.send_message(message.chat.id,
                           'Произведите оплату переводом на номер карты: <b>1234 5678 9012 3456</b>, а затем отправьте мне скриншот, подтверждающий оплату')

    # сохраняем заказ в базе данных
    # save_order(price, article, '')

    # завершаем процесс заказа
    # await state.finish()
    await OrderForm.payment.set()


# создаем обработчик фото
@dp.message_handler(content_types=types.ContentType.PHOTO, state=OrderForm.payment)
async def process_order_step4(message: types.Message, state: StatesGroup):  # state: FSMContext
    # сохраняем фото в файл
    # photo_id = message.photo[-1].file_id
    # file_path = await bot.get_file(photo_id)
    # file = await bot.download_file(file_path.file_path)

    # сохраняем заказ в базе данных
    async with state.proxy() as data:
        price = data['price']
        article = data['article']
    save_order(message.from_user.username, message.from_user.id, price, article)

    # завершаем процесс заказа
    await state.finish()

    ##### ЛЕНЯ ВОТ ТУТ АЙДИШНИК ТИПА КОТОРОМУ НУЖНО ПЕРЕСЛАТЬ
    await bot.forward_message(chat_id=497731774, from_chat_id=message.chat.id, message_id=message.message_id)
    await bot.send_message(chat_id=497731774, text=f'никнейм - {message.from_user.username}\nайди - {message.from_user.id}\nцена в руб - {price}\nартикул - {article}')
    await bot.send_message(chat_id=497731774, text='----------------------')

    await message.answer('Спасибо за оплату. Ваш заказ принят и будет обработан в ближайшее время.\nОжидайте, скоро с вами свяжется наш менеджер',
                         reply_markup=markup)


# Создаем обработчик для кнопки "Узнать стоимость"
@dp.message_handler(Text(equals='Узнать стоимость в рублях💰'))
async def ask_price(message: types.Message):
    # Сохраняем состояние в FSM
    # await OrderForm.price.set()
    await message.answer("Введите стоимость товара:")


# создаем обработчик состояния "цена"
@dp.message_handler(lambda message: not message.text.isdigit())
async def process_order_step_invalid(message: types.Message):
    await message.answer('Цена должна быть числом. Попробуйте еще раз.')


@dp.message_handler(lambda message: message.text.isdigit())
async def process_order_step(message: types.Message):
    price = int(message.text)
    # Умножаем цену на 10
    price *= 12.7

    # Отправляем ответ и сбрасываем состояние FSM
    await message.answer(f"Стоимость товара: <b>{round(price, 2)}</b>руб", parse_mode='HTML')


if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
