"""
Состояния FSM для бота
"""
# Сторонние библиотеки
from aiogram.fsm.state import State, StatesGroup


class FilterStates(StatesGroup):
    """Состояния для настройки фильтров"""
    waiting_brand = State()
    waiting_model = State()
    waiting_year_from = State()
    waiting_year_to = State()
    waiting_price_from = State()
    waiting_price_to = State()
    waiting_transmission = State()
    waiting_engine_type = State()
    waiting_body_type = State()
