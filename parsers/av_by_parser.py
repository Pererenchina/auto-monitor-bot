"""
Парсер для av.by

Использует HTML-парсинг с cloudscraper для обхода защиты.
Данные извлекаются из JSON в __NEXT_DATA__ script теге.
"""
import asyncio
import logging
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class AvByParser(BaseParser):
    """Парсер объявлений с av.by"""
    
    BASE_URL = "https://cars.av.by/filter"
    BASE_URL_ALT = "https://cars.av.by/"
    
    def __init__(self):
        super().__init__()
        # Используем cloudscraper для обхода Cloudflare с улучшенными настройками
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=15  # Увеличенная задержка между запросами
        )
        # Улучшенные заголовки
        self.headers.update({
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на av.by с retry логикой"""
        results = []
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Формируем URL с фильтрами
                url = self.BASE_URL
                params = []
                
                # Маппинг брендов для av.by (ID брендов в системе av.by)
                # Полный список можно получить через API или из HTML страницы
                brand_map = {
                    'BMW': '6',
                    'Bmw': '6',
                    'bmw': '6',
                    'Mercedes': '8',
                    'Mercedes-Benz': '8',
                    'Mercedes Benz': '8',
                    'mercedes': '8',
                    'mercedes-benz': '8',
                    'Audi': '1',
                    'audi': '1',
                    'Toyota': '14',
                    'toyota': '14',
                    'Volkswagen': '15',
                    'volkswagen': '15',
                    'VW': '15',
                    'vw': '15',
                    'Ford': '5',
                    'ford': '5',
                    'Opel': '11',
                    'opel': '11',
                    'Renault': '12',
                    'renault': '12',
                    'Peugeot': '10',
                    'peugeot': '10',
                    'Nissan': '9',
                    'nissan': '9',
                    'Hyundai': '7',
                    'hyundai': '7',
                    'Kia': '13',
                    'kia': '13',
                    'Mazda': '16',
                    'mazda': '16',
                    'Skoda': '17',
                    'skoda': '17',
                    'Volvo': '18',
                    'volvo': '18',
                    'Fiat': '4',
                    'fiat': '4',
                    'Tesla': '19',
                    'tesla': '19',
                    'Chevrolet': '3',
                    'chevrolet': '3',
                    'Citroen': '20',
                    'citroen': '20',
                    'Honda': '21',
                    'honda': '21',
                    'Lexus': '22',
                    'lexus': '22',
                    'Mitsubishi': '23',
                    'mitsubishi': '23',
                    'Subaru': '24',
                    'subaru': '24',
                    'Suzuki': '25',
                    'suzuki': '25',
                }
                
                # Добавляем фильтры в URL
                if filters.get('brand'):
                    brand_id = brand_map.get(filters['brand'], '')
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
                
                # Если есть фильтры, добавляем их в URL
                if params:
                    url += '?' + '&'.join(params)
                    logger.info(f"av.by: URL с фильтрами: {url}")
                
                # Добавляем задержку перед запросом для избежания rate limiting
                if attempt > 0:
                    wait_time = 5 * (attempt + 1)  # Экспоненциальная задержка: 10, 15, 20 сек
                    logger.warning(f"av.by: Повторная попытка {attempt + 1}/{max_retries}, жду {wait_time} сек...")
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(2)  # Задержка для первого запроса
                
                # Выполняем запрос синхронно (cloudscraper не поддерживает async напрямую)
                # Используем run_in_executor для асинхронности
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
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
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    logger.info(f"av.by: Получен HTML, размер: {len(response.text)} символов")
                    
                    # Ищем __NEXT_DATA__ script
                    script = soup.find('script', id='__NEXT_DATA__')
                    if not script:
                        # Ищем в обычных script тегах
                        scripts = soup.find_all('script', string=re.compile(r'__NEXT_DATA__'))
                        if scripts:
                            script = scripts[0]
                    
                    if not script:
                        logger.warning("av.by: Не найден __NEXT_DATA__ script")
                
                if script and script.string:
                    try:
                        data = json.loads(script.string)
                        # Извлекаем объявления из структуры - пробуем разные пути
                        adverts = (
                            data.get('props', {}).get('initialState', {}).get('filter', {}).get('main', {}).get('adverts', []) or
                            data.get('props', {}).get('pageProps', {}).get('adverts', []) or
                            data.get('props', {}).get('initialState', {}).get('adverts', []) or
                            data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('adverts', []) or
                            []
                        )
                        
                        logger.info(f"av.by: Найдено объявлений в JSON: {len(adverts)}")
                        
                        # Если фильтры применены в URL, но все равно получаем все объявления,
                        # возможно фильтры не работают на сервере - логируем это
                        if filters and len(adverts) > 0:
                            # Проверяем первые несколько объявлений на соответствие фильтрам
                            sample_count = min(5, len(adverts))
                            matching_count = 0
                            for i in range(sample_count):
                                sample_ad = adverts[i]
                                sample_car = self._parse_ad(sample_ad)
                                if sample_car and self.matches_filters(sample_car, filters):
                                    matching_count += 1
                            
                            if matching_count == 0 and sample_count > 0:
                                logger.warning(f"av.by: Фильтры в URL могут не работать - из {sample_count} проверенных объявлений ни одно не соответствует фильтрам")
                        
                        # Если не нашли объявления, пробуем альтернативный URL
                        if not adverts:
                            # Пробуем альтернативный URL
                            alt_url = self.BASE_URL_ALT if url == self.BASE_URL else self.BASE_URL
                            await asyncio.sleep(2)  # Задержка перед альтернативным запросом
                            alt_response = await loop.run_in_executor(
                                None,
                                lambda: self.scraper.get(
                                    alt_url, 
                                    timeout=30,
                                    headers={
                                        **self.headers,
                                        'Referer': 'https://av.by/',
                                    }
                                )
                            )
                            if alt_response.status_code == 200:
                                alt_soup = BeautifulSoup(alt_response.text, 'lxml')
                                alt_script = alt_soup.find('script', id='__NEXT_DATA__')
                                if alt_script and alt_script.string:
                                    alt_data = json.loads(alt_script.string)
                                    adverts = (
                                        alt_data.get('props', {}).get('initialState', {}).get('filter', {}).get('main', {}).get('adverts', []) or
                                        alt_data.get('props', {}).get('pageProps', {}).get('adverts', []) or
                                        alt_data.get('props', {}).get('initialState', {}).get('adverts', []) or
                                        []
                                    )
                        
                        parsed_count = 0
                        filtered_count = 0
                        first_filtered = None
                        for ad in adverts:
                            car_data = self._parse_ad(ad)
                            if car_data:
                                parsed_count += 1
                                # Применяем фильтры (включая фильтрацию по бренду после парсинга)
                                if self.matches_filters(car_data, filters):
                                    results.append(car_data)
                                else:
                                    filtered_count += 1
                                    # Сохраняем первый отфильтрованный для логирования
                                    if filtered_count == 1 and first_filtered is None:
                                        first_filtered = car_data
                        
                        # Логируем первый отфильтрованный после цикла
                        if first_filtered:
                            logger.info(f"av.by: Пример отфильтрованного: brand='{first_filtered.get('brand')}', model='{first_filtered.get('model')}', filter_brand='{filters.get('brand')}', filter_model='{filters.get('model')}', year={first_filtered.get('year')}, filter_year_from={filters.get('year_from')}, price_usd={first_filtered.get('price_usd')}, filter_price_to={filters.get('price_to_usd')}")
                        
                        logger.info(f"av.by: Распарсено {parsed_count} из {len(adverts)}, отфильтровано {filtered_count}, осталось {len(results)}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON av.by: {e}")
                        if attempt == max_retries - 1:
                            logger.exception("Полная трассировка ошибки JSON")
                
                elif response.status_code == 429:
                    # Rate limit - ждем дольше и пробуем снова
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.warning(f"av.by: Rate limit (429), жду {wait_time} секунд перед повтором...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"av.by: Превышен лимит запросов после {max_retries} попыток")
                        break
                else:
                    # Другая ошибка HTTP
                    if attempt < max_retries - 1:
                        logger.warning(f"av.by: HTTP {response.status_code}, повтор через {2 * (attempt + 1)} сек...")
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    else:
                        logger.error(f"av.by: HTTP {response.status_code} после {max_retries} попыток")
                        break
                
                # Если успешно получили данные, выходим из цикла retry
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"av.by: Ошибка (попытка {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                else:
                    logger.error(f"Ошибка при парсинге av.by после {max_retries} попыток: {e}", exc_info=True)
        
        return results
    
    def _parse_ad(self, ad: Dict) -> Dict:
        """Парсинг одного объявления"""
        try:
            ad_id = str(ad.get('id', ''))
            
            # Извлекаем марку и модель из properties
            brand = ''
            model = ''
            properties = ad.get('properties', [])
            
            # Сначала пробуем напрямую из ad (на случай другой структуры)
            brand_raw = ad.get('brand') or ad.get('brandName') or ad.get('make')
            if brand_raw:
                if isinstance(brand_raw, dict):
                    brand = brand_raw.get('name', '') or str(brand_raw)
                else:
                    brand = str(brand_raw)
            
            model_raw = ad.get('model') or ad.get('modelName')
            if model_raw:
                if isinstance(model_raw, dict):
                    model = model_raw.get('name', '') or str(model_raw)
                else:
                    model = str(model_raw)
            
            # Затем пробуем из properties
            for prop in properties:
                if isinstance(prop, dict):
                    prop_name = prop.get('name', '')
                    prop_value = prop.get('value', '')
                    if prop_name == 'brand' and not brand:
                        brand = str(prop_value)
                    elif prop_name == 'model' and not model:
                        model = str(prop_value)
            
            # Формируем название из марки и модели
            if brand or model:
                title = f"{brand} {model}".strip()
                # Если есть год, добавляем его для более информативного названия
                year = ad.get('year') or (ad.get('properties', []) and next((p.get('value') for p in ad.get('properties', []) if isinstance(p, dict) and p.get('name') == 'year'), None))
                if year and str(year).isdigit():
                    title = f"{title} {year}".strip()
            else:
                title = ''
            
            # Цена - структура: price.usd.amount и price.byn.amount
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
            
            # Конвертация валют, если одна из цен отсутствует (примерный курс: 1 USD = 3.3 BYN)
            if price_usd and not price_byn:
                price_byn = price_usd * 3.3
            elif price_byn and not price_usd:
                price_usd = price_byn / 3.3
            
            # Характеристики
            year = ad.get('year')
            
            # Пробег - извлекаем из properties
            mileage = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'mileage':
                    mileage_value = prop.get('value')
                    if isinstance(mileage_value, (int, float)):
                        mileage = int(mileage_value)
                    elif isinstance(mileage_value, str):
                        # Убираем пробелы и пробуем преобразовать
                        mileage_str = mileage_value.replace(' ', '').replace(',', '')
                        try:
                            mileage = int(mileage_str)
                        except:
                            pass
                    break
            
            # Если не нашли в properties, пробуем старый способ
            if mileage is None:
                odometer = ad.get('odometer')
                if odometer:
                    if isinstance(odometer, dict):
                        mileage = odometer.get('value')
                    elif isinstance(odometer, (int, float)):
                        mileage = int(odometer)
            
            # Объем двигателя - извлекаем из properties
            engine_volume = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'engine_capacity':
                    volume_str = str(prop.get('value', '')).replace(',', '.')
                    try:
                        engine_volume = float(volume_str)
                    except:
                        pass
                    break
            
            # Если не нашли в properties, пробуем старый способ
            if engine_volume is None:
                engine_volume = ad.get('engineDisplacement') or ad.get('engineVolume')
            city = ad.get('locationName', '')
            
            # Фото
            image_url = None
            photos = ad.get('photos', [])
            if photos and len(photos) > 0:
                first_photo = photos[0]
                if isinstance(first_photo, dict):
                    image_url = first_photo.get('medium', {}).get('url') or first_photo.get('url')
                elif isinstance(first_photo, str):
                    image_url = first_photo
            
            # Коробка передач - сначала пробуем из properties
            transmission = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'transmission_type':
                    gearbox = str(prop.get('value', ''))
                    gearbox_lower = gearbox.lower()
                    if 'вариатор' in gearbox_lower or 'cvt' in gearbox_lower:
                        transmission = 'Вариатор'
                    elif 'автомат' in gearbox_lower or 'automatic' in gearbox_lower:
                        transmission = 'Автомат'
                    elif 'механика' in gearbox_lower or 'manual' in gearbox_lower:
                        transmission = 'Механика'
                    break
            
            # Если не нашли в properties, пробуем из gearbox
            if not transmission:
                gearbox = ad.get('gearbox')
                if gearbox:
                    if isinstance(gearbox, dict):
                        gearbox = gearbox.get('name', '') or str(gearbox)
                    gearbox_lower = str(gearbox).lower()
                    if 'вариатор' in gearbox_lower or 'cvt' in gearbox_lower:
                        transmission = 'Вариатор'
                    elif 'автомат' in gearbox_lower or 'automatic' in gearbox_lower:
                        transmission = 'Автомат'
                    elif 'механика' in gearbox_lower or 'manual' in gearbox_lower:
                        transmission = 'Механика'
            
            # Тип двигателя - извлекаем из properties
            engine_type = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'engine_type':
                    fuel = str(prop.get('value', ''))
                    fuel_lower = fuel.lower()
                    if 'бензин' in fuel_lower or 'petrol' in fuel_lower or 'gasoline' in fuel_lower:
                        engine_type = 'Бензин'
                    elif 'дизель' in fuel_lower or 'diesel' in fuel_lower:
                        engine_type = 'Дизель'
                    elif 'электро' in fuel_lower or 'electric' in fuel_lower:
                        engine_type = 'Электро'
                    break
            
            # Если не нашли в properties, пробуем старый способ
            if not engine_type:
                fuel = ad.get('fuelType')
                if fuel:
                    if isinstance(fuel, dict):
                        fuel = fuel.get('name', '') or str(fuel)
                    fuel_lower = str(fuel).lower()
                    if 'бензин' in fuel_lower or 'petrol' in fuel_lower or 'gasoline' in fuel_lower:
                        engine_type = 'Бензин'
                    elif 'дизель' in fuel_lower or 'diesel' in fuel_lower:
                        engine_type = 'Дизель'
                    elif 'электро' in fuel_lower or 'electric' in fuel_lower:
                        engine_type = 'Электро'
            
            # URL - пробуем извлечь из данных, иначе формируем
            url = ad.get('publicUrl') or ad.get('url') or ad.get('link')
            if not url:
                # Формируем URL из ID
                url = f"https://av.by/offer/{ad_id}"
            elif not url.startswith('http'):
                url = f"https://av.by{url}" if url.startswith('/') else f"https://av.by/{url}"
            
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
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге объявления av.by: {e}", exc_info=True)
            return None
