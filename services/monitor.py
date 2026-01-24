"""
Фоновая задача для мониторинга объявлений
"""
# Стандартная библиотека
import asyncio
import logging
from typing import Dict, List

# Сторонние библиотеки
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Локальные импорты
from database import UserFilter
from db_manager import DBManager
from parsers.factory import ParserFactory
from .notifications import send_notification

logger = logging.getLogger(__name__)


class MonitorService:
    """Сервис для мониторинга объявлений"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db_manager = DBManager()
        self.parsers = ParserFactory.get_all_parsers()
    
    async def check_ads(self) -> None:
        """Проверка объявлений по всем активным фильтрам"""
        logger.info("Начинаю проверку объявлений...")
        
        try:
            # Получаем все активные фильтры
            filters = await self.db_manager.get_all_active_filters()
            
            if not filters:
                logger.info("Нет активных фильтров для проверки")
                return
            
            logger.info(f"Найдено {len(filters)} активных фильтров")
            
            # Проверяем каждый фильтр последовательно (для избежания rate limiting)
            for user_filter in filters:
                await self.check_filter(user_filter)
                
        except Exception as e:
            logger.error(f"Ошибка при проверке объявлений: {e}", exc_info=True)
    
    async def check_filter(self, user_filter: UserFilter) -> None:
        """Проверка объявлений по одному фильтру"""
        try:
            # Преобразуем фильтр в словарь для парсеров
            filter_dict = {
                'brand': user_filter.brand,
                'model': user_filter.model,
                'year_from': user_filter.year_from,
                'year_to': user_filter.year_to,
                'price_from_usd': user_filter.price_from_usd,
                'price_to_usd': user_filter.price_to_usd,
                'transmission': user_filter.transmission,
                'engine_type': user_filter.engine_type,
                'body_type': user_filter.body_type,
            }
            
            # Удаляем None значения
            filter_dict = {k: v for k, v in filter_dict.items() if v is not None}
            
            # Проверяем каждый источник
            for source_name, parser in self.parsers.items():
                try:
                    logger.info(f"Проверяю {source_name} для фильтра #{user_filter.id}...")
                    if filter_dict:
                        logger.debug(f"  Фильтры: {filter_dict}")
                    cars = await parser.search(filter_dict)
                    logger.info(f"  Найдено объявлений на {source_name}: {len(cars)}")
                    
                    if len(cars) > 0:
                        logger.debug(f"  Пример первого объявления: {cars[0].get('title', 'N/A')[:50]}...")
                    
                    valid_count = 0
                    new_cars_count = 0
                    filtered_count = 0
                    exists_count = 0
                    # Определяем количество проверяемых объявлений
                    # Если фильтр создан недавно (менее 7 дней назад), проверяем больше объявлений
                    # чтобы не пропустить объявления, которые были выложены до создания фильтра
                    from datetime import datetime, timedelta
                    filter_age = datetime.utcnow() - user_filter.created_at.replace(tzinfo=None) if user_filter.created_at else timedelta(days=7)
                    if filter_age < timedelta(days=7):
                        # Новый фильтр - проверяем больше объявлений (до 200)
                        # Это нужно, чтобы охватить объявления, выложенные несколько дней назад
                        cars_to_check = cars[:200]
                        logger.info(f"  Фильтр #{user_filter.id} создан недавно ({filter_age.days} дней назад), проверяю до 200 объявлений")
                    else:
                        # Старый фильтр - проверяем только новые (первые 50)
                        cars_to_check = cars[:50]
                    
                    for car in cars_to_check:
                        # Проверяем, что данные объявления валидны
                        title = car.get('title', '').strip()
                        url = car.get('url', '').strip()
                        
                        # Пропускаем объявления без заголовка или с неправильным URL
                        if not title or len(title) < 3:
                            continue
                        if not url or url == 'https://abw.by/cars' or 'filter' in url.lower():
                            continue
                        
                        # Дополнительная проверка фильтров (на случай если парсер не применил их)
                        # Особенно важно для цены - проверяем еще раз перед сохранением
                        if not parser.matches_filters(car, filter_dict):
                            filtered_count += 1
                            if filtered_count == 1:
                                logger.debug(f"  [FILTER #{user_filter.id}] Отфильтровано объявление: {title[:50]}... (brand={car.get('brand')}, model={car.get('model')}, year={car.get('year')}, price_usd={car.get('price_usd')})")
                            continue
                        
                        valid_count += 1
                        
                        # Проверяем, не было ли уже это объявление для данного пользователя
                        # (чтобы не отправлять дубликаты, если объявление подходит нескольким фильтрам пользователя)
                        exists = await self.db_manager.check_car_exists_for_user(
                            car['source'],
                            car['ad_id'],
                            user_filter.user_id
                        )
                        
                        if exists:
                            exists_count += 1
                        
                        if not exists:
                            # Удаляем поля, которых нет в модели FoundCar
                            car_data = {k: v for k, v in car.items() 
                                       if k in ['source', 'ad_id', 'title', 'price_usd', 'price_byn', 
                                               'year', 'mileage', 'engine_volume', 'city', 'url', 
                                               'image_url', 'transmission', 'engine_type', 'body_type']}
                            
                            # Сохраняем новое объявление
                            found_car = await self.db_manager.add_found_car(
                                filter_id=user_filter.id,
                                **car_data
                            )
                            
                            # Отправляем уведомление
                            await send_notification(user_filter.user_id, car)
                            
                            # Отмечаем как уведомленное
                            await self.db_manager.mark_car_as_notified(found_car.id)
                            
                            new_cars_count += 1
                            logger.info(f"  [NEW] Найдено новое объявление: {title[:50]}")
                            
                            # Небольшая задержка между уведомлениями
                            await asyncio.sleep(10)
                    
                    logger.info(f"  Валидных объявлений на {source_name}: {valid_count} из {len(cars)}, отфильтровано: {filtered_count}, уже в БД: {exists_count}, новых: {new_cars_count}")
                
                except Exception as e:
                    logger.error(f"Ошибка при проверке {source_name}: {e}", exc_info=True)
                    continue
        
        except Exception as e:
            logger.error(f"Ошибка при проверке фильтра #{user_filter.id}: {e}", exc_info=True)
    
    def start(self, interval_minutes: int = 3) -> None:
        """Запустить мониторинг"""
        # Запускаем периодическую проверку
        self.scheduler.add_job(
            self.check_ads,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='check_ads',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"Мониторинг запущен (интервал: {interval_minutes} минут)")
    
    def stop(self) -> None:
        """Остановить мониторинг"""
        self.scheduler.shutdown()
        logger.info("Мониторинг остановлен")
