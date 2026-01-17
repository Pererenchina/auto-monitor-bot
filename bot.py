"""
Telegram-бот для мониторинга объявлений о продаже автомобилей
"""
# Стандартная библиотека
from typing import Optional

# Сторонние библиотеки
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Локальные импорты
from config import BOT_TOKEN
from db_manager import DBManager
from handlers import register_command_handlers, register_callback_handlers, register_state_handlers

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_manager = DBManager()

# Регистрация обработчиков
register_command_handlers(dp, db_manager)
register_callback_handlers(dp, db_manager)
register_state_handlers(dp, db_manager)
