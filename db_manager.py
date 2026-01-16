"""
Менеджер базы данных для работы с SQLAlchemy
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_
from database import Base, UserFilter, FoundCar
from typing import Optional, List

DATABASE_URL = "sqlite+aiosqlite:///./auto_monitor.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """Получить сессию базы данных"""
    async with async_session() as session:
        yield session


class DBManager:
    """Менеджер для работы с базой данных"""
    
    @staticmethod
    async def add_user_filter(user_id: int, **kwargs) -> UserFilter:
        """Добавить фильтр пользователя"""
        async with async_session() as session:
            filter_obj = UserFilter(user_id=user_id, **kwargs)
            session.add(filter_obj)
            await session.commit()
            await session.refresh(filter_obj)
            return filter_obj
    
    @staticmethod
    async def get_user_filters(user_id: int, active_only: bool = True) -> List[UserFilter]:
        """Получить фильтры пользователя"""
        async with async_session() as session:
            query = select(UserFilter).where(UserFilter.user_id == user_id)
            if active_only:
                query = query.where(UserFilter.is_active == True)
            result = await session.execute(query)
            return list(result.scalars().all())
    
    @staticmethod
    async def get_filter_by_id(filter_id: int, user_id: Optional[int] = None) -> Optional[UserFilter]:
        """Получить фильтр по ID с проверкой владельца"""
        async with async_session() as session:
            query = select(UserFilter).where(UserFilter.id == filter_id)
            if user_id is not None:
                query = query.where(UserFilter.user_id == user_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def update_user_filter(filter_id: int, user_id: int, **kwargs) -> Optional[UserFilter]:
        """Обновить фильтр пользователя с проверкой владельца"""
        async with async_session() as session:
            result = await session.execute(
                select(UserFilter).where(
                    and_(UserFilter.id == filter_id, UserFilter.user_id == user_id)
                )
            )
            filter_obj = result.scalar_one_or_none()
            if filter_obj:
                for key, value in kwargs.items():
                    setattr(filter_obj, key, value)
                await session.commit()
                await session.refresh(filter_obj)
            return filter_obj
    
    @staticmethod
    async def delete_user_filter(filter_id: int, user_id: int) -> bool:
        """Удалить фильтр пользователя с проверкой владельца"""
        async with async_session() as session:
            result = await session.execute(
                select(UserFilter).where(
                    and_(UserFilter.id == filter_id, UserFilter.user_id == user_id)
                )
            )
            filter_obj = result.scalar_one_or_none()
            if filter_obj:
                await session.delete(filter_obj)
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def check_car_exists(source: str, ad_id: str) -> bool:
        """Проверить, существует ли объявление в базе"""
        async with async_session() as session:
            result = await session.execute(
                select(FoundCar).where(
                    and_(FoundCar.source == source, FoundCar.ad_id == str(ad_id))
                )
            )
            return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def add_found_car(filter_id: int, **kwargs) -> FoundCar:
        """Добавить найденное объявление"""
        async with async_session() as session:
            car = FoundCar(filter_id=filter_id, **kwargs)
            session.add(car)
            await session.commit()
            await session.refresh(car)
            return car
    
    @staticmethod
    async def mark_car_as_notified(car_id: int):
        """Отметить объявление как уведомленное"""
        async with async_session() as session:
            result = await session.execute(
                select(FoundCar).where(FoundCar.id == car_id)
            )
            car = result.scalar_one_or_none()
            if car:
                car.notified = True
                await session.commit()
    
    @staticmethod
    async def get_all_active_filters() -> List[UserFilter]:
        """Получить все активные фильтры всех пользователей"""
        async with async_session() as session:
            result = await session.execute(
                select(UserFilter).where(UserFilter.is_active == True)
            )
            return list(result.scalars().all())
