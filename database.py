"""
Модели базы данных для хранения фильтров пользователей и найденных объявлений
"""
from sqlalchemy import Column, Integer, String, Float, BigInteger, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class UserFilter(Base):
    """Фильтры пользователя для поиска автомобилей"""
    __tablename__ = 'users_filters'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    brand = Column(String(100), nullable=True)  # Марка
    model = Column(String(100), nullable=True)  # Модель
    year_from = Column(Integer, nullable=True)  # Год от
    year_to = Column(Integer, nullable=True)  # Год до
    price_from_usd = Column(Float, nullable=True)  # Цена от (USD)
    price_to_usd = Column(Float, nullable=True)  # Цена до (USD)
    transmission = Column(String(20), nullable=True)  # Автомат/Механика
    engine_type = Column(String(20), nullable=True)  # Бензин/Дизель/Электро
    body_type = Column(String(50), nullable=True)  # Тип кузова (седан, хэтчбек, универсал, внедорожник и т.д.)
    is_active = Column(Boolean, default=True)  # Активен ли фильтр
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с найденными автомобилями
    found_cars = relationship("FoundCar", back_populates="filter", cascade="all, delete-orphan")


class FoundCar(Base):
    """Найденные объявления автомобилей"""
    __tablename__ = 'found_cars'
    
    id = Column(Integer, primary_key=True)
    filter_id = Column(Integer, ForeignKey('users_filters.id'), nullable=False)
    source = Column(String(50), nullable=False)  # av.by, kufar.by, onliner.by, abw.by
    ad_id = Column(String(200), nullable=False)  # ID объявления на сайте
    title = Column(String(500), nullable=False)  # Название
    price_usd = Column(Float, nullable=True)  # Цена в USD
    price_byn = Column(Float, nullable=True)  # Цена в BYN
    year = Column(Integer, nullable=True)  # Год выпуска
    mileage = Column(Integer, nullable=True)  # Пробег
    engine_volume = Column(Float, nullable=True)  # Объем двигателя
    city = Column(String(100), nullable=True)  # Город
    url = Column(Text, nullable=False)  # Ссылка на объявление
    image_url = Column(Text, nullable=True)  # Ссылка на фото
    transmission = Column(String(20), nullable=True)  # Коробка передач
    engine_type = Column(String(20), nullable=True)  # Тип двигателя
    body_type = Column(String(50), nullable=True)  # Тип кузова
    notified = Column(Boolean, default=False)  # Отправлено ли уведомление
    found_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с фильтром
    filter = relationship("UserFilter", back_populates="found_cars")
    
    # Уникальность по источнику и ID объявления
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
