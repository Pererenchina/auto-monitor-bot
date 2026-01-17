"""
Утилиты для форматирования текста
"""
# Локальные импорты
from config import BODY_TYPES
from database import UserFilter


def format_filter_text(f: UserFilter) -> str:
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
    
    # Тип кузова
    if f.body_type:
        # Находим название типа кузова по ключу
        body_type_name = next((title for key, title in BODY_TYPES if key == f.body_type), f.body_type)
        text += f"🚙 Кузов: {body_type_name}\n"
    else:
        text += "🚙 Кузов: любой\n"
    
    # Статус
    status = "✅ Активен" if f.is_active else "❌ Неактивен"
    text += f"\n{status}"
    
    return text
