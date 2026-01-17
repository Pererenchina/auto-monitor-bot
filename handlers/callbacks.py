"""
Обработчики callback-запросов бота
"""
# Стандартная библиотека
from typing import Optional, TYPE_CHECKING

# Сторонние библиотеки
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

# Локальные импорты
from config import BRANDS, BRAND_MODELS, BODY_TYPES
from keyboards import (
    get_main_keyboard, get_filter_keyboard, get_brand_keyboard,
    get_model_keyboard, get_transmission_keyboard, get_engine_type_keyboard,
    get_body_type_keyboard, get_year_from_keyboard, get_year_to_keyboard,
    get_price_from_keyboard, get_price_to_keyboard
)
from states import FilterStates
from utils.formatters import format_filter_text

if TYPE_CHECKING:
    from db_manager import DBManager


def register_callback_handlers(dp: Dispatcher, db_manager: 'DBManager') -> None:
    """Регистрация обработчиков callback-запросов"""
    
    @dp.callback_query(F.data == "help")
    async def callback_help(callback: CallbackQuery):
        """Обработчик кнопки помощи (для обратной совместимости)"""
        await callback.message.edit_text(
            "ℹ️ Помощь по использованию бота:\n\n"
            "1. Добавьте фильтр через меню\n"
            "2. Настройте параметры поиска\n"
            "3. Сохраните фильтр\n"
            "4. Получайте уведомления о новых объявлениях!"
        )
        await callback.message.answer(
            "Используйте кнопки внизу для навигации:",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
    
    @dp.callback_query(F.data == "add_filter")
    async def callback_add_filter(callback: CallbackQuery, state: FSMContext):
        """Обработчик создания нового фильтра (возврат к меню создания)"""
        try:
            await state.clear()
            await state.update_data(filter_id=None)
            await callback.message.edit_text(
                "⚙️ Настройте параметры фильтра:\n\n"
                "Выберите параметр для настройки:",
                reply_markup=get_filter_keyboard(None)
            )
            await callback.answer()
        except Exception as e:
            print(f"Ошибка в callback_add_filter: {e}")
            await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)
    
    @dp.callback_query(F.data.startswith("edit_filter_"))
    async def callback_edit_filter(callback: CallbackQuery, state: FSMContext):
        """Редактировать существующий фильтр (только свой)"""
        try:
            filter_id = int(callback.data.split("_")[-1])
            user_id = callback.from_user.id
            
            # Проверяем, что фильтр принадлежит пользователю
            filter_obj = await db_manager.get_filter_by_id(filter_id, user_id)
            
            if not filter_obj:
                await callback.answer("❌ Фильтр не найден или у вас нет доступа к нему!", show_alert=True)
                return
            
            # Сохраняем текущие значения фильтра в state для редактирования
            await state.update_data(
                filter_id=filter_id,
                brand=filter_obj.brand,
                model=filter_obj.model,
                year_from=filter_obj.year_from,
                year_to=filter_obj.year_to,
                price_from_usd=filter_obj.price_from_usd,
                price_to_usd=filter_obj.price_to_usd,
                transmission=filter_obj.transmission,
                engine_type=filter_obj.engine_type,
                body_type=filter_obj.body_type,
            )
            
            # Используем функцию форматирования для единообразия
            text = "⚙️ <b>Редактирование фильтра</b>:\n\n"
            text += format_filter_text(filter_obj)
            text += "\nВыберите параметр для изменения:"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_filter_keyboard(filter_id),
                parse_mode='HTML'
            )
            await callback.answer()
        except ValueError:
            await callback.answer("❌ Неверный ID фильтра!", show_alert=True)
        except Exception as e:
            print(f"Ошибка в callback_edit_filter: {e}")
            await callback.answer("❌ Произошла ошибка при загрузке фильтра!", show_alert=True)
    
    # ========== Обработчики марки ==========
    @dp.callback_query(F.data.startswith("filter_brand_"))
    async def callback_set_brand(callback: CallbackQuery, state: FSMContext):
        """Установить марку"""
        raw_id = callback.data.split("_")[-1]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        await callback.message.edit_text(
            "Выберите марку автомобиля:",
            reply_markup=get_brand_keyboard(filter_id)
        )
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("input_brand_"))
    async def callback_input_brand(callback: CallbackQuery, state: FSMContext):
        """Перейти к ручному вводу марки"""
        await callback.message.edit_text("Введите марку автомобиля (например: BMW, Mercedes, Toyota):")
        await state.set_state(FilterStates.waiting_brand)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_brand_"))
    async def callback_save_brand(callback: CallbackQuery, state: FSMContext):
        """Сохранить выбранную марку с кнопки"""
        parts = callback.data.split("_")
        # set_brand_<brand_key>_<filter_id>
        brand_key = parts[2]
        raw_id = parts[3]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        # Находим отображаемое название марки
        brand_title = next((title for key, title in BRANDS if key == brand_key), brand_key)
        
        data = await state.get_data()
        if not data.get("filter_id") and filter_id is not None:
            data["filter_id"] = filter_id
        
        data["brand"] = brand_title
        data["brand_key"] = brand_key
        await state.update_data(**data)
        
        await callback.message.edit_text(
            f"✅ Марка установлена: {brand_title}",
            reply_markup=get_filter_keyboard(data.get("filter_id"))
        )
        await callback.answer()
    
    # ========== Обработчики модели ==========
    @dp.callback_query(F.data.startswith("filter_model_"))
    async def callback_set_model(callback: CallbackQuery, state: FSMContext):
        """Установить модель (только после выбора марки)"""
        raw_id = callback.data.split("_")[-1]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        data = await state.get_data()
        brand_key = data.get("brand_key")
        brand = data.get("brand")
        
        # Проверяем, выбрана ли марка
        if not brand_key and not brand:
            await callback.answer(
                "❌ Сначала выберите марку автомобиля!",
                show_alert=True
            )
            return
        
        # Если марка выбрана из списка и для нее есть модели — показываем список моделей
        if brand_key and brand_key in BRAND_MODELS and BRAND_MODELS[brand_key]:
            brand_title = next((t for k, t in BRANDS if k == brand_key), brand_key)
            await callback.message.edit_text(
                f"Выберите модель автомобиля ({brand_title}):",
                reply_markup=get_model_keyboard(brand_key, filter_id)
            )
            await state.set_state(FilterStates.waiting_model)
        else:
            # Если марка введена вручную или нет списка моделей — просим ввести модель вручную
            brand_display = brand or "выбранной марки"
            await callback.message.edit_text(
                f"Введите модель автомобиля для {brand_display} (например: X5, C-Class, Camry):"
            )
            await state.set_state(FilterStates.waiting_model)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("input_model_"))
    async def callback_input_model(callback: CallbackQuery, state: FSMContext):
        """Перейти к ручному вводу модели (только если выбрана марка)"""
        data = await state.get_data()
        brand = data.get("brand")
        brand_key = data.get("brand_key")
        
        # Проверяем, выбрана ли марка
        if not brand and not brand_key:
            await callback.answer(
                "❌ Сначала выберите марку автомобиля!",
                show_alert=True
            )
            return
        
        brand_display = brand or "выбранной марки"
        await callback.message.edit_text(
            f"Введите модель автомобиля для {brand_display} (например: X5, C-Class, Camry):"
        )
        await state.set_state(FilterStates.waiting_model)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_model_"))
    async def callback_save_model(callback: CallbackQuery, state: FSMContext):
        """Сохранить выбранную модель с кнопки (только если выбрана марка)"""
        parts = callback.data.split("_")
        # set_model_<brand_key>_<idx>_<filter_id>
        brand_key = parts[2]
        idx = int(parts[3])
        raw_id = parts[4]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        # Проверяем, что марка соответствует
        data = await state.get_data()
        current_brand_key = data.get("brand_key")
        current_brand = data.get("brand")
        
        if not current_brand_key and not current_brand:
            await callback.answer(
                "❌ Сначала выберите марку автомобиля!",
                show_alert=True
            )
            return
        
        # Проверяем соответствие марки (если brand_key указан в callback)
        if current_brand_key and current_brand_key != brand_key:
            await callback.answer(
                "❌ Модель не соответствует выбранной марке!",
                show_alert=True
            )
            return
        
        models = BRAND_MODELS.get(brand_key, [])
        if not models or idx < 0 or idx >= len(models):
            await callback.answer("❌ Не удалось определить модель", show_alert=True)
            return
        
        model_title = models[idx]
        
        if not data.get("filter_id") and filter_id is not None:
            data["filter_id"] = filter_id
        
        data["model"] = model_title
        data["brand_key"] = brand_key
        await state.update_data(**data)
        
        brand_title = next((t for k, t in BRANDS if k == brand_key), brand_key)
        await callback.message.edit_text(
            f"✅ Модель установлена: {model_title} ({brand_title})",
            reply_markup=get_filter_keyboard(data.get("filter_id"))
        )
        await callback.answer()
    
    # ========== Обработчики года ==========
    @dp.callback_query(F.data.startswith("filter_year_from_"))
    async def callback_set_year_from(callback: CallbackQuery, state: FSMContext):
        """Установить год от"""
        raw_id = callback.data.split("_")[-1]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        await callback.message.edit_text(
            "Выберите год выпуска ОТ:",
            reply_markup=get_year_from_keyboard(filter_id)
        )
        # Разрешаем как выбор кнопкой, так и ввод текста сразу после этого шага
        await state.set_state(FilterStates.waiting_year_from)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("input_year_from_"))
    async def callback_input_year_from(callback: CallbackQuery, state: FSMContext):
        """Перейти к ручному вводу года ОТ"""
        await callback.message.edit_text("Введите год выпуска ОТ (например: 2015):")
        await state.set_state(FilterStates.waiting_year_from)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_year_from_"))
    async def callback_save_year_from(callback: CallbackQuery, state: FSMContext):
        """Сохранить выбранный год ОТ с кнопки"""
        parts = callback.data.split("_")
        # set_year_from_<year>_<filter_id>
        year = int(parts[3])
        raw_id = parts[4]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        data = await state.get_data()
        if not data.get("filter_id") and filter_id is not None:
            data["filter_id"] = filter_id
        
        data["year_from"] = year
        await state.update_data(**data)
        
        await callback.message.edit_text(
            f"✅ Год ОТ установлен: {year}",
            reply_markup=get_filter_keyboard(data.get("filter_id"))
        )
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("filter_year_to_"))
    async def callback_set_year_to(callback: CallbackQuery, state: FSMContext):
        """Установить год до"""
        raw_id = callback.data.split("_")[-1]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        await callback.message.edit_text(
            "Выберите год выпуска ДО:",
            reply_markup=get_year_to_keyboard(filter_id)
        )
        # Разрешаем как выбор кнопкой, так и ввод текста сразу после этого шага
        await state.set_state(FilterStates.waiting_year_to)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("input_year_to_"))
    async def callback_input_year_to(callback: CallbackQuery, state: FSMContext):
        """Перейти к ручному вводу года ДО"""
        await callback.message.edit_text("Введите год выпуска ДО (например: 2023):")
        await state.set_state(FilterStates.waiting_year_to)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_year_to_"))
    async def callback_save_year_to(callback: CallbackQuery, state: FSMContext):
        """Сохранить выбранный год ДО с кнопки"""
        parts = callback.data.split("_")
        # set_year_to_<year>_<filter_id>
        year = int(parts[3])
        raw_id = parts[4]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        data = await state.get_data()
        if not data.get("filter_id") and filter_id is not None:
            data["filter_id"] = filter_id
        
        data["year_to"] = year
        await state.update_data(**data)
        
        await callback.message.edit_text(
            f"✅ Год ДО установлен: {year}",
            reply_markup=get_filter_keyboard(data.get("filter_id"))
        )
        await callback.answer()
    
    # ========== Обработчики цены ==========
    @dp.callback_query(F.data.startswith("filter_price_from_"))
    async def callback_set_price_from(callback: CallbackQuery, state: FSMContext):
        """Установить цену от"""
        raw_id = callback.data.split("_")[-1]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        await callback.message.edit_text(
            "Выберите цену ОТ в USD:",
            reply_markup=get_price_from_keyboard(filter_id)
        )
        # Разрешаем как выбор кнопкой, так и ввод текста сразу после этого шага
        await state.set_state(FilterStates.waiting_price_from)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("input_price_from_"))
    async def callback_input_price_from(callback: CallbackQuery, state: FSMContext):
        """Перейти к ручному вводу цены ОТ"""
        await callback.message.edit_text("Введите цену ОТ в USD (например: 5000):")
        await state.set_state(FilterStates.waiting_price_from)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_price_from_"))
    async def callback_save_price_from(callback: CallbackQuery, state: FSMContext):
        """Сохранить выбранную цену ОТ с кнопки"""
        parts = callback.data.split("_")
        # set_price_from_<price>_<filter_id>
        price = float(parts[3])
        raw_id = parts[4]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        data = await state.get_data()
        if not data.get("filter_id") and filter_id is not None:
            data["filter_id"] = filter_id
        
        data["price_from_usd"] = price
        await state.update_data(**data)
        
        await callback.message.edit_text(
            f"✅ Цена ОТ установлена: ${price:.0f}",
            reply_markup=get_filter_keyboard(data.get("filter_id"))
        )
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("filter_price_to_"))
    async def callback_set_price_to(callback: CallbackQuery, state: FSMContext):
        """Установить цену до"""
        raw_id = callback.data.split("_")[-1]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        await callback.message.edit_text(
            "Выберите цену ДО в USD:",
            reply_markup=get_price_to_keyboard(filter_id)
        )
        # Разрешаем как выбор кнопкой, так и ввод текста сразу после этого шага
        await state.set_state(FilterStates.waiting_price_to)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("input_price_to_"))
    async def callback_input_price_to(callback: CallbackQuery, state: FSMContext):
        """Перейти к ручному вводу цены ДО"""
        await callback.message.edit_text("Введите цену ДО в USD (например: 20000):")
        await state.set_state(FilterStates.waiting_price_to)
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_price_to_"))
    async def callback_save_price_to(callback: CallbackQuery, state: FSMContext):
        """Сохранить выбранную цену ДО с кнопки"""
        parts = callback.data.split("_")
        # set_price_to_<price>_<filter_id>
        price = float(parts[3])
        raw_id = parts[4]
        filter_id: Optional[int] = None if raw_id == "None" else int(raw_id)
        
        data = await state.get_data()
        if not data.get("filter_id") and filter_id is not None:
            data["filter_id"] = filter_id
        
        data["price_to_usd"] = price
        await state.update_data(**data)
        
        await callback.message.edit_text(
            f"✅ Цена ДО установлена: ${price:.0f}",
            reply_markup=get_filter_keyboard(data.get("filter_id"))
        )
        await callback.answer()
    
    # ========== Обработчики коробки передач ==========
    @dp.callback_query(F.data.startswith("filter_transmission_"))
    async def callback_set_transmission(callback: CallbackQuery, state: FSMContext):
        """Установить коробку передач"""
        filter_id = callback.data.split("_")[-1]
        if filter_id == "None":
            filter_id = None
        else:
            filter_id = int(filter_id)
        
        await callback.message.edit_text(
            "Выберите тип коробки передач:",
            reply_markup=get_transmission_keyboard(filter_id)
        )
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_transmission_"))
    async def callback_save_transmission(callback: CallbackQuery, state: FSMContext):
        """Сохранить коробку передач"""
        parts = callback.data.split("_")
        transmission = parts[2]
        filter_id = parts[3] if parts[3] != "None" else None
        
        data = await state.get_data()
        if not data.get('filter_id') and filter_id:
            data['filter_id'] = filter_id
        
        data['transmission'] = transmission
        await state.update_data(**data)
        
        await callback.message.edit_text(
            f"✅ Коробка передач установлена: {transmission}",
            reply_markup=get_filter_keyboard(data.get('filter_id'))
        )
        await callback.answer()
    
    # ========== Обработчики типа двигателя ==========
    @dp.callback_query(F.data.startswith("filter_engine_type_"))
    async def callback_set_engine_type(callback: CallbackQuery, state: FSMContext):
        """Установить тип двигателя"""
        filter_id = callback.data.split("_")[-1]
        if filter_id == "None":
            filter_id = None
        else:
            filter_id = int(filter_id)
        
        await callback.message.edit_text(
            "Выберите тип двигателя:",
            reply_markup=get_engine_type_keyboard(filter_id)
        )
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_engine_"))
    async def callback_save_engine_type(callback: CallbackQuery, state: FSMContext):
        """Сохранить тип двигателя"""
        parts = callback.data.split("_")
        engine_type = parts[2]
        filter_id = parts[3] if parts[3] != "None" else None
        
        data = await state.get_data()
        if not data.get('filter_id') and filter_id:
            data['filter_id'] = filter_id
        
        data['engine_type'] = engine_type
        await state.update_data(**data)
        
        await callback.message.edit_text(
            f"✅ Тип двигателя установлен: {engine_type}",
            reply_markup=get_filter_keyboard(data.get('filter_id'))
        )
        await callback.answer()
    
    # ========== Обработчики типа кузова ==========
    @dp.callback_query(F.data.startswith("filter_body_type_"))
    async def callback_set_body_type(callback: CallbackQuery, state: FSMContext):
        """Установить тип кузова"""
        filter_id = callback.data.split("_")[-1]
        if filter_id == "None":
            filter_id = None
        else:
            filter_id = int(filter_id)
        
        await callback.message.edit_text(
            "Выберите тип кузова:",
            reply_markup=get_body_type_keyboard(filter_id)
        )
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("set_body_type_"))
    async def callback_save_body_type(callback: CallbackQuery, state: FSMContext):
        """Сохранить тип кузова"""
        # Формат callback_data: set_body_type_{key}_{filter_id}
        # Пример: set_body_type_sedan_None или set_body_type_sedan_123
        # При split("_") получаем: ['set', 'body', 'type', 'sedan', 'None']
        parts = callback.data.split("_")
        if len(parts) >= 5:
            # parts[0]='set', parts[1]='body', parts[2]='type', parts[3]=key, parts[4]=filter_id
            body_type_key = parts[3]  # Ключ типа кузова
            filter_id_str = parts[4]
        elif len(parts) >= 4:
            # Если filter_id отсутствует
            body_type_key = parts[3]
            filter_id_str = "None"
        else:
            # Fallback (не должно происходить)
            body_type_key = parts[-1] if parts else ""
            filter_id_str = "None"
        
        filter_id = None if filter_id_str == "None" else int(filter_id_str)
        
        data = await state.get_data()
        if not data.get('filter_id') and filter_id:
            data['filter_id'] = filter_id
        
        data['body_type'] = body_type_key
        await state.update_data(**data)
        
        # Находим название типа кузова
        body_type_name = next((title for key, title in BODY_TYPES if key == body_type_key), body_type_key)
        await callback.message.edit_text(
            f"✅ Тип кузова установлен: {body_type_name}",
            reply_markup=get_filter_keyboard(data.get('filter_id'))
        )
        await callback.answer()
    
    # ========== Обработчики сохранения и удаления фильтра ==========
    @dp.callback_query(F.data.startswith("save_filter_"))
    async def callback_save_filter(callback: CallbackQuery, state: FSMContext):
        """Сохранить фильтр"""
        try:
            data = await state.get_data()
            filter_id = data.get('filter_id')
            
            filter_data = {
                'brand': data.get('brand'),
                'model': data.get('model'),
                'year_from': data.get('year_from'),
                'year_to': data.get('year_to'),
                'price_from_usd': data.get('price_from_usd'),
                'price_to_usd': data.get('price_to_usd'),
                'transmission': data.get('transmission'),
                'engine_type': data.get('engine_type'),
                'body_type': data.get('body_type'),
            }
            
            # Удаляем None значения
            filter_data = {k: v for k, v in filter_data.items() if v is not None}
            
            # Проверяем, что есть хотя бы один параметр
            if not filter_data:
                await callback.answer("❌ Укажите хотя бы один параметр фильтра!", show_alert=True)
                return
            
            if filter_id:
                # Обновляем существующий фильтр с проверкой владельца
                user_id = callback.from_user.id
                filter_obj = await db_manager.update_user_filter(filter_id, user_id, **filter_data)
                if filter_obj:
                    await callback.message.edit_text(
                        "✅ <b>Фильтр обновлен!</b>\n\n" + format_filter_text(filter_obj),
                        parse_mode='HTML'
                    )
                    # Отправляем сообщение с постоянной клавиатурой
                    await callback.message.answer(
                        "Используйте кнопки внизу для дальнейших действий:",
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await callback.answer("❌ Ошибка: фильтр не найден или у вас нет доступа к нему!", show_alert=True)
                    return
            else:
                # Создаем новый фильтр
                filter_obj = await db_manager.add_user_filter(callback.from_user.id, **filter_data)
                await callback.message.edit_text(
                    f"✅ <b>Фильтр #{filter_obj.id} создан!</b>\n\n" + format_filter_text(filter_obj),
                    parse_mode='HTML'
                )
                # Отправляем сообщение с постоянной клавиатурой
                await callback.message.answer(
                    "Используйте кнопки внизу для дальнейших действий:",
                    reply_markup=get_main_keyboard()
                )
            
            await state.clear()
            await callback.answer()
        except Exception as e:
            print(f"Ошибка в callback_save_filter: {e}")
            await callback.answer("❌ Произошла ошибка при сохранении фильтра!", show_alert=True)
    
    @dp.callback_query(F.data.startswith("delete_filter_"))
    async def callback_delete_filter(callback: CallbackQuery):
        """Удалить фильтр (только свой)"""
        try:
            filter_id = int(callback.data.split("_")[-1])
            user_id = callback.from_user.id
            
            # Удаляем фильтр с проверкой владельца
            success = await db_manager.delete_user_filter(filter_id, user_id)
            
            if success:
                await callback.message.edit_text(
                    "✅ <b>Фильтр удален!</b>",
                    parse_mode='HTML'
                )
                await callback.message.answer(
                    "Используйте кнопки внизу для управления фильтрами:",
                    reply_markup=get_main_keyboard()
                )
            else:
                await callback.answer("❌ Ошибка: фильтр не найден или у вас нет доступа к нему!", show_alert=True)
            
            await callback.answer()
        except ValueError:
            await callback.answer("❌ Неверный ID фильтра!", show_alert=True)
        except Exception as e:
            print(f"Ошибка в callback_delete_filter: {e}")
            await callback.answer("❌ Произошла ошибка при удалении фильтра!", show_alert=True)
    
    @dp.callback_query(F.data == "my_filters")
    async def callback_my_filters(callback: CallbackQuery):
        """Показать мои фильтры (только для текущего пользователя)"""
        try:
            user_id = callback.from_user.id
            # Получаем фильтры только текущего пользователя
            filters = await db_manager.get_user_filters(user_id, active_only=True)
            
            if not filters:
                await callback.message.edit_text(
                    "📋 <b>Ваши фильтры</b>\n\n"
                    "У вас пока нет активных фильтров.\n"
                    "Добавьте первый фильтр через меню!",
                    parse_mode='HTML'
                )
                await callback.message.answer(
                    "Используйте кнопки внизу:",
                    reply_markup=get_main_keyboard()
                )
                await callback.answer()
                return
            
            text = f"📋 <b>Ваши фильтры</b> (найдено: {len(filters)}):\n\n"
            buttons = []
            
            for f in filters:
                text += format_filter_text(f)
                text += "\n"
                buttons.append([InlineKeyboardButton(
                    text=f"✏️ Редактировать фильтр #{f.id}",
                    callback_data=f"edit_filter_{f.id}"
                )])
            
            buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode='HTML'
            )
            # Отправляем сообщение с постоянной клавиатурой для удобства
            await callback.message.answer(
                "Используйте кнопки внизу для навигации:",
                reply_markup=get_main_keyboard()
            )
            await callback.answer()
        except Exception as e:
            print(f"Ошибка в callback_my_filters: {e}")
            await callback.answer("❌ Произошла ошибка при загрузке фильтров!", show_alert=True)
    
    @dp.callback_query(F.data == "back_to_menu")
    async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
        """Вернуться в главное меню"""
        try:
            await state.clear()
            await callback.message.edit_text(
                "🚗 <b>Авто-Монитор</b>\n\n"
                "Используйте кнопки внизу для навигации:",
                parse_mode='HTML'
            )
            await callback.message.answer(
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
            await callback.answer()
        except Exception as e:
            print(f"Ошибка в callback_back_to_menu: {e}")
            await callback.answer("Произошла ошибка.", show_alert=True)
