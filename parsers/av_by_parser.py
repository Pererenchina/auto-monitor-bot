"""
Парсер для av.by
Переписан с нуля для упрощения и улучшения надежности
"""
# Стандартная библиотека
import asyncio
import json
import logging
import re
from typing import List, Dict, Optional

# Сторонние библиотеки
import cloudscraper
from bs4 import BeautifulSoup

# Локальные импорты
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class AvByParser(BaseParser):
    """Парсер объявлений с av.by"""
    
    BASE_URL = "https://cars.av.by/filter"
    BASE_URL_ALT = "https://cars.av.by/"
    MAX_RETRIES = 3
    
    # Маппинг брендов для av.by (ID брендов в системе av.by)
    BRAND_MAP = {
        'BMW': '6', 'Bmw': '6', 'bmw': '6',
        'Mercedes': '8', 'Mercedes-Benz': '8', 'Mercedes Benz': '8',
        'mercedes': '8', 'mercedes-benz': '8',
        'Audi': '1', 'audi': '1',
        'Toyota': '14', 'toyota': '14',
        'Volkswagen': '15', 'volkswagen': '15', 'VW': '15', 'vw': '15',
        'Ford': '5', 'ford': '5',
        'Opel': '11', 'opel': '11',
        'Renault': '12', 'renault': '12',
        'Peugeot': '10', 'peugeot': '10',
        'Nissan': '9', 'nissan': '9',
        'Hyundai': '7', 'hyundai': '7',
        'Kia': '13', 'kia': '13',
        'Mazda': '16', 'mazda': '16',
        'Skoda': '17', 'skoda': '17',
        'Volvo': '18', 'volvo': '18',
        'Fiat': '4', 'fiat': '4',
        'Tesla': '19', 'tesla': '19',
        'Chevrolet': '3', 'chevrolet': '3',
        'Citroen': '20', 'citroen': '20',
        'Honda': '21', 'honda': '21',
        'Lexus': '22', 'lexus': '22',
        'Mitsubishi': '23', 'mitsubishi': '23',
        'Subaru': '24', 'subaru': '24',
        'Suzuki': '25', 'suzuki': '25',
    }
    
    def __init__(self):
        super().__init__()
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
            delay=15
        )
        self.headers.update({
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на av.by с retry логикой"""
        results = []
        
        for attempt in range(self.MAX_RETRIES):
            try:
                url = self._build_url(filters)
                if url != self.BASE_URL:
                    logger.info(f"av.by: URL с фильтрами: {url}")
                
                # Задержка перед запросом
                if attempt > 0:
                    wait_time = 5 * (attempt + 1)
                    logger.warning(f"av.by: Повторная попытка {attempt + 1}/{self.MAX_RETRIES}, жду {wait_time} сек...")
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(2)
                
                # Выполняем запрос
                response = await self._fetch_page(url)
                
                if response.status_code == 200:
                    adverts = self._extract_adverts_from_html(response.text)
                    
                    if not adverts and url == self.BASE_URL:
                        # Пробуем альтернативный URL
                        await asyncio.sleep(2)
                        alt_response = await self._fetch_page(self.BASE_URL_ALT)
                        if alt_response.status_code == 200:
                            adverts = self._extract_adverts_from_html(alt_response.text)
                    
                    if adverts:
                        results = self._parse_and_filter(adverts, filters)
                        # Выходим только если нашли объявления
                        break
                    else:
                        # Если объявлений не найдено, пробуем еще раз
                        if attempt < self.MAX_RETRIES - 1:
                            logger.warning(f"av.by: Объявления не найдены (попытка {attempt + 1}/{self.MAX_RETRIES}), повтор...")
                            await asyncio.sleep(5 * (attempt + 1))
                            continue
                        else:
                            logger.warning(f"av.by: Объявления не найдены после {self.MAX_RETRIES} попыток")
                            break
                elif response.status_code == 429:
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.warning(f"av.by: Rate limit (429), жду {wait_time} секунд...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"av.by: Превышен лимит запросов после {self.MAX_RETRIES} попыток")
                        break
                else:
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"av.by: HTTP {response.status_code}, повтор через {2 * (attempt + 1)} сек...")
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    else:
                        logger.error(f"av.by: HTTP {response.status_code} после {self.MAX_RETRIES} попыток")
                        break
                        
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"av.by: Ошибка (попытка {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                else:
                    logger.error(f"Ошибка при парсинге av.by после {self.MAX_RETRIES} попыток: {e}", exc_info=True)
        
        return results
    
    def _build_url(self, filters: Dict) -> str:
        """Формирование URL с фильтрами"""
        url = self.BASE_URL
        params = []
        
        if filters.get('brand'):
            brand_id = self.BRAND_MAP.get(filters['brand'], '')
            if brand_id:
                params.append(f"brands[0][brand]={brand_id}")
        
        if filters.get('year_from'):
            params.append(f"year_from={filters['year_from']}")
        if filters.get('year_to'):
            params.append(f"year_to={filters['year_to']}")
        if filters.get('price_from_usd'):
            params.append(f"price_from={int(filters['price_from_usd'])}")
        if filters.get('price_to_usd'):
            params.append(f"price_to={int(filters['price_to_usd'])}")
        
        if params:
            url += '?' + '&'.join(params)
        
        return url
    
    async def _fetch_page(self, url: str):
        """Выполнение HTTP запроса"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.scraper.get(
                url,
                timeout=30,
                headers={
                    **self.headers,
                    'Referer': 'https://cars.av.by/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
            )
        )
    
    def _extract_adverts_from_html(self, html: str) -> List[Dict]:
        """Извлечение объявлений из HTML"""
        soup = BeautifulSoup(html, 'lxml')
        logger.info(f"av.by: Получен HTML, размер: {len(html)} символов")
        
        # Ищем __NEXT_DATA__ script
        script = soup.find('script', id='__NEXT_DATA__')
        if not script:
            scripts = soup.find_all('script', string=re.compile(r'__NEXT_DATA__'))
            if scripts:
                script = scripts[0]
        
        if not script or not script.string:
            logger.warning("av.by: Не найден __NEXT_DATA__ script")
            return []
        
        try:
            data = json.loads(script.string)
            # Пробуем разные пути к объявлениям
            adverts = (
                data.get('props', {}).get('initialState', {}).get('filter', {}).get('main', {}).get('adverts', []) or
                data.get('props', {}).get('pageProps', {}).get('adverts', []) or
                data.get('props', {}).get('initialState', {}).get('adverts', []) or
                data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('adverts', []) or
                []
            )
            
            # Если не нашли объявления, пробуем более глубокий поиск
            if not adverts:
                # Пробуем найти в других местах структуры
                def find_adverts(obj, path=""):
                    """Рекурсивный поиск объявлений в структуре"""
                    if isinstance(obj, dict):
                        # Проверяем ключи, которые могут содержать объявления
                        for key, value in obj.items():
                            if key in ['adverts', 'advertisements', 'items', 'listings', 'results'] and isinstance(value, list):
                                if value and len(value) > 0:
                                    # Проверяем, что это действительно объявления (есть поле id или ad_id)
                                    if isinstance(value[0], dict) and ('id' in value[0] or 'ad_id' in value[0]):
                                        return value
                            result = find_adverts(value, f"{path}.{key}")
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            result = find_adverts(item, f"{path}[{i}]")
                            if result:
                                return result
                    return None
                
                found_adverts = find_adverts(data)
                if found_adverts:
                    adverts = found_adverts
                    logger.info(f"av.by: Найдено объявлений через рекурсивный поиск: {len(adverts)}")
            
            logger.info(f"av.by: Найдено объявлений в JSON: {len(adverts)}")
            return adverts
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON av.by: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при извлечении объявлений av.by: {e}", exc_info=True)
            return []
    
    def _parse_and_filter(self, adverts: List[Dict], filters: Dict) -> List[Dict]:
        """Парсинг и фильтрация объявлений"""
        results = []
        parsed_count = 0
        filtered_count = 0
        first_filtered = None
        
        for ad in adverts:
            car_data = self._parse_ad(ad)
            if car_data:
                parsed_count += 1
                if self.matches_filters(car_data, filters):
                    results.append(car_data)
                else:
                    filtered_count += 1
                    if filtered_count == 1 and first_filtered is None:
                        first_filtered = car_data
        
        if first_filtered:
            logger.info(f"av.by: Пример отфильтрованного: brand='{first_filtered.get('brand')}', model='{first_filtered.get('model')}', filter_brand='{filters.get('brand')}', filter_model='{filters.get('model')}', year={first_filtered.get('year')}, filter_year_from={filters.get('year_from')}, price_usd={first_filtered.get('price_usd')}, filter_price_to={filters.get('price_to_usd')}")
        
        logger.info(f"av.by: Распарсено {parsed_count} из {len(adverts)}, отфильтровано {filtered_count}, осталось {len(results)}")
        return results
    
    def _parse_ad(self, ad: Dict) -> Optional[Dict]:
        """Парсинг одного объявления"""
        try:
            ad_id = str(ad.get('id', ''))
            if not ad_id:
                return None
            
            properties = ad.get('properties', [])
            
            # Марка и модель
            brand, model = self.extract_brand_model_from_properties(properties, ad)
            
            # Заголовок
            title = self._build_title(brand, model, ad)
            
            # Цены
            price_usd, price_byn = self._extract_prices(ad)
            
            # Год
            year = ad.get('year')
            
            # Пробег
            mileage = self._extract_mileage(properties, ad)
            
            # Объем двигателя
            engine_volume = self._extract_engine_volume(properties, ad)
            
            # Город
            city = ad.get('locationName', '')
            
            # Фото
            image_url = self._extract_image(ad)
            
            # Коробка передач
            transmission = self._extract_transmission(properties, ad)
            
            # Тип двигателя
            engine_type = self._extract_engine_type(properties, ad)
            
            # Тип кузова
            body_type = self._extract_body_type(properties, ad, title)
            
            # URL
            url = self._extract_url(ad, ad_id)
            
            return {
                'source': 'av.by',
                'ad_id': ad_id,
                'title': title or f"{brand} {model}".strip(),
                'brand': brand,
                'model': model,
                'price_usd': price_usd,
                'price_byn': price_byn,
                'year': year,
                'mileage': mileage,
                'engine_volume': engine_volume,
                'city': city,
                'url': url,
                'image_url': image_url,
                'transmission': transmission,
                'engine_type': engine_type,
                'body_type': body_type,
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге объявления av.by: {e}", exc_info=True)
            return None
    
    def _build_title(self, brand: str, model: str, ad: Dict) -> str:
        """Формирование заголовка"""
        if brand or model:
            title = f"{brand} {model}".strip()
            year = ad.get('year') or next(
                (p.get('value') for p in ad.get('properties', [])
                 if isinstance(p, dict) and p.get('name') == 'year'),
                None
            )
            if year and str(year).isdigit():
                title = f"{title} {year}".strip()
            return title
        return ''
    
    def _extract_prices(self, ad: Dict) -> tuple:
        """Извлечение цен"""
        price_usd = None
        price_byn = None
        price_info = ad.get('price', {})
        
        if price_info:
            usd_info = price_info.get('usd', {})
            byn_info = price_info.get('byn', {})
            
            if isinstance(usd_info, dict):
                price_usd = usd_info.get('amount')
            elif isinstance(usd_info, (int, float)):
                price_usd = usd_info
            
            if isinstance(byn_info, dict):
                price_byn = byn_info.get('amount')
            elif isinstance(byn_info, (int, float)):
                price_byn = byn_info
        
        price_usd, price_byn = self.normalize_prices(price_usd, price_byn, validate=False)
        return price_usd, price_byn
    
    def _extract_mileage(self, properties: List[Dict], ad: Dict) -> Optional[int]:
        """Извлечение пробега"""
        for prop in properties:
            if isinstance(prop, dict) and prop.get('name') == 'mileage':
                mileage_value = prop.get('value')
                if isinstance(mileage_value, (int, float)):
                    return self.parse_mileage(str(mileage_value))
                elif isinstance(mileage_value, str):
                    return self.parse_mileage(mileage_value)
        
        # Если не нашли в properties
        odometer = ad.get('odometer')
        if odometer:
            if isinstance(odometer, dict):
                return self.parse_mileage(str(odometer.get('value', '')))
            elif isinstance(odometer, (int, float)):
                return self.parse_mileage(str(odometer))
            elif isinstance(odometer, str):
                return self.parse_mileage(odometer)
        
        return None
    
    def _extract_engine_volume(self, properties: List[Dict], ad: Dict) -> Optional[float]:
        """Извлечение объема двигателя"""
        for prop in properties:
            if isinstance(prop, dict) and prop.get('name') == 'engine_capacity':
                volume_str = str(prop.get('value', '')).replace(',', '.')
                try:
                    return float(volume_str)
                except (ValueError, TypeError):
                    pass
        
        # Если не нашли в properties
        engine_volume = ad.get('engineDisplacement') or ad.get('engineVolume')
        if engine_volume:
            try:
                return float(str(engine_volume).replace(',', '.'))
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _extract_image(self, ad: Dict) -> Optional[str]:
        """Извлечение URL изображения"""
        photos = ad.get('photos', [])
        if photos and len(photos) > 0:
            first_photo = photos[0]
            if isinstance(first_photo, dict):
                return first_photo.get('medium', {}).get('url') or first_photo.get('url')
            elif isinstance(first_photo, str):
                return first_photo
        return None
    
    def _extract_transmission(self, properties: List[Dict], ad: Dict) -> Optional[str]:
        """Извлечение коробки передач"""
        for prop in properties:
            if isinstance(prop, dict) and prop.get('name') == 'transmission_type':
                gearbox = str(prop.get('value', '')).lower()
                if any(x in gearbox for x in ['вариатор', 'cvt']):
                    return 'Вариатор'
                elif any(x in gearbox for x in ['автомат', 'automatic']):
                    return 'Автомат'
                elif any(x in gearbox for x in ['механика', 'manual']):
                    return 'Механика'
        
        # Если не нашли в properties
        gearbox = ad.get('gearbox')
        if gearbox:
            if isinstance(gearbox, dict):
                gearbox = gearbox.get('name', '') or str(gearbox)
            gearbox_lower = str(gearbox).lower()
            if any(x in gearbox_lower for x in ['вариатор', 'cvt']):
                return 'Вариатор'
            elif any(x in gearbox_lower for x in ['автомат', 'automatic']):
                return 'Автомат'
            elif any(x in gearbox_lower for x in ['механика', 'manual']):
                return 'Механика'
        
        return None
    
    def _extract_engine_type(self, properties: List[Dict], ad: Dict) -> Optional[str]:
        """Извлечение типа двигателя"""
        for prop in properties:
            if isinstance(prop, dict) and prop.get('name') == 'engine_type':
                fuel = str(prop.get('value', '')).lower()
                if any(x in fuel for x in ['бензин', 'petrol', 'gasoline']):
                    return 'Бензин'
                elif any(x in fuel for x in ['дизель', 'diesel']):
                    return 'Дизель'
                elif any(x in fuel for x in ['электро', 'electric']):
                    return 'Электро'
        
        # Если не нашли в properties
        fuel = ad.get('fuelType')
        if fuel:
            if isinstance(fuel, dict):
                fuel = fuel.get('name', '') or str(fuel)
            fuel_lower = str(fuel).lower()
            if any(x in fuel_lower for x in ['бензин', 'petrol', 'gasoline']):
                return 'Бензин'
            elif any(x in fuel_lower for x in ['дизель', 'diesel']):
                return 'Дизель'
            elif any(x in fuel_lower for x in ['электро', 'electric']):
                return 'Электро'
        
        return None
    
    def _extract_body_type(self, properties: List[Dict], ad: Dict, title: str) -> Optional[str]:
        """Извлечение типа кузова"""
        for prop in properties:
            if isinstance(prop, dict):
                prop_name = prop.get('name', '').lower()
                if prop_name in ['body_type', 'bodytype', 'кузов', 'body']:
                    return self.extract_body_type(str(prop.get('value', '')), properties)
        
        # Если не нашли в properties, пробуем из текста
        full_text = f"{title} {ad.get('description', '')}"
        return self.extract_body_type(full_text, ad)
    
    def _extract_url(self, ad: Dict, ad_id: str) -> str:
        """Извлечение URL объявления"""
        url = ad.get('publicUrl') or ad.get('url') or ad.get('link')
        if not url:
            url = f"https://av.by/offer/{ad_id}"
        elif not url.startswith('http'):
            url = f"https://av.by{url}" if url.startswith('/') else f"https://av.by/{url}"
        return url
