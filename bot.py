"""
Telegram-бот для мониторинга объявлений о продаже автомобилей
"""
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from db_manager import DBManager
from typing import Dict, Optional, List, Tuple

# Токен бота из переменной окружения
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Создайте файл .env с BOT_TOKEN=your_token")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_manager = DBManager()

# Справочники марок и моделей для выбора по кнопкам
# Популярные марки на белорусском рынке (av.by, kufar.by, onliner.by, abw.by)
BRANDS: List[Tuple[str, str]] = [
    # Премиум сегмент
    ("bmw", "BMW"),
    ("mercedes", "Mercedes-Benz"),
    ("audi", "Audi"),
    ("lexus", "Lexus"),
    ("volvo", "Volvo"),
    ("tesla", "Tesla"),
    # Немецкие марки
    ("volkswagen", "Volkswagen"),
    ("opel", "Opel"),
    # Японские марки
    ("toyota", "Toyota"),
    ("nissan", "Nissan"),
    ("honda", "Honda"),
    ("mazda", "Mazda"),
    ("mitsubishi", "Mitsubishi"),
    ("subaru", "Subaru"),
    ("suzuki", "Suzuki"),
    # Корейские марки
    ("hyundai", "Hyundai"),
    ("kia", "Kia"),
    # Французские марки
    ("renault", "Renault"),
    ("peugeot", "Peugeot"),
    ("citroen", "Citroen"),
    # Чешские марки
    ("skoda", "Skoda"),
    # Американские марки
    ("ford", "Ford"),
    ("chevrolet", "Chevrolet"),
    # Итальянские марки
    ("fiat", "Fiat"),
    # Популярные в Беларуси
    ("belgee", "BelGee"),
    ("lada", "LADA"),
    ("geely", "Geely"),
    ("chery", "Chery"),
    ("byd", "BYD"),
    ("haval", "Haval"),
    ("greatwall", "Great Wall"),
    ("dongfeng", "Dongfeng"),
    ("faw", "FAW"),
    ("changan", "Changan"),
]

BRAND_MODELS: Dict[str, List[str]] = {
    # BMW
    "bmw": ["1 Series", "2 Series", "3 Series", "4 Series", "5 Series", "6 Series", "7 Series", "8 Series", 
            "X1", "X2", "X3", "X4", "X5", "X6", "X7", "Z4", "i3", "i4", "iX"],
    # Mercedes-Benz
    "mercedes": ["A-Class", "B-Class", "C-Class", "E-Class", "S-Class", "CLA", "CLS", "GLA", "GLB", "GLC", 
                 "GLE", "GLS", "G-Class", "AMG GT", "EQC", "EQS"],
    # Audi
    "audi": ["A1", "A3", "A4", "A5", "A6", "A7", "A8", "Q2", "Q3", "Q5", "Q7", "Q8", "e-tron", "TT", "R8"],
    # Lexus
    "lexus": ["IS", "ES", "GS", "LS", "NX", "RX", "GX", "LX", "UX", "LC"],
    # Volvo
    "volvo": ["S40", "S60", "S80", "S90", "V40", "V60", "V90", "XC40", "XC60", "XC90"],
    # Tesla
    "tesla": ["Model S", "Model 3", "Model X", "Model Y"],
    # Volkswagen
    "volkswagen": ["Polo", "Golf", "Jetta", "Passat", "Arteon", "Tiguan", "Touareg", "T-Cross", "T-Roc", "ID.3", "ID.4"],
    # Opel
    "opel": ["Corsa", "Astra", "Insignia", "Crossland", "Grandland", "Mokka", "Combo"],
    # Toyota
    "toyota": ["Yaris", "Corolla", "Camry", "Prius", "RAV4", "Highlander", "Land Cruiser", "Prado", "C-HR", "bZ4X"],
    # Nissan
    "nissan": ["Almera", "Sentra", "Altima", "Maxima", "Juke", "Qashqai", "X-Trail", "Pathfinder", "Murano", "Patrol", "Leaf"],
    # Honda
    "honda": ["Civic", "Accord", "CR-V", "HR-V", "Pilot", "Passport", "Ridgeline", "e"],
    # Mazda
    "mazda": ["2", "3", "6", "CX-3", "CX-5", "CX-9", "MX-5"],
    # Mitsubishi
    "mitsubishi": ["Lancer", "Outlander", "Pajero", "ASX", "Eclipse Cross"],
    # Subaru
    "subaru": ["Impreza", "Legacy", "Outback", "Forester", "XV", "Ascent", "BRZ"],
    # Suzuki
    "suzuki": ["Swift", "SX4", "Vitara", "Grand Vitara", "Jimny", "S-Cross"],
    # Hyundai
    "hyundai": ["Solaris", "Elantra", "Sonata", "Tucson", "Santa Fe", "Palisade", "Kona", "Nexo", "IONIQ"],
    # Kia
    "kia": ["Rio", "Ceed", "Cerato", "Optima", "Sportage", "Sorento", "Telluride", "Soul", "Niro", "EV6"],
    # Renault
    "renault": ["Logan", "Sandero", "Duster", "Kaptur", "Koleos", "Megane", "Fluence", "Scenic", "Arkana"],
    # Peugeot
    "peugeot": ["208", "308", "408", "508", "2008", "3008", "5008", "Partner"],
    # Citroen
    "citroen": ["C3", "C4", "C5", "Berlingo", "C4 Cactus", "C4 Picasso"],
    # Skoda
    "skoda": ["Fabia", "Rapid", "Octavia", "Superb", "Kamiq", "Karoq", "Kodiaq", "Enyaq"],
    # Ford
    "ford": ["Fiesta", "Focus", "Mondeo", "Kuga", "Edge", "Explorer", "Mustang", "Ranger", "EcoSport"],
    # Chevrolet
    "chevrolet": ["Aveo", "Cruze", "Malibu", "Equinox", "Traverse", "Tahoe", "Camaro", "Corvette"],
    # Fiat
    "fiat": ["500", "Panda", "Tipo", "Bravo", "Doblo", "Ducato"],
    # BelGee (популярные в Беларуси)
    "belgee": ["X50", "X55", "X60", "X70", "X80"],
    # LADA
    "lada": ["Granta", "Vesta", "Largus", "XRAY", "Niva", "4x4"],
    # Geely
    "geely": ["Coolray", "Atlas", "Monjaro", "Tugella", "Emgrand", "Geometry C"],
    # Chery
    "chery": ["Tiggo 2", "Tiggo 4", "Tiggo 7", "Tiggo 8", "Exeed TX", "Exeed VX"],
    # BYD
    "byd": ["F3", "F5", "F6", "S6", "Tang", "Song", "Yuan", "Han", "Atto 3"],
    # Haval
    "haval": ["H2", "H6", "H9", "Jolion", "Dargo", "F7", "F7x"],
    # Great Wall
    "greatwall": ["Hover", "Wingle", "Steed", "Poer", "Tank 300", "Tank 500"],
    # Dongfeng
    "dongfeng": ["AX7", "T5", "SX6", "Fengon", "Mengshi"],
    # FAW
    "faw": ["Besturn", "Oley", "Vita", "V2", "V5"],
    # Changan
    "changan": ["CS35", "CS55", "CS75", "CS95", "UNI-T", "UNI-K", "Eado"],
}


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
        [InlineKeyboardButton(text="✅ Сохранить фильтр", callback_data=f"save_filter_{filter_id}"),
         InlineKeyboardButton(text="❌ Удалить фильтр", callback_data=f"delete_filter_{filter_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
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
    back_cb = f"edit_filter_{filter_id}" if filter_id is not None else "back_to_menu"
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
    back_cb = f"edit_filter_{filter_id}" if filter_id is not None else "back_to_menu"
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
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_filter_{filter_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_engine_type_keyboard(filter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа двигателя"""
    buttons = [
        [InlineKeyboardButton(text="Бензин", callback_data=f"set_engine_Бензин_{filter_id}")],
        [InlineKeyboardButton(text="Дизель", callback_data=f"set_engine_Дизель_{filter_id}")],
        [InlineKeyboardButton(text="Электро", callback_data=f"set_engine_Электро_{filter_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_filter_{filter_id}")]
    ]
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
    back_cb = f"edit_filter_{filter_id}" if filter_id is not None else "back_to_menu"
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
    back_cb = f"edit_filter_{filter_id}" if filter_id is not None else "back_to_menu"
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
    back_cb = f"edit_filter_{filter_id}" if filter_id is not None else "back_to_menu"
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
    back_cb = f"edit_filter_{filter_id}" if filter_id is not None else "back_to_menu"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_filter_text(f: 'UserFilter') -> str:
    """Форматирование текста фильтра для отображения"""
    text = f"🔍 <b>Фильтр #{f.id}</b>\n"
    
    # Марка и модель
    if f.brand or f.model:
        brand = f.brand or "любая"
        model = f.model or "любая"
        text += f"🚗 <b>{brand} {model}</b>\n"
    else:
        text += "🚗 <b>Любая марка и модель</b>\n"
    
    # Год
    if f.year_from is not None or f.year_to is not None:
        year_from = str(f.year_from) if f.year_from is not None else "—"
        year_to = str(f.year_to) if f.year_to is not None else "—"
        text += f"📅 Год: {year_from} — {year_to}\n"
    else:
        text += "📅 Год: не ограничено\n"
    
    # Цена
    if f.price_from_usd is not None or f.price_to_usd is not None:
        price_from = f"${f.price_from_usd:,.0f}" if f.price_from_usd is not None else "—"
        price_to = f"${f.price_to_usd:,.0f}" if f.price_to_usd is not None else "—"
        text += f"💰 Цена: {price_from} — {price_to}\n"
    else:
        text += "💰 Цена: не ограничено\n"
    
    # Коробка передач
    if f.transmission:
        text += f"⚙️ Коробка: {f.transmission}\n"
    else:
        text += "⚙️ Коробка: любая\n"
    
    # Тип двигателя
    if f.engine_type:
        text += f"⛽ Двигатель: {f.engine_type}\n"
    else:
        text += "⛽ Двигатель: любой\n"
    
    # Статус
    status = "✅ Активен" if f.is_active else "❌ Неактивен"
    text += f"📊 Статус: {status}\n"
    
    return text


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "🚗 Добро пожаловать в Авто-Монитор!\n\n"
        "Я помогу вам отслеживать новые объявления о продаже автомобилей на сайтах:\n"
        "• av.by\n"
        "• kufar.by\n"
        "• cars.onliner.by\n"
        "• abw.by\n\n"
        "Настройте фильтры, и я буду присылать вам уведомления о новых подходящих объявлениях!",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "📖 Помощь по использованию бота:\n\n"
        "1. Добавьте фильтр через меню\n"
        "2. Настройте параметры поиска (марка, модель, год, цена и т.д.)\n"
        "3. Сохраните фильтр\n"
        "4. Бот будет проверять новые объявления каждые 2-5 минут\n"
        "5. Вы получите уведомление, когда найдется подходящее объявление\n\n"
        "Команды:\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/filters - Список ваших фильтров",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("filters"))
async def cmd_filters(message: Message):
    """Показать список фильтров пользователя"""
    filters = await db_manager.get_user_filters(message.from_user.id)
    if not filters:
        await message.answer("У вас пока нет активных фильтров. Добавьте первый фильтр через меню!")
        return
    
    text = "📋 Ваши фильтры:\n\n"
    for f in filters:
        text += format_filter_text(f)
        text += "\n"
    
    await message.answer(text, reply_markup=get_main_keyboard())


@dp.message(F.text == "➕ Добавить фильтр")
async def handle_add_filter_button(message: Message, state: FSMContext):
    """Обработчик кнопки 'Добавить фильтр' из постоянной клавиатуры"""
    try:
        await state.clear()
        await state.update_data(filter_id=None)
        await message.answer(
            "🔍 Настройте параметры фильтра:\n\n"
            "Выберите параметр для настройки:",
            reply_markup=get_filter_keyboard(None)
        )
    except Exception as e:
        print(f"Ошибка в handle_add_filter_button: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )


@dp.message(F.text == "📋 Мои фильтры")
async def handle_my_filters_button(message: Message):
    """Обработчик кнопки 'Мои фильтры' из постоянной клавиатуры"""
    try:
        user_id = message.from_user.id
        filters = await db_manager.get_user_filters(user_id)
        
        if not filters:
            await message.answer(
                "📋 <b>Ваши фильтры</b>\n\n"
                "У вас пока нет активных фильтров.\n"
                "Добавьте первый фильтр через меню!",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        # Ограничиваем количество фильтров для отображения (чтобы не превысить лимит Telegram)
        MAX_FILTERS_PER_MESSAGE = 10
        total_filters = len(filters)
        filters_to_show = filters[:MAX_FILTERS_PER_MESSAGE]
        
        text = f"📋 <b>Ваши фильтры</b> (всего: {total_filters}"
        if total_filters > MAX_FILTERS_PER_MESSAGE:
            text += f", показано: {MAX_FILTERS_PER_MESSAGE}"
        text += "):\n\n"
        
        buttons = []
        current_text_length = len(text)
        MAX_MESSAGE_LENGTH = 3500  # Оставляем запас от лимита 4096
        
        for f in filters_to_show:
            filter_text = format_filter_text(f) + "\n"
            filter_text_length = len(filter_text)
            
            # Проверяем, не превысит ли добавление фильтра лимит
            if current_text_length + filter_text_length > MAX_MESSAGE_LENGTH:
                # Если превысит, останавливаемся
                break
            
            text += filter_text
            current_text_length += filter_text_length
            
            buttons.append([InlineKeyboardButton(
                text=f"✏️ Редактировать фильтр #{f.id}",
                callback_data=f"edit_filter_{f.id}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode='HTML'
        )
        
        # Если фильтров больше, чем показано, отправляем дополнительное сообщение
        if total_filters > len(filters_to_show):
            remaining = total_filters - len(filters_to_show)
            await message.answer(
                f"<i>И еще {remaining} фильтр(ов). Используйте команду /filters для просмотра всех.</i>",
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Ошибка в handle_my_filters_button: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            "❌ Произошла ошибка при загрузке фильтров. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )


@dp.message(F.text == "ℹ️ Помощь")
async def handle_help_button(message: Message):
    """Обработчик кнопки 'Помощь' из постоянной клавиатуры"""
    await message.answer(
        "📖 Помощь по использованию бота:\n\n"
        "1. Добавьте фильтр через меню\n"
        "2. Настройте параметры поиска (марка, модель, год, цена и т.д.)\n"
        "3. Сохраните фильтр\n"
        "4. Бот будет проверять новые объявления каждые 2-5 минут\n"
        "5. Вы получите уведомление, когда найдется подходящее объявление\n\n"
        "Команды:\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/filters - Список ваших фильтров",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Обработчик кнопки помощи (для обратной совместимости)"""
    await callback.message.edit_text(
        "📖 Помощь по использованию бота:\n\n"
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
    """Добавить новый фильтр"""
    await state.clear()
    await callback.message.edit_text(
        "🔍 Создание нового фильтра\n\n"
        "Выберите параметр для настройки:",
        reply_markup=get_filter_keyboard(None)
    )
    await callback.answer()
    """Добавить новый фильтр"""
    await state.update_data(filter_id=None)
    await callback.message.edit_text(
        "🔍 Настройте параметры фильтра:\n\n"
        "Выберите параметр для настройки:",
        reply_markup=get_filter_keyboard()
    )
    await callback.answer()


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
        )
        
        # Используем функцию форматирования для единообразия
        text = "🔍 <b>Редактирование фильтра</b>:\n\n"
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


@dp.callback_query(F.data.startswith("filter_brand_"))
async def callback_set_brand(callback: CallbackQuery, state: FSMContext):
    """Установить марку"""
    raw_id = callback.data.split("_")[-1]
    filter_id: Optional[int]
    if raw_id == "None":
        filter_id = None
    else:
        filter_id = int(raw_id)

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


@dp.callback_query(F.data.startswith("filter_model_"))
async def callback_set_model(callback: CallbackQuery, state: FSMContext):
    """Установить модель (только после выбора марки)"""
    raw_id = callback.data.split("_")[-1]
    filter_id: Optional[int]
    if raw_id == "None":
        filter_id = None
    else:
        filter_id = int(raw_id)

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

    # Если марка выбрана из списка и для неё есть модели — показываем список моделей
    if brand_key and brand_key in BRAND_MODELS and BRAND_MODELS[brand_key]:
        brand_title = next((t for k, t in BRANDS if k == brand_key), brand_key)
        await callback.message.edit_text(
            f"Выберите модель автомобиля ({brand_title}):",
            reply_markup=get_model_keyboard(brand_key, filter_id)
        )
        await state.set_state(FilterStates.waiting_model)
    else:
        # Если марка введена вручную или нет списка моделей - просим ввести модель вручную
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


@dp.callback_query(F.data.startswith("filter_year_from_"))
async def callback_set_year_from(callback: CallbackQuery, state: FSMContext):
    """Установить год от"""
    raw_id = callback.data.split("_")[-1]
    filter_id: Optional[int]
    if raw_id == "None":
        filter_id = None
    else:
        filter_id = int(raw_id)

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
    filter_id: Optional[int]
    if raw_id == "None":
        filter_id = None
    else:
        filter_id = int(raw_id)

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


@dp.callback_query(F.data.startswith("filter_price_from_"))
async def callback_set_price_from(callback: CallbackQuery, state: FSMContext):
    """Установить цену от"""
    raw_id = callback.data.split("_")[-1]
    filter_id: Optional[int]
    if raw_id == "None":
        filter_id = None
    else:
        filter_id = int(raw_id)

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
    filter_id: Optional[int]
    if raw_id == "None":
        filter_id = None
    else:
        filter_id = int(raw_id)

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


@dp.callback_query(F.data.startswith("filter_transmission_"))
async def callback_set_transmission(callback: CallbackQuery, state: FSMContext):
    """Установить коробку передач"""
    filter_id = callback.data.split("_")[-1]
    if filter_id == "None":
        filter_id = None
    else:
        filter_id = int(filter_id)
    
    await callback.message.edit_text("Выберите тип коробки передач:", reply_markup=get_transmission_keyboard(filter_id))
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
    
    await callback.message.edit_text(f"✅ Коробка передач установлена: {transmission}", reply_markup=get_filter_keyboard(data.get('filter_id')))
    await callback.answer()


@dp.callback_query(F.data.startswith("filter_engine_type_"))
async def callback_set_engine_type(callback: CallbackQuery, state: FSMContext):
    """Установить тип двигателя"""
    filter_id = callback.data.split("_")[-1]
    if filter_id == "None":
        filter_id = None
    else:
        filter_id = int(filter_id)
    
    await callback.message.edit_text("Выберите тип двигателя:", reply_markup=get_engine_type_keyboard(filter_id))
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
    
    await callback.message.edit_text(f"✅ Тип двигателя установлен: {engine_type}", reply_markup=get_filter_keyboard(data.get('filter_id')))
    await callback.answer()


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
        filters = await db_manager.get_user_filters(user_id)
        
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


# Обработчики текстовых сообщений для ввода параметров
@dp.message(F.text.in_(["➕ Добавить фильтр", "📋 Мои фильтры", "ℹ️ Помощь"]))
async def handle_main_menu_buttons(message: Message, state: FSMContext):
    """Обработчик кнопок главного меню - должен обрабатываться первым"""
    text = message.text
    if text == "➕ Добавить фильтр":
        await handle_add_filter_button(message, state)
    elif text == "📋 Мои фильтры":
        await handle_my_filters_button(message)
    elif text == "ℹ️ Помощь":
        await handle_help_button(message)


@dp.message(StateFilter(FilterStates.waiting_brand))
async def process_brand(message: Message, state: FSMContext):
    """Обработка ввода марки"""
    await state.update_data(brand=message.text)
    data = await state.get_data()
    await message.answer(f"✅ Марка установлена: {message.text}", reply_markup=get_filter_keyboard(data.get('filter_id')))
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
            await message.answer(f"✅ Год ОТ установлен: {year}", reply_markup=get_filter_keyboard(data.get('filter_id')))
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
            await message.answer(f"✅ Год ДО установлен: {year}", reply_markup=get_filter_keyboard(data.get('filter_id')))
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
            await message.answer(f"✅ Цена ОТ установлена: ${price:.0f}", reply_markup=get_filter_keyboard(data.get('filter_id')))
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
            await message.answer(f"✅ Цена ДО установлена: ${price:.0f}", reply_markup=get_filter_keyboard(data.get('filter_id')))
        else:
            await message.answer("❌ Цена должна быть больше 0")
    except ValueError:
        await message.answer("❌ Введите корректную цену (число)")
    await state.set_state(None)
