"""
Модуль клавиатур для бота
"""
# Стандартная библиотека
from typing import Optional, List

# Сторонние библиотеки
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

# Локальные импорты
from config import BRANDS, BRAND_MODELS, BODY_TYPES


def get_filter_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура для настройки фильтров"""
    buttons = [
        [InlineKeyboardButton(text="📝 Марка", callback_data=f"filter_brand_{filter_id}"),
         InlineKeyboardButton(text="🚗 Модель", callback_data=f"filter_model_{filter_id}")],
        [InlineKeyboardButton(text="📅 Год от", callback_data=f"filter_year_from_{filter_id}"),
         InlineKeyboardButton(text="📅 Год до", callback_data=f"filter_year_to_{filter_id}")],
        [InlineKeyboardButton(text="💰 Цена от (USD)", callback_data=f"filter_price_from_{filter_id}"),
         InlineKeyboardButton(text="💰 Цена до (USD)", callback_data=f"filter_price_to_{filter_id}")],
        [InlineKeyboardButton(text="⚙️ Коробка передач", callback_data=f"filter_transmission_{filter_id}"),
         InlineKeyboardButton(text="⛽ Тип двигателя", callback_data=f"filter_engine_type_{filter_id}")],
        [InlineKeyboardButton(text="🚙 Тип кузова", callback_data=f"filter_body_type_{filter_id}")],
        [InlineKeyboardButton(text="✅ Сохранить фильтр", callback_data=f"save_filter_{filter_id}"),
         InlineKeyboardButton(text="❌ Удалить фильтр", callback_data=f"delete_filter_{filter_id}")],
    ]
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_filter_{filter_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="add_filter")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_brand_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора марки"""
    kb_buttons: List[List[InlineKeyboardButton]] = []
    for key, title in BRANDS:
        kb_buttons.append([
            InlineKeyboardButton(
                text=title,
                callback_data=f"set_brand_{key}_{filter_id}"
            )
        ])
    kb_buttons.append([
        InlineKeyboardButton(
            text="Другая марка (ввести вручную)",
            callback_data=f"input_brand_{filter_id}"
        )
    ])
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        back_cb = f"edit_filter_{filter_id}"
    else:
        back_cb = "add_filter"
    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)


def get_model_keyboard(brand_key: str, filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора модели по выбранной марке (с группировкой по 2 кнопки в ряд)"""
    models = BRAND_MODELS.get(brand_key, [])
    kb_buttons: List[List[InlineKeyboardButton]] = []
    
    # Группируем модели по 2 в ряд для компактности
    for i in range(0, len(models), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=models[i],
            callback_data=f"set_model_{brand_key}_{i}_{filter_id}"
        ))
        if i + 1 < len(models):
            row.append(InlineKeyboardButton(
                text=models[i + 1],
                callback_data=f"set_model_{brand_key}_{i + 1}_{filter_id}"
            ))
        kb_buttons.append(row)
    
    kb_buttons.append([
        InlineKeyboardButton(
            text="Другая модель (ввести вручную)",
            callback_data=f"input_model_{filter_id}"
        )
    ])
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        back_cb = f"edit_filter_{filter_id}"
    else:
        back_cb = "add_filter"
    kb_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота (постоянная клавиатура рядом с полем ввода)"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить фильтр"), KeyboardButton(text="📋 Мои фильтры")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard


def get_transmission_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора коробки передач"""
    buttons = [
        [InlineKeyboardButton(text="Автомат", callback_data=f"set_transmission_Автомат_{filter_id}")],
        [InlineKeyboardButton(text="Механика", callback_data=f"set_transmission_Механика_{filter_id}")],
    ]
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_filter_{filter_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="add_filter")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_engine_type_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа двигателя"""
    buttons = [
        [InlineKeyboardButton(text="Бензин", callback_data=f"set_engine_Бензин_{filter_id}")],
        [InlineKeyboardButton(text="Дизель", callback_data=f"set_engine_Дизель_{filter_id}")],
        [InlineKeyboardButton(text="Электро", callback_data=f"set_engine_Электро_{filter_id}")],
    ]
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_filter_{filter_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="add_filter")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_body_type_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа кузова"""
    buttons: List[List[InlineKeyboardButton]] = []
    # Группируем по 2 кнопки в ряд для компактности
    for i in range(0, len(BODY_TYPES), 2):
        row = []
        key1, title1 = BODY_TYPES[i]
        row.append(InlineKeyboardButton(
            text=title1,
            callback_data=f"set_body_type_{key1}_{filter_id}"
        ))
        if i + 1 < len(BODY_TYPES):
            key2, title2 = BODY_TYPES[i + 1]
            row.append(InlineKeyboardButton(
                text=title2,
                callback_data=f"set_body_type_{key2}_{filter_id}"
            ))
        buttons.append(row)
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_filter_{filter_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="add_filter")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_year_from_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора года ОТ"""
    years = [2000, 2005, 2010, 2015, 2018, 2020, 2022, 2024]
    buttons: List[List[InlineKeyboardButton]] = []
    for y in years:
        buttons.append([
            InlineKeyboardButton(
                text=str(y),
                callback_data=f"set_year_from_{y}_{filter_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="Другой год (ввести вручную)",
            callback_data=f"input_year_from_{filter_id}"
        )
    ])
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        back_cb = f"edit_filter_{filter_id}"
    else:
        back_cb = "add_filter"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_year_to_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора года ДО"""
    years = [2008, 2012, 2016, 2018, 2020, 2022, 2025]
    buttons: List[List[InlineKeyboardButton]] = []
    for y in years:
        buttons.append([
            InlineKeyboardButton(
                text=str(y),
                callback_data=f"set_year_to_{y}_{filter_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="Другой год (ввести вручную)",
            callback_data=f"input_year_to_{filter_id}"
        )
    ])
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        back_cb = f"edit_filter_{filter_id}"
    else:
        back_cb = "add_filter"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_price_from_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора цены ОТ"""
    prices = [2000, 4000, 6000, 8000, 10000, 15000]
    buttons: List[List[InlineKeyboardButton]] = []
    for p in prices:
        buttons.append([
            InlineKeyboardButton(
                text=f"от {p} $",
                callback_data=f"set_price_from_{p}_{filter_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="Другая цена (ввести вручную)",
            callback_data=f"input_price_from_{filter_id}"
        )
    ])
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        back_cb = f"edit_filter_{filter_id}"
    else:
        back_cb = "add_filter"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_price_to_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора цены ДО"""
    prices = [5000, 8000, 10000, 15000, 20000, 30000]
    buttons: List[List[InlineKeyboardButton]] = []
    for p in prices:
        buttons.append([
            InlineKeyboardButton(
                text=f"до {p} $",
                callback_data=f"set_price_to_{p}_{filter_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="Другая цена (ввести вручную)",
            callback_data=f"input_price_to_{filter_id}"
        )
    ])
    # Кнопка "Назад" - возвращает к редактированию фильтра или к созданию нового
    if filter_id is not None:
        back_cb = f"edit_filter_{filter_id}"
    else:
        back_cb = "add_filter"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
