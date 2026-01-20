"""
Модуль для отправки уведомлений пользователям
"""
# Стандартная библиотека
import logging
import os
from pathlib import Path
from typing import Dict

# Сторонние библиотеки
from aiogram import Bot
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Загружаем .env из корневой директории проекта
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, encoding='utf-8-sig')

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден в переменных окружения. "
        "Создайте файл .env с BOT_TOKEN=your_token"
    )

bot_instance = Bot(token=BOT_TOKEN)


async def send_notification(user_id: int, car_data: Dict):
    """Отправить уведомление о найденном автомобиле"""
    # Логируем данные для отладки (INFO уровень, чтобы видеть в логах)
    logger.info(f"Отправка уведомления: title={car_data.get('title')}, year={car_data.get('year')}, mileage={car_data.get('mileage')}, engine_volume={car_data.get('engine_volume')}, city={car_data.get('city')}, transmission={car_data.get('transmission')}, engine_type={car_data.get('engine_type')}, body_type={car_data.get('body_type')}, source={car_data.get('source')}")
    
    # Проверяем, что есть минимальные данные для отправки
    title = car_data.get('title', '').strip()
    if not title or len(title) < 3:
        logger.warning(f"Пропущено уведомление: нет заголовка или заголовок слишком короткий (title: '{title}')")
        return
    
    url = car_data.get('url', '').strip()
    if not url or url == 'https://abw.by/cars' or 'filter' in url.lower():
        logger.warning(f"Пропущено уведомление: неправильный URL - {url}")
        return
    
    text = f"🚗 <b>Новое объявление!</b>\n\n"
    
    # Используем полный заголовок, если он есть и содержит больше информации, чем просто brand + model
    brand = car_data.get('brand', '').strip()
    model = car_data.get('model', '').strip()
    
    # Формируем название автомобиля
    if title and len(title) > len(f"{brand} {model}".strip()):
        # Если заголовок более информативен, используем его
        text += f"<b>{title}</b>\n"
    elif brand or model:
        # Иначе используем brand + model
        car_name = f"{brand} {model}".strip()
        if car_name:
            text += f"<b>{car_name}</b>\n"
        else:
            # Если brand и model пустые, используем заголовок
            text += f"<b>{title}</b>\n"
    else:
        # Если ничего нет, используем заголовок
        text += f"<b>{title}</b>\n"
    
    text += "\n"
    
    # Формируем список характеристик
    details = []
    
    if car_data.get('year'):
        details.append(f"📅 Год: {car_data['year']}")
    if car_data.get('mileage'):
        mileage = car_data['mileage']
        if isinstance(mileage, (int, float)):
            # Форматируем пробег с разделителями тысяч (пробелы вместо запятых)
            mileage_formatted = f"{int(mileage):,}".replace(',', ' ')
            details.append(f"🛣️ Пробег: {mileage_formatted} км")
        else:
            details.append(f"🛣️ Пробег: {mileage} км")
    if car_data.get('engine_volume'):
        volume = car_data['engine_volume']
        if isinstance(volume, (int, float)):
            details.append(f"⚙️ Объем: {volume} л")
        else:
            details.append(f"⚙️ Объем: {volume}")
    if car_data.get('city'):
        details.append(f"📍 Город: {car_data['city']}")
    if car_data.get('transmission'):
        details.append(f"🔧 Коробка: {car_data['transmission']}")
    if car_data.get('engine_type'):
        details.append(f"⛽ Двигатель: {car_data['engine_type']}")
    if car_data.get('body_type'):
        details.append(f"🚙 Тип кузова: {car_data['body_type']}")
    
    # Добавляем все характеристики
    if details:
        text += "\n".join(details) + "\n"
    
    text += "\n"
    
    # Цена
    price_parts = []
    price_usd = None
    price_byn = None
    
    # Извлекаем цены и нормализуем их
    if car_data.get('price_usd'):
        try:
            price_usd = float(car_data['price_usd'])
            # Проверка на разумность: если цена больше 1 миллиона USD, вероятно ошибка парсинга
            if price_usd > 1000000:
                logger.warning(f"Подозрительно большая цена USD: {price_usd}, пропускаем")
                price_usd = None
        except (ValueError, TypeError):
            pass
    
    if car_data.get('price_byn'):
        try:
            price_byn = float(car_data['price_byn'])
            # Проверка на разумность: если цена больше 10 миллионов BYN, вероятно ошибка парсинга
            if price_byn > 10000000:
                logger.warning(f"Подозрительно большая цена BYN: {price_byn}, пропускаем")
                price_byn = None
        except (ValueError, TypeError):
            pass
    
    # Проверка соответствия цен, если обе есть
    if price_usd and price_byn:
        expected_byn = price_usd * 3.3
        expected_usd = price_byn / 3.3
        # Если разница больше 15%, вероятно ошибка парсинга
        usd_diff = abs(price_usd - expected_usd) / max(price_usd, 1)
        byn_diff = abs(price_byn - expected_byn) / max(expected_byn, 1)
        
        if byn_diff > 0.15 or usd_diff > 0.15:
            logger.warning(f"Несоответствие цен в уведомлении: USD={price_usd}, BYN={price_byn}, ожидалось BYN={expected_byn:.0f}, USD={expected_usd:.0f}")
            # Исправляем цену, используя более точную
            if usd_diff < byn_diff:
                # USD более точная, пересчитываем BYN
                price_byn = round(price_usd * 3.3, 0)
                logger.info(f"Исправлена цена BYN: {price_byn} (было {car_data.get('price_byn')})")
            else:
                # BYN более точная, пересчитываем USD
                price_usd = round(price_byn / 3.3, 0)
                logger.info(f"Исправлена цена USD: {price_usd} (было {car_data.get('price_usd')})")
    
    # Конвертация валют, если одна из цен отсутствует (примерный курс: 1 USD = 3.3 BYN)
    # Но только если обе цены разумные
    if price_usd and not price_byn:
        if price_usd < 1000000:  # Только если цена разумная
            price_byn = round(price_usd * 3.3, 0)
    elif price_byn and not price_usd:
        if price_byn < 10000000:  # Только если цена разумная
            price_usd = round(price_byn / 3.3, 0)
    
    # Форматируем и добавляем цены (используем пробелы как разделители тысяч для читаемости)
    if price_usd and price_usd < 1000000:
        price_parts.append(f"<b>${price_usd:,.0f}</b>".replace(',', ' '))
    if price_byn and price_byn < 10000000:
        price_parts.append(f"<b>{price_byn:,.0f} BYN</b>".replace(',', ' '))
    
    if price_parts:
        # Если обе цены есть, разделяем их для читаемости
        if len(price_parts) == 2:
            text += f"💰 {price_parts[0]} / {price_parts[1]}\n\n"
        else:
            text += f"💰 {price_parts[0]}\n\n"
    else:
        text += "\n"
    
    # Проверяем и исправляем URL если нужно
    url = car_data.get('url', '')
    if url:
        # Убеждаемся, что URL полный
        if not url.startswith('http'):
            # Если относительный путь, добавляем домен в зависимости от источника
            source = car_data.get('source', '')
            if 'av.by' in source or 'av.by' in url:
                url = f"https://av.by{url}" if url.startswith('/') else f"https://av.by/{url}"
            elif 'kufar' in source or 'kufar' in url:
                url = f"https://kufar.by{url}" if url.startswith('/') else f"https://kufar.by/{url}"
            elif 'onliner' in source or 'onliner' in url:
                url = f"https://ab.onliner.by{url}" if url.startswith('/') else f"https://ab.onliner.by/{url}"
            elif 'abw' in source or 'abw' in url:
                url = f"https://abw.by{url}" if url.startswith('/') else f"https://abw.by/{url}"
    
    if url:
        text += f"🔗 <a href='{url}'>Открыть объявление</a>"
    else:
        text += "🔗 Ссылка на объявление недоступна"
    
    try:
        if car_data.get('image_url'):
            await bot_instance.send_photo(user_id, car_data['image_url'], caption=text, parse_mode='HTML')
            logger.info(f"Отправлено уведомление с фото пользователю {user_id}: {title[:50] if title else 'N/A'}")
        else:
            await bot_instance.send_message(user_id, text, parse_mode='HTML', disable_web_page_preview=False)
            logger.info(f"Отправлено уведомление пользователю {user_id}: {title[:50] if title else 'N/A'}")
    except Exception as e:
        error_msg = str(e)
        # Игнорируем ошибку "chat not found" для несуществующих пользователей (тестовые аккаунты)
        if 'chat not found' in error_msg.lower():
            logger.warning(f"Пропущено уведомление пользователю {user_id}: чат не найден (возможно, тестовый пользователь)")
        else:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}", exc_info=True)
