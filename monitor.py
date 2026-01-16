"""
Фоновая задача для мониторинга объявлений
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from db_manager import DBManager
from parsers import AvByParser, KufarParser, OnlinerParser, AbwParser
from notifications import send_notification
import asyncio
from typing import Dict, List

logger = logging.getLogger(__name__)


class MonitorService:
    """Сервис для мониторинга объявлений"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db_manager = DBManager()
        self.parsers = {
            'av.by': AvByParser(),
            'kufar.by': KufarParser(),
            'ab.onliner.by': OnlinerParser(),
            'abw.by': AbwParser(),
        }
    
    async def check_ads(self):
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
    
    async def check_filter(self, user_filter):
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
                    # Ограничиваем количество проверяемых объявлений для оптимизации
                    # Проверяем только первые 30 самых новых объявлений
                    # Это предотвращает отправку уведомлений о старых объявлениях при первом запуске
                    cars_to_check = cars[:30]
                    
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
                            continue
                        
                        valid_count += 1
                        
                        # Проверяем, не было ли уже это объявление
                        exists = await self.db_manager.check_car_exists(
                            car['source'],
                            car['ad_id']
                        )
                        
                        if not exists:
                            # Удаляем поля, которых нет в модели FoundCar
                            car_data = {k: v for k, v in car.items() 
                                       if k in ['source', 'ad_id', 'title', 'price_usd', 'price_byn', 
                                               'year', 'mileage', 'engine_volume', 'city', 'url', 
                                               'image_url', 'transmission', 'engine_type']}
                            
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
                    
                    logger.info(f"  Валидных объявлений на {source_name}: {valid_count} из {len(cars)}, новых: {new_cars_count}")
                
                except Exception as e:
                    logger.error(f"Ошибка при проверке {source_name}: {e}", exc_info=True)
                    continue
        
        except Exception as e:
            logger.error(f"Ошибка при проверке фильтра #{user_filter.id}: {e}", exc_info=True)
    
    def start(self, interval_minutes: int = 3):
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
    
    def stop(self):
        """Остановить мониторинг"""
        self.scheduler.shutdown()
        logger.info("Мониторинг остановлен")
