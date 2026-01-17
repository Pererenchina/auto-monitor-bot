"""
Обработчики состояний FSM для ввода параметров фильтра
"""
# Стандартная библиотека
from typing import TYPE_CHECKING

# Сторонние библиотеки
from aiogram import Dispatcher
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

# Локальные импорты
from keyboards import get_filter_keyboard
from states import FilterStates

if TYPE_CHECKING:
    from db_manager import DBManager


def register_state_handlers(dp: Dispatcher, db_manager: 'DBManager') -> None:
    """Регистрация обработчиков состояний FSM"""
    
    @dp.message(StateFilter(FilterStates.waiting_brand))
    async def process_brand(message: Message, state: FSMContext):
        """Обработка ввода марки"""
        await state.update_data(brand=message.text)
        data = await state.get_data()
        await message.answer(
            f"✅ Марка установлена: {message.text}",
            reply_markup=get_filter_keyboard(data.get('filter_id'))
        )
        await state.set_state(None)
    
    @dp.message(StateFilter(FilterStates.waiting_model))
    async def process_model(message: Message, state: FSMContext):
        """Обработка ввода модели (только если выбрана марка)"""
        data = await state.get_data()
        brand = data.get("brand")
        brand_key = data.get("brand_key")
        
        # Проверяем, выбрана ли марка
        if not brand and not brand_key:
            await message.answer(
                "❌ Сначала выберите марку автомобиля!\n"
                "Используйте кнопку 'Марка' в меню фильтра."
            )
            return
        
        # Сохраняем модель
        await state.update_data(model=message.text)
        data = await state.get_data()
        brand_display = brand or "выбранной марки"
        await message.answer(
            f"✅ Модель установлена: {message.text} ({brand_display})",
            reply_markup=get_filter_keyboard(data.get('filter_id'))
        )
        await state.set_state(None)
    
    @dp.message(StateFilter(FilterStates.waiting_year_from))
    async def process_year_from(message: Message, state: FSMContext):
        """Обработка ввода года от"""
        try:
            year = int(message.text)
            if 1900 <= year <= 2030:
                await state.update_data(year_from=year)
                data = await state.get_data()
                await message.answer(
                    f"✅ Год ОТ установлен: {year}",
                    reply_markup=get_filter_keyboard(data.get('filter_id'))
                )
            else:
                await message.answer("❌ Год должен быть от 1900 до 2030")
        except ValueError:
            await message.answer("❌ Введите корректный год (число)")
        await state.set_state(None)
    
    @dp.message(StateFilter(FilterStates.waiting_year_to))
    async def process_year_to(message: Message, state: FSMContext):
        """Обработка ввода года до"""
        try:
            year = int(message.text)
            if 1900 <= year <= 2030:
                await state.update_data(year_to=year)
                data = await state.get_data()
                await message.answer(
                    f"✅ Год ДО установлен: {year}",
                    reply_markup=get_filter_keyboard(data.get('filter_id'))
                )
            else:
                await message.answer("❌ Год должен быть от 1900 до 2030")
        except ValueError:
            await message.answer("❌ Введите корректный год (число)")
        await state.set_state(None)
    
    @dp.message(StateFilter(FilterStates.waiting_price_from))
    async def process_price_from(message: Message, state: FSMContext):
        """Обработка ввода цены от"""
        try:
            price = float(message.text)
            if price > 0:
                await state.update_data(price_from_usd=price)
                data = await state.get_data()
                await message.answer(
                    f"✅ Цена ОТ установлена: ${price:.0f}",
                    reply_markup=get_filter_keyboard(data.get('filter_id'))
                )
            else:
                await message.answer("❌ Цена должна быть больше 0")
        except ValueError:
            await message.answer("❌ Введите корректную цену (число)")
        await state.set_state(None)
    
    @dp.message(StateFilter(FilterStates.waiting_price_to))
    async def process_price_to(message: Message, state: FSMContext):
        """Обработка ввода цены до"""
        try:
            price = float(message.text)
            if price > 0:
                await state.update_data(price_to_usd=price)
                data = await state.get_data()
                await message.answer(
                    f"✅ Цена ДО установлена: ${price:.0f}",
                    reply_markup=get_filter_keyboard(data.get('filter_id'))
                )
            else:
                await message.answer("❌ Цена должна быть больше 0")
        except ValueError:
            await message.answer("❌ Введите корректную цену (число)")
        await state.set_state(None)
