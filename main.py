from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

bot_token = '6178523486:AAHYatLOHjaLa2UMjyZ2gXGF_lwsHP-VKLQ'
bot = Bot(token=bot_token)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    chat_id = (await bot.get_updates())[0].message.chat.id
    await bot.send_message(chat_id=chat_id, text="Привет!\nЯ бот от quality box")
    await bot.send_message(chat_id=chat_id, text="Введите стоимость товара:")


@dp.message_handler(regexp=r'^\d+$')
async def calculate(message: types.Message):
    number = int(message.text)
    result = number * 11.9 + 1990
    await message.reply(f"Итоговая стоимость {result}.")
# DICK

if __name__ == '__main__':
    executor.start_polling(dp)
