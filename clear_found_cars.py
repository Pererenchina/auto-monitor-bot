"""
Скрипт для очистки базы данных от найденных объявлений
Фильтры пользователей остаются нетронутыми
"""
import asyncio
from db_manager import async_session
from database import FoundCar, UserFilter
from sqlalchemy import select, func

async def clear_found_cars():
    """Очистка всех найденных объявлений из базы данных"""
    
    async with async_session() as session:
        # Подсчитываем количество записей до удаления
        result = await session.execute(select(func.count(FoundCar.id)))
        total_before = result.scalar()
        
        # Подсчитываем количество фильтров (для проверки)
        result = await session.execute(select(func.count(UserFilter.id)))
        total_filters = result.scalar()
        
        print("=" * 80)
        print("ОЧИСТКА БАЗЫ ДАННЫХ ОТ НАЙДЕННЫХ ОБЪЯВЛЕНИЙ")
        print("=" * 80)
        print(f"\nТекущее состояние:")
        print(f"  Найдено объявлений в базе: {total_before}")
        print(f"  Всего фильтров: {total_filters}")
        
        if total_before == 0:
            print("\nБаза данных уже пуста. Нечего удалять.")
            return
        
        # Подтверждение
        print(f"\nВНИМАНИЕ: Будет удалено {total_before} объявлений!")
        print("Фильтры пользователей останутся нетронутыми.")
        print("\nУдаление объявлений...")
        
        # Удаляем все найденные объявления
        from sqlalchemy import delete
        await session.execute(delete(FoundCar))
        await session.commit()
        
        # Проверяем результат
        result = await session.execute(select(func.count(FoundCar.id)))
        total_after = result.scalar()
        
        result = await session.execute(select(func.count(UserFilter.id)))
        filters_after = result.scalar()
        
        print(f"\nГотово!")
        print(f"  Удалено объявлений: {total_before}")
        print(f"  Осталось объявлений: {total_after}")
        print(f"  Фильтров осталось: {filters_after}")
        print("\nТеперь бот начнет заново искать объявления для всех активных фильтров.")

if __name__ == "__main__":
    asyncio.run(clear_found_cars())
