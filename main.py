import logging
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from aiogram.utils import executor


# инициализируем бота и хранилище состояний
bot = Bot("6178523486:AAHYatLOHjaLa2UMjyZ2gXGF_lwsHP-VKLQ", parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# инициализируем базу данных
DATABASE = 'orders.db'


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'price INTEGER, article TEXT, photo_id TEXT)')
    conn.commit()
    conn.close()


def save_order(price, article, photo_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (price, article, photo_id) VALUES (?, ?, ?)',
                   (price, article, photo_id))
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
    await message.answer('Привет! Это тестовый бот для заказа товаров. '
                         'Напишите /order, чтобы начать оформление заказа.')


# создаем обработчик команды /order
@dp.message_handler(commands=['order'])
async def process_order_command(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(types.KeyboardButton('Отмена'))
    await message.answer('Введите цену товара:', reply_markup=markup)

    # устанавливаем состояние "цена"
    await OrderForm.price.set()


# создаем обработчик кнопки "Отмена"
@dp.message_handler(Text(equals='Отмена', ignore_case=True), state='*')
async def process_cancel_command(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    await state.finish()

    # удалить клавиатуру
    markup = types.ReplyKeyboardRemove()
    await message.answer('Отменено.', reply_markup=markup)


# создаем обработчик состояния "цена"
@dp.message_handler(lambda message: not message.text.isdigit(), state=OrderForm.price)
async def process_order_step1_invalid(message: types.Message):
    await message.answer('Цена должна быть числом. Попробуйте еще раз.')


@dp.message_handler(lambda message: message.text.isdigit(), state=OrderForm.price)
async def process_order_step1(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['price'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(types.KeyboardButton('Отмена'))
    await message.answer('Введите артикул товара:', reply_markup=markup)

    # устанавливаем состояние "артикул"
    await OrderForm.article.set()


# создаем обработчик состояния "артикул"
@dp.message_handler(state=OrderForm.article)
async def process_order_step2(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['article'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(types.KeyboardButton('Оплатить'))
    markup.add(types.KeyboardButton('Отмена'))
    await message.answer('Вы заказываете товар за {price} рублей, с артикулом {article}. '
                         'Нажмите кнопку "Оплатить", чтобы перейти к оплате.'
                         .format(price=data['price'], article=data['article']),
                         reply_markup=markup)

    # устанавливаем состояние "оплата"
    await OrderForm.payment.set()


# создаем обработчик кнопки "Оплатить"
@dp.message_handler(Text(equals='Оплатить', ignore_case=True), state=OrderForm.payment)
async def process_order_step3(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        price = data['price']
        article = data['article']

    await bot.send_message(message.chat.id, 'Сделайте оплату на номер карты: 1234 5678 9012 3456')

    # сохраняем заказ в базе данных
    save_order(price, article, '')

    # завершаем процесс заказа
    await state.finish()


# создаем обработчик фото
@dp.message_handler(content_types=types.ContentType.PHOTO, state=OrderForm.payment)
async def process_order_step4(message: types.Message, state: FSMContext):
    # сохраняем фото в файл
    photo_id = message.photo[-1].file_id
    file_path = await bot.get_file(photo_id)
    file = await bot.download_file(file_path.file_path)

    # сохраняем заказ в базе данных
    async with state.proxy() as data:
        price = data['price']
        article = data['article']
    save_order(price, article, photo_id)

    # завершаем процесс заказа
    await state.finish()

    await bot.send_message(message.chat.id, 'Спасибо за оплату. Ваш заказ принят и будет обработан в ближайшее время.')


if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
