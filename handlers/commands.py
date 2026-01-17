"""
Обработчики команд бота
"""
# Стандартная библиотека
from typing import TYPE_CHECKING

# Сторонние библиотеки
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

# Локальные импорты
from keyboards import get_main_keyboard, get_filter_keyboard
from utils.formatters import format_filter_text

if TYPE_CHECKING:
    from db_manager import DBManager


def register_command_handlers(dp: Dispatcher, db_manager: 'DBManager') -> None:
    """Регистрация обработчиков команд"""
    
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        """Обработчик команды /start"""
        await message.answer(
            "🚗 <b>Добро пожаловать в Авто-Монитор!</b>\n\n"
            "Я помогу вам отслеживать новые объявления о продаже автомобилей на сайтах:\n"
            "• av.by\n"
            "• kufar.by\n"
            "• cars.onliner.by\n"
            "• abw.by\n\n"
            "Настройте фильтры, и я буду присылать вам уведомления о новых подходящих объявлениях!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        """Обработчик команды /help"""
        await message.answer(
            "ℹ️ Помощь по использованию бота:\n\n"
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
        filters = await db_manager.get_user_filters(message.from_user.id, active_only=False)
        if not filters:
            await message.answer("У вас пока нет активных фильтров. Добавьте первый фильтр через меню!")
            return
        
        text = "📋 Ваши фильтры:\n\n"
        for f in filters:
            text += format_filter_text(f)
            text += "\n"
        
        await message.answer(text, parse_mode='HTML', reply_markup=get_main_keyboard())
    
    @dp.message(F.text == "➕ Добавить фильтр")
    async def handle_add_filter_button(message: Message, state: FSMContext):
        """Обработчик кнопки 'Добавить фильтр' из постоянной клавиатуры"""
        try:
            await state.clear()
            await state.update_data(filter_id=None)
            await message.answer(
                "⚙️ Настройте параметры фильтра:\n\n"
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
            filters = await db_manager.get_user_filters(user_id, active_only=True)
            
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
                
                from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
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
            "ℹ️ Помощь по использованию бота:\n\n"
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
    
    # Обработчик кнопок главного меню - должен обрабатываться первым
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
