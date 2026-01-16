"""
Базовый класс для парсеров объявлений
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import cloudscraper
import logging

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Базовый класс для всех парсеров"""
    
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    @abstractmethod
    async def search(self, filters: Dict) -> List[Dict]:
        """
        Поиск объявлений по фильтрам
        Возвращает список словарей с данными объявлений
        """
        pass
    
    def parse_price(self, price_str: str) -> Optional[float]:
        """Парсинг цены из строки"""
        if not price_str:
            return None
        # Удаляем все кроме цифр и точки
        price_str = ''.join(c for c in price_str if c.isdigit() or c == '.')
        try:
            return float(price_str)
        except ValueError:
            return None
    
    def parse_year(self, year_str: str) -> Optional[int]:
        """Парсинг года из строки"""
        if not year_str:
            return None
        year_str = ''.join(c for c in year_str if c.isdigit())
        try:
            year = int(year_str)
            if 1900 <= year <= 2030:
                return year
        except ValueError:
            pass
        return None
    
    def parse_mileage(self, mileage_str: str) -> Optional[int]:
        """Парсинг пробега из строки"""
        if not mileage_str:
            return None
        mileage_str = ''.join(c for c in mileage_str if c.isdigit())
        try:
            return int(mileage_str)
        except ValueError:
            return None
    
    def extract_body_type(self, text: str, properties: Optional[Dict] = None) -> Optional[str]:
        """Извлечение типа кузова из текста или свойств"""
        if not text:
            text = ''
        text_lower = text.lower()
        
        # Маппинг ключевых слов на типы кузовов
        body_keywords = {
            'sedan': ['седан', 'sedan'],
            'hatchback': ['хэтчбек', 'hatchback', 'хетчбек', 'хетч'],
            'universal': ['универсал', 'universal', 'wagon', 'вагон'],
            'wagon': ['универсал', 'universal', 'wagon', 'вагон'],
            'suv': ['внедорожник', 'suv', 'джип', 'jeep', 'внедорожн'],
            'crossover': ['кроссовер', 'crossover', 'кросс'],
            'coupe': ['купе', 'coupe'],
            'cabriolet': ['кабриолет', 'cabriolet', 'convertible', 'конвертируемый'],
            'minivan': ['минивэн', 'minivan', 'микроавтобус', 'минивен'],
            'van': ['фургон', 'van', 'микроавтобус'],
            'pickup': ['пикап', 'pickup'],
            'liftback': ['лифтбек', 'liftback'],
        }
        
        # Проверяем свойства (если переданы)
        if properties:
            if isinstance(properties, dict):
                # Ищем в разных полях
                body_field = properties.get('body_type') or properties.get('bodyType') or properties.get('кузов') or properties.get('body')
                if body_field:
                    body_str = str(body_field).lower()
                    for body_type, keywords in body_keywords.items():
                        if any(kw in body_str for kw in keywords):
                            return body_type
        
        # Ищем в тексте
        for body_type, keywords in body_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return body_type
        
        return None
    
    def matches_filters(self, car: Dict, filters: Dict) -> bool:
        """Проверка соответствия автомобиля фильтрам"""
        # Если фильтров нет, пропускаем все
        if not filters:
            return True
        
        # Оптимизация: кешируем нормализованные значения
        if filters.get('brand'):
            filter_brand = filters['brand'].lower().strip()
            car_brand = str(car.get('brand', '')).lower().strip()
            
            # Если в машине нет марки, но фильтр требует марку - не подходит
            if not car_brand:
                logger.debug(f"Фильтр по марке не пройден: у автомобиля нет марки (filter: {filter_brand})")
                return False
            
            # Нормализация для сравнения
            def normalize_brand(b):
                """Нормализация названия марки для сравнения"""
                b = b.lower().strip()
                # Замены для разных вариантов написания
                replacements = {
                    'mercedes': 'mercedes-benz',
                    'mercedes benz': 'mercedes-benz',
                    'mercedesbenz': 'mercedes-benz',
                    'vw': 'volkswagen',
                    'volkswagen': 'volkswagen',
                }
                for key, value in replacements.items():
                    if key in b:
                        return value
                return b.replace('-', '').replace(' ', '').replace('benz', '')
            
            filter_brand_norm = normalize_brand(filter_brand)
            car_brand_norm = normalize_brand(car_brand)
            
            # Проверка совпадения
            if (filter_brand_norm == car_brand_norm or 
                filter_brand_norm in car_brand_norm or 
                car_brand_norm in filter_brand_norm):
                pass  # Марка совпадает, продолжаем проверку других фильтров
            else:
                logger.debug(f"Фильтр по марке не пройден: car_brand='{car_brand}' != filter_brand='{filter_brand}'")
                return False
        
        if filters.get('model'):
            filter_model = filters['model'].lower().strip()
            car_model = str(car.get('model', '')).lower().strip()
            
            # Если в машине нет модели, но фильтр требует модель - не подходит
            if not car_model:
                logger.debug(f"Фильтр по модели не пройден: у автомобиля нет модели (filter: {filter_model})")
                return False
            
            # Нормализация для сравнения
            filter_model_norm = filter_model.replace('-', '').replace(' ', '').replace('_', '')
            car_model_norm = car_model.replace('-', '').replace(' ', '').replace('_', '')
            
            # Проверка совпадения
            if (filter_model_norm == car_model_norm or 
                filter_model_norm in car_model_norm or 
                car_model_norm in filter_model_norm):
                pass  # Модель совпадает, продолжаем проверку других фильтров
            else:
                logger.debug(f"Фильтр по модели не пройден: car_model='{car_model}' != filter_model='{filter_model}'")
                return False
        
        # Проверка года: если фильтр требует год, а у автомобиля его нет - не пропускаем
        if filters.get('year_from') is not None:
            car_year = car.get('year')
            if car_year is None:
                # Если фильтр требует минимальный год, а у автомобиля его нет - не подходит
                return False
            if car_year < filters['year_from']:
                return False
        
        if filters.get('year_to') is not None:
            car_year = car.get('year')
            if car_year is None:
                # Если фильтр требует максимальный год, а у автомобиля его нет - не подходит
                return False
            if car_year > filters['year_to']:
                return False
        
        # Проверка цены: если фильтр требует цену, а у автомобиля её нет - не пропускаем
        if filters.get('price_from_usd') is not None:
            car_price = car.get('price_usd')
            if car_price is None:
                # Если фильтр требует минимальную цену, а у автомобиля её нет - не подходит
                return False
            # Преобразуем цену в число, если она строка
            try:
                car_price = float(car_price) if isinstance(car_price, str) else car_price
            except (ValueError, TypeError):
                return False
            if car_price < filters['price_from_usd']:
                return False
        
        if filters.get('price_to_usd') is not None:
            car_price = car.get('price_usd')
            if car_price is None:
                # Если фильтр требует максимальную цену, а у автомобиля её нет - не подходит
                return False
            # Преобразуем цену в число, если она строка
            try:
                car_price = float(car_price) if isinstance(car_price, str) else car_price
            except (ValueError, TypeError):
                return False
            if car_price > filters['price_to_usd']:
                return False
        
        if filters.get('transmission') and car.get('transmission'):
            filter_trans = filters['transmission'].lower()
            car_trans = car['transmission'].lower()
            # Если фильтр требует автомат, а у машины механика или вариатор - не подходит
            if filter_trans == 'автомат':
                if 'механика' in car_trans or 'вариатор' in car_trans:
                    return False
            # Если фильтр требует механика, а у машины автомат или вариатор - не подходит
            elif filter_trans == 'механика':
                if 'автомат' in car_trans or 'вариатор' in car_trans:
                    return False
            # Если фильтр требует вариатор, а у машины автомат или механика - не подходит
            elif filter_trans == 'вариатор':
                if 'автомат' in car_trans or 'механика' in car_trans:
                    return False
            # Точное совпадение
            elif filter_trans not in car_trans:
                return False
        
        if filters.get('engine_type') and car.get('engine_type'):
            filter_engine = filters['engine_type'].lower()
            car_engine = car['engine_type'].lower()
            if filter_engine not in car_engine:
                return False
        
        # Проверка типа кузова
        if filters.get('body_type') and car.get('body_type'):
            filter_body = filters['body_type'].lower().strip()
            car_body = str(car.get('body_type', '')).lower().strip()
            
            # Маппинг для разных вариантов написания
            body_type_mapping = {
                'sedan': ['седан', 'sedan'],
                'hatchback': ['хэтчбек', 'hatchback', 'хетчбек'],
                'universal': ['универсал', 'universal', 'wagon', 'вагон'],
                'wagon': ['универсал', 'universal', 'wagon', 'вагон'],
                'suv': ['внедорожник', 'suv', 'джип'],
                'crossover': ['кроссовер', 'crossover'],
                'coupe': ['купе', 'coupe'],
                'cabriolet': ['кабриолет', 'cabriolet', 'convertible', 'конвертируемый'],
                'minivan': ['минивэн', 'minivan', 'микроавтобус'],
                'van': ['фургон', 'van', 'микроавтобус'],
                'pickup': ['пикап', 'pickup'],
                'liftback': ['лифтбек', 'liftback'],
            }
            
            # Получаем варианты для фильтра
            filter_variants = body_type_mapping.get(filter_body, [filter_body])
            
            # Проверяем совпадение
            if not any(variant in car_body for variant in filter_variants):
                logger.debug(f"Фильтр по типу кузова не пройден: car_body='{car_body}' != filter_body='{filter_body}'")
                return False
        
        return True
