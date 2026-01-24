"""
Скрипт для просмотра базы данных
"""
import asyncio
import sqlite3
from datetime import datetime
from db_manager import async_session
from database import UserFilter, FoundCar
from sqlalchemy import select, func

async def view_database():
    """Просмотр содержимого базы данных"""
    
    print("=" * 80)
    print("БАЗА ДАННЫХ АВТОМОБИЛЬНОГО БОТА")
    print("=" * 80)
    
    async with async_session() as session:
        # Статистика по фильтрам
        result = await session.execute(select(func.count(UserFilter.id)))
        total_filters = result.scalar()
        
        result = await session.execute(select(func.count(UserFilter.id)).where(UserFilter.is_active == True))
        active_filters = result.scalar()
        
        result = await session.execute(select(func.count(FoundCar.id)))
        total_cars = result.scalar()
        
        result = await session.execute(select(func.count(FoundCar.id)).where(FoundCar.notified == True))
        notified_cars = result.scalar()
        
        print(f"\nСТАТИСТИКА:")
        print(f"  Всего фильтров: {total_filters}")
        print(f"  Активных фильтров: {active_filters}")
        print(f"  Всего найденных объявлений: {total_cars}")
        print(f"  Отправлено уведомлений: {notified_cars}")
        
        # Список всех фильтров
        print(f"\n{'=' * 80}")
        print("ФИЛЬТРЫ ПОЛЬЗОВАТЕЛЕЙ:")
        print(f"{'=' * 80}")
        
        result = await session.execute(
            select(UserFilter)
            .order_by(UserFilter.created_at.desc())
        )
        filters = result.scalars().all()
        
        for f in filters:
            status = "[АКТИВЕН]" if f.is_active else "[НЕАКТИВЕН]"
            print(f"\nФильтр #{f.id} ({status})")
            print(f"  Пользователь ID: {f.user_id}")
            print(f"  Марка: {f.brand or 'не указана'}")
            print(f"  Модель: {f.model or 'не указана'}")
            print(f"  Год: {f.year_from or 'не указан'} - {f.year_to or 'не указан'}")
            print(f"  Цена: ${f.price_from_usd or 'не указана'} - ${f.price_to_usd or 'не указана'}")
            print(f"  Коробка: {f.transmission or 'не указана'}")
            print(f"  Двигатель: {f.engine_type or 'не указан'}")
            print(f"  Кузов: {f.body_type or 'не указан'}")
            print(f"  Создан: {f.created_at}")
            
            # Количество найденных объявлений для этого фильтра
            result2 = await session.execute(
                select(func.count(FoundCar.id))
                .where(FoundCar.filter_id == f.id)
            )
            cars_count = result2.scalar()
            print(f"  Найдено объявлений: {cars_count}")
        
        # Последние найденные объявления
        print(f"\n{'=' * 80}")
        print("ПОСЛЕДНИЕ НАЙДЕННЫЕ ОБЪЯВЛЕНИЯ (топ 20):")
        print(f"{'=' * 80}")
        
        result = await session.execute(
            select(FoundCar)
            .order_by(FoundCar.found_at.desc())
            .limit(20)
        )
        cars = result.scalars().all()
        
        for car in cars:
            notified = "[УВЕДОМЛЕНО]" if car.notified else "[НЕ УВЕДОМЛЕНО]"
            print(f"\n{notified} Объявление #{car.id} (Фильтр #{car.filter_id})")
            print(f"  {car.title[:60]}")
            print(f"  Источник: {car.source} | ID: {car.ad_id}")
            print(f"  Год: {car.year or 'не указан'} | Пробег: {car.mileage or 'не указан'} км")
            print(f"  Цена: ${car.price_usd or 'не указана'} / {car.price_byn or 'не указана'} BYN")
            print(f"  Город: {car.city or 'не указан'}")
            print(f"  Найдено: {car.found_at}")
            print(f"  URL: {car.url[:80]}...")

if __name__ == "__main__":
    asyncio.run(view_database())
