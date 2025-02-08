import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.bot import DefaultBotProperties

# Настройки логирования
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения
DATE = os.getenv("DATE", "Не указано")
TIME = os.getenv("TIME", "Не указано")
PLACE = os.getenv("PLACE", "Не указано")
PLAYERS_COUNT = os.getenv("PLAYERS_COUNT", "Не указано")
PRICE = os.getenv("PRICE", "Не указано")
EVENT_TEXT = os.getenv("EVENT_TEXT", "Описание мероприятия отсутствует")

# Получаем токен и ID чата
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

# Список администраторов
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='Markdown'))
dp = Dispatcher()

# Храним список игроков и зрителей
players = []
spectators = []
registration_open = True  # Флаг доступности записи

# Функция для клавиатуры
def get_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Записаться", callback_data="join")],
        [InlineKeyboardButton(text="👀 Записаться зрителем", callback_data="spectate")],
        [InlineKeyboardButton(text="❌ Удалить запись", callback_data="leave")]
    ] if registration_open else [[InlineKeyboardButton(text="🚫 Запись закрыта", callback_data="disabled")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Функция для генерации списка участников
def generate_list():
    text = (
        f"📅 **Дата:** {DATE}\n"
        f"⏰ **Время:** {TIME}\n"
        f"📍 **Место:** {PLACE}\n"
        f"👥 **Количество игроков:** {PLAYERS_COUNT}\n"
        f"💵 **Цена участия:** {PRICE}\n\n"
        f"{EVENT_TEXT}\n\n"
    )

    if players:
        text += "**🎭 Игроки:**\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(players)) + "\n\n"
    else:
        text += "**🎭 Игроки:**\n⛔ Пока никто не записался.\n\n"

    if spectators:
        text += "**👀 Зрители:**\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(spectators)) + "\n"
    else:
        text += "**👀 Зрители:**\n⛔ Пока никто не записался.\n"

    return text

# Обработчик команды /start – включает запись
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    global registration_open
    if message.chat.id != CHAT_ID:
        return
    registration_open = True
    await bot.send_message(CHAT_ID, "✅ Запись **открыта**!", reply_markup=get_keyboard())

# Обработчик команды /stop – отключает запись, но список сохраняется
@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 У вас нет прав для этой команды.")
        return

    global registration_open
    registration_open = False
    await bot.send_message(CHAT_ID, "🚫 **Запись закрыта!**", reply_markup=get_keyboard())

# Обработчик команды /list – выводит текущий список
@dp.message(Command("list"))
async def list_handler(message: types.Message):
    await message.answer(generate_list())

# Обработчик кнопки "Записаться"
@dp.callback_query(F.data == "join")
async def join_game(callback: types.CallbackQuery):
    if not registration_open:
        await callback.answer("🚫 Запись закрыта!", show_alert=True)
        return

    user_name = callback.from_user.full_name
    if user_name not in players:
        players.append(user_name)
        if user_name in spectators:
            spectators.remove(user_name)
        await bot.send_message(CHAT_ID, generate_list(), reply_markup=get_keyboard())

    await callback.answer("✅ Вы записаны как игрок!")

# Обработчик кнопки "Записаться зрителем"
@dp.callback_query(F.data == "spectate")
async def spectate_game(callback: types.CallbackQuery):
    if not registration_open:
        await callback.answer("🚫 Запись закрыта!", show_alert=True)
        return

    user_name = callback.from_user.full_name
    if user_name not in spectators:
        spectators.append(user_name)
        if user_name in players:
            players.remove(user_name)
        await bot.send_message(CHAT_ID, generate_list(), reply_markup=get_keyboard())

    await callback.answer("👀 Вы записаны как зритель!")

# Обработчик кнопки "Удалить запись"
@dp.callback_query(F.data == "leave")
async def leave_game(callback: types.CallbackQuery):
    logging.info(f"🔄 Получен callback: {callback.data} от {callback.from_user.full_name}")

    user_name = callback.from_user.full_name
    if user_name in players:
        players.remove(user_name)
    if user_name in spectators:
        spectators.remove(user_name)

    await bot.send_message(CHAT_ID, generate_list(), reply_markup=get_keyboard())
    await callback.answer("🚫 Вы удалены из списка.")

# Логирование всех callback-запросов (для диагностики)
@dp.callback_query()
async def debug_callback(callback: types.CallbackQuery):
    logging.info(f"⚠️ Бот получил callback: {callback.data}")
    await callback.answer("🔍 Callback получен, но не обработан.")

# Обработчик команды /reset (только для администратора)
@dp.message(Command("reset"))
async def reset_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 У вас нет прав для этой команды.")
        return

    players.clear()
    spectators.clear()
    await bot.send_message(CHAT_ID, "🗑 Список участников очищен!", reply_markup=get_keyboard())

# Основная функция
async def main():
    logging.info("🚀 Бот запущен! Ожидание событий...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
