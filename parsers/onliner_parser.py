"""
Парсер для cars.onliner.by / ab.onliner.by

ВАЖНО: Onliner.by не предоставляет публичного API для автомобилей.
Используется HTML-парсинг с Playwright для рендеринга JavaScript и получения полного HTML.
"""
# Стандартная библиотека
import asyncio
import json
import logging
import re
from typing import List, Dict

# Сторонние библиотеки
import cloudscraper
from bs4 import BeautifulSoup

# Локальные импорты
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

# Пробуем импортировать Playwright, если не установлен - используем cloudscraper
try:
    from playwright.async_api import (
        async_playwright,
        TimeoutError as PlaywrightTimeoutError
    )
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning(
        "Playwright не установлен. "
        "Установите: pip install playwright && playwright install chromium"
    )


class OnlinerParser(BaseParser):
    """Парсер объявлений с ab.onliner.by (автобарахолка onliner)"""
    
    BASE_URL = "https://ab.onliner.by/"
    
    def __init__(self):
        super().__init__()
        # Используем cloudscraper для обхода Cloudflare с улучшенными настройками (fallback)
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10
        )
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def _init_playwright(self):
        """Инициализация Playwright браузера"""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
            
            if not self.page:
                self.page = await self.browser.new_page()
                # Устанавливаем User-Agent
                await self.page.set_extra_http_headers({
                    'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                })
            
            return True
        except Exception as e:
            logger.error(f"ab.onliner.by: Ошибка инициализации Playwright: {e}")
            return False
    
    async def _fetch_with_playwright(self, url: str) -> str:
        """Получение HTML через Playwright с рендерингом JavaScript"""
        if not await self._init_playwright():
            raise Exception("Playwright не инициализирован")
        
        try:
            # Переходим на страницу
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Ждем загрузки объявлений (ищем элементы vehicle-form__offers-unit)
            try:
                # Пробуем разные селекторы для ожидания
                await self.page.wait_for_selector('a.vehicle-form__offers-unit, .vehicle-form__offers-unit, .vehicle-form__offers-list', timeout=15000)
            except PlaywrightTimeoutError:
                # Если не нашли за 15 секунд, ждем еще немного для полной загрузки
                logger.warning("ab.onliner.by: Не найдены элементы vehicle-form__offers-unit за 15 секунд, ждем дополнительно")
                await asyncio.sleep(3)
            
            # Получаем HTML после рендеринга JavaScript
            html_content = await self.page.content()
            return html_content
        except Exception as e:
            logger.error(f"ab.onliner.by: Ошибка при получении HTML через Playwright: {e}")
            raise
    
    async def _close_playwright(self):
        """Закрытие Playwright браузера"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
        except Exception as e:
            logger.error(f"ab.onliner.by: Ошибка при закрытии Playwright: {e}")
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на ab.onliner.by с улучшенным HTML парсингом"""
        results = []
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                # Добавляем задержку
                if attempt > 0:
                    await asyncio.sleep(3 * attempt)
                else:
                    await asyncio.sleep(1)
                
                # Формируем URL с фильтрами
                url = self.BASE_URL
                params = []
                
                # Добавляем фильтры в URL (если ab.onliner.by поддерживает их)
                if filters.get('brand'):
                    brand_slug = filters['brand'].lower().replace(' ', '-').replace('mercedes-benz', 'mercedes')
                    params.append(f"brand={brand_slug}")
                
                if filters.get('model'):
                    model_slug = filters['model'].lower().replace(' ', '-')
                    params.append(f"model={model_slug}")
                
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
                    logger.info(f"ab.onliner.by: URL с фильтрами: {url}")
                
                # Используем Playwright для рендеринга JavaScript, если доступен
                html_content = None
                if PLAYWRIGHT_AVAILABLE:
                    try:
                        html_content = await self._fetch_with_playwright(url)
                        logger.info(f"ab.onliner.by: Получен HTML через Playwright, размер: {len(html_content)} символов")
                    except Exception as e:
                        logger.warning(f"ab.onliner.by: Ошибка при использовании Playwright: {e}, используем cloudscraper")
                        html_content = None
                
                # Если Playwright не доступен или произошла ошибка, используем cloudscraper
                if not html_content:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.scraper.get(
                            url, 
                            timeout=30,
                            headers={
                                **self.headers,
                                'Referer': 'https://ab.onliner.by/',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            }
                        )
                    )
                    if response.status_code == 200:
                        html_content = response.text
                        logger.info(f"ab.onliner.by: Получен HTML через cloudscraper, размер: {len(html_content)} символов")
                    else:
                        logger.error(f"ab.onliner.by: Ошибка HTTP {response.status_code}")
                        continue
                
                if html_content:
                    soup = BeautifulSoup(html_content, 'lxml')
                    
                    # Парсим HTML напрямую (основной метод для onliner)
                    # Ищем объявления в HTML - используем правильные селекторы на основе реальной структуры
                    listings = []
                    
                    # Метод 1: Ищем элементы с классом vehicle-form__offers-unit (самый надежный способ)
                    # Это основной контейнер для каждого объявления на странице списка
                    offers_units = soup.find_all('a', class_=lambda x: x and 'vehicle-form__offers-unit' in str(x))
                    logger.info(f"ab.onliner.by: Найдено элементов vehicle-form__offers-unit: {len(offers_units)}")
                    
                    # Все элементы с классом vehicle-form__offers-unit - это объявления
                    listings = list(offers_units)
                    
                    logger.info(f"ab.onliner.by: Найдено объявлений: {len(listings)}")
                    
                    # Метод 2: Fallback - если метод 1 не нашел объявлений (используется редко)
                    if not listings:
                        selectors = [
                            ('div', {'class': lambda x: x and ('vehicle' in str(x).lower() or 'car' in str(x).lower() or 'auto' in str(x).lower())}),
                            ('article', {'class': lambda x: x and ('item' in str(x).lower() or 'listing' in str(x).lower())}),
                            ('div', {'class': lambda x: x and 'listing' in str(x).lower()}),
                            ('div', {'class': lambda x: x and 'card' in str(x).lower()}),
                            ('li', {'class': lambda x: x and ('item' in str(x).lower() or 'car' in str(x).lower())}),
                        ]
                        
                        for tag, attrs in selectors:
                            found = soup.find_all(tag, attrs)
                            if found:
                                for item in found:
                                    if item not in listings:
                                        listings.append(item)
                                logger.info(f"ab.onliner.by: Метод 2 нашел {len(found)} элементов через селектор {tag}")
                                break
                    
                    logger.info(f"ab.onliner.by: Найдено элементов для парсинга (после метода 2): {len(listings)}")
                    
                    # Метод 3: Fallback через data-атрибуты (используется только если метод 1 не нашел объявлений)
                    if len(listings) < 5:
                        # Пробуем разные варианты data-атрибутов
                        all_listings = soup.find_all('div', attrs={'data-id': re.compile(r'\d+')})
                        if not all_listings:
                            all_listings = soup.find_all('article', attrs={'data-id': re.compile(r'\d+')})
                        if not all_listings:
                            all_listings = soup.find_all('li', attrs={'data-id': re.compile(r'\d+')})
                        if not all_listings:
                            # Пробуем найти любые элементы с data-атрибутами, связанными с объявлениями
                            all_listings = soup.find_all(attrs={'data-id': re.compile(r'\d+')})
                            all_listings.extend(soup.find_all(attrs={'data-ad-id': re.compile(r'\d+')}))
                            all_listings.extend(soup.find_all(attrs={'data-vehicle-id': re.compile(r'\d+')}))
                        
                        # Фильтруем элементы - проверяем, что они содержат ссылку на объявление
                        # Если не нашли ссылки, все равно добавляем элементы с data-id (они могут содержать объявления)
                        for item in all_listings:
                            # Проверяем, что элемент содержит ссылку на объявление
                            # Пробуем разные варианты поиска ссылки
                            link = None
                            # Вариант 1: прямая ссылка с href
                            link = item.find('a', href=re.compile(r'/car/|/vehicle/|/auto/|\d+'))
                            if not link:
                                # Вариант 2: любая ссылка с href, содержащая цифры (ID)
                                link = item.find('a', href=re.compile(r'\d+'))
                            if not link:
                                # Вариант 3: ссылка внутри дочерних элементов
                                all_links = item.find_all('a', href=True)
                                for l in all_links:
                                    href = l.get('href', '')
                                    if href and not re.match(r'^https?://(www\.)?onliner\.by/?$', href):
                                        if re.search(r'/\d+', href) or re.search(r'\d{4,}', href):
                                            link = l
                                            break
                            
                            # Если нашли ссылку, добавляем элемент
                            if link:
                                href = link.get('href', '')
                                # Пропускаем ссылки на главную страницу
                                if href and not re.match(r'^https?://(www\.)?onliner\.by/?$', href):
                                    # Проверяем наличие ID в URL или в самом href
                                    if re.search(r'/\d+', href) or re.search(r'\d{4,}', href):
                                        if item not in listings:
                                            listings.append(item)
                            # Если не нашли ссылку, но есть data-id, все равно добавляем (может быть объявление)
                            elif ad_id := item.get('data-id', ''):
                                # Проверяем, что data-id содержит цифры (ID объявления)
                                if re.match(r'^\d+$', str(ad_id)):
                                    if item not in listings:
                                        listings.append(item)
                        
                        logger.info(f"ab.onliner.by: После фильтрации по ссылкам из data-id: {len(listings)} элементов")
                    
                    # Если все еще не нашли, пробуем найти через структуру страницы
                    if not listings:
                        # Ищем контейнеры с объявлениями
                        containers = soup.find_all(['div', 'section', 'article'], class_=re.compile(r'list|grid|items|cards|vehicles', re.I))
                        for container in containers:
                            items = container.find_all(['div', 'article', 'li'], recursive=False)
                            # Фильтруем элементы с ссылками на объявления
                            for item in items:
                                link = item.find('a', href=re.compile(r'/car/|/vehicle/|/auto/|\d+'))
                                if link:
                                    href = link.get('href', '')
                                    if href and not re.match(r'^https?://(www\.)?onliner\.by/?$', href):
                                        if re.search(r'/\d+', href):
                                            if item not in listings:
                                                listings.append(item)
                            if listings:
                                break
                    
                    # Парсим найденные объявления
                    if listings:
                        parsed_count = 0
                        filtered_count = 0
                        for listing in listings[:50]:  # Ограничиваем 50 объявлениями
                            car_data = self._parse_html_ad(listing)
                            if car_data:
                                parsed_count += 1
                                if self.matches_filters(car_data, filters):
                                    results.append(car_data)
                                else:
                                    filtered_count += 1
                        
                        logger.info(f"ab.onliner.by: Распарсено {parsed_count} из {len(listings)}, отфильтровано {filtered_count}, осталось {len(results)}")
                    
                    # Если успешно получили данные, выходим из цикла retry
                    break
                    
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)
                        logger.warning(f"onliner.by: Rate limit (429), жду {wait_time} секунд...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"onliner.by: Превышен лимит запросов")
                        break
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"onliner.by: HTTP {response.status_code}, повтор...")
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    else:
                        logger.error(f"onliner.by: HTTP {response.status_code}")
                        break
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"onliner.by: Ошибка (попытка {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
                else:
                    logger.error(f"Ошибка при парсинге ab.onliner.by: {e}", exc_info=True)
        
        return results
    
    def _parse_ad(self, ad: Dict) -> Dict:
        """Парсинг одного объявления"""
        try:
            ad_id = str(ad.get('id', ''))
            
            # Название - может быть в разных полях
            title = (ad.get('title') or 
                    ad.get('publicTitle') or 
                    ad.get('name') or 
                    '')
            
            # Извлекаем марку и модель из properties (как в av.by) или напрямую
            properties = ad.get('properties', [])
            brand, model = self.extract_brand_model_from_properties(properties, ad)
            
            # Если название пустое, формируем из марки и модели
            if not title and (brand or model):
                title = f"{brand} {model}".strip()
            
            # Цена - может быть в разных форматах
            price_usd = None
            price_byn = None
            price_info = ad.get('price', {})
            if price_info:
                if isinstance(price_info, dict):
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
                else:
                    # Прямые поля
                    price_usd = ad.get('price_usd')
                    price_byn = ad.get('price_byn')
            
            # Характеристики
            year = ad.get('year')
            
            # Пробег
            mileage = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'mileage':
                    mileage_value = prop.get('value')
                    if isinstance(mileage_value, (int, float)):
                        # Используем parse_mileage для валидации
                        mileage = self.parse_mileage(str(mileage_value))
                    elif isinstance(mileage_value, str):
                        # Используем parse_mileage для валидации
                        mileage = self.parse_mileage(mileage_value)
                    if mileage:
                        break
            if mileage is None:
                mileage_raw = ad.get('mileage') or ad.get('odometer')
                if mileage_raw:
                    if isinstance(mileage_raw, (int, float)):
                        # Используем parse_mileage для валидации
                        mileage = self.parse_mileage(str(mileage_raw))
                    elif isinstance(mileage_raw, str):
                        # Используем parse_mileage для валидации
                        mileage = self.parse_mileage(mileage_raw)
            
            # Объем двигателя
            engine_volume = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'engine_capacity':
                    volume_str = str(prop.get('value', '')).replace(',', '.')
                    try:
                        engine_volume = float(volume_str)
                    except:
                        pass
                    break
            if engine_volume is None:
                engine_volume = ad.get('engine_volume') or ad.get('engineDisplacement')
            
            city = ad.get('city') or ad.get('locationName', '')
            
            # Фото
            image_url = None
            photos = ad.get('photos', [])
            if photos and len(photos) > 0:
                first_photo = photos[0]
                if isinstance(first_photo, dict):
                    image_url = first_photo.get('medium', {}).get('url') or first_photo.get('url')
                elif isinstance(first_photo, str):
                    image_url = first_photo
            
            # Коробка передач
            transmission = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'transmission_type':
                    trans = str(prop.get('value', ''))
                    trans_lower = trans.lower()
                    if 'вариатор' in trans_lower or 'cvt' in trans_lower:
                        transmission = 'Вариатор'
                    elif 'автомат' in trans_lower or 'automatic' in trans_lower:
                        transmission = 'Автомат'
                    elif 'механика' in trans_lower or 'manual' in trans_lower:
                        transmission = 'Механика'
                    break
            
            if not transmission:
                trans = ad.get('transmission')
                if trans:
                    if isinstance(trans, dict):
                        trans = trans.get('name', '') or str(trans)
                    trans_lower = str(trans).lower()
                    if 'вариатор' in trans_lower or 'cvt' in trans_lower:
                        transmission = 'Вариатор'
                    elif 'автомат' in trans_lower or 'automatic' in trans_lower:
                        transmission = 'Автомат'
                    elif 'механика' in trans_lower or 'manual' in trans_lower:
                        transmission = 'Механика'
            
            # Тип двигателя
            engine_type = None
            for prop in properties:
                if isinstance(prop, dict) and prop.get('name') == 'engine_type':
                    fuel = str(prop.get('value', ''))
                    fuel_lower = fuel.lower()
                    if 'бензин' in fuel_lower or 'petrol' in fuel_lower:
                        engine_type = 'Бензин'
                    elif 'дизель' in fuel_lower or 'diesel' in fuel_lower:
                        engine_type = 'Дизель'
                    elif 'электро' in fuel_lower or 'electric' in fuel_lower:
                        engine_type = 'Электро'
                    break
            
            if not engine_type:
                fuel = ad.get('fuel_type') or ad.get('fuelType')
                if fuel:
                    fuel_lower = str(fuel).lower()
                    if 'бензин' in fuel_lower or 'petrol' in fuel_lower:
                        engine_type = 'Бензин'
                    elif 'дизель' in fuel_lower or 'diesel' in fuel_lower:
                        engine_type = 'Дизель'
                    elif 'электро' in fuel_lower or 'electric' in fuel_lower:
                        engine_type = 'Электро'
            
            # Тип кузова - извлекаем из properties или текста
            body_type = None
            for prop in properties:
                if isinstance(prop, dict):
                    prop_name = prop.get('name', '').lower()
                    if prop_name in ['body_type', 'bodytype', 'кузов', 'body']:
                        body_type = self.extract_body_type(str(prop.get('value', '')), ad)
                        break
            
            if not body_type:
                full_text = f"{title} {ad.get('description', '')}"
                body_type = self.extract_body_type(full_text, ad)
            
            # URL - пробуем разные варианты полей
            url = ad.get('publicUrl') or ad.get('url') or ad.get('link') or ad.get('ad_url')
            if not url:
                # Формируем URL из ID
                url = f"https://ab.onliner.by/car/{ad_id}"
            elif not url.startswith('http'):
                url = f"https://ab.onliner.by{url}" if url.startswith('/') else f"https://ab.onliner.by/{url}"
            
            return {
                'source': 'ab.onliner.by',
                'ad_id': ad_id,
                'title': title,
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
            logger.error(f"Ошибка при парсинге объявления ab.onliner.by: {e}", exc_info=True)
            return None
    
    def _parse_html_ad(self, element) -> Dict:
        """Парсинг объявления из HTML элемента (основной метод для onliner)"""
        try:
            # Если элемент - это ссылка с классом vehicle-form__offers-unit, извлекаем URL напрямую
            url = ''
            if element.name == 'a' and element.get('href'):
                href = element.get('href', '')
                if href.startswith('http'):
                    url = href
                elif href.startswith('/'):
                    url = f"https://ab.onliner.by{href}"
                else:
                    url = f"https://ab.onliner.by/{href}"
            
            # Извлекаем ID из URL
            ad_id = ''
            if url:
                match = re.search(r'/(\d+)/?$', url)
                if match:
                    ad_id = match.group(1)
            
            # Если не нашли URL, пробуем найти ссылку внутри элемента
            if not url:
                link = element.find('a', href=True)
                if link:
                    href = link.get('href', '')
                    if href.startswith('http'):
                        url = href
                    elif href.startswith('/'):
                        url = f"https://ab.onliner.by{href}"
                    else:
                        url = f"https://ab.onliner.by/{href}"
                    # Извлекаем ID из URL
                    if not ad_id:
                        match = re.search(r'/(\d+)/?$', url)
                        if match:
                            ad_id = match.group(1)
            
            # Заголовок - ищем в vehicle-form__link_primary-alter или vehicle-form__title
            title = ''
            title_elem = element.find(['div', 'span', 'a'], {'class': lambda x: x and 'vehicle-form__link_primary-alter' in str(x)})
            if not title_elem:
                title_elem = element.find(['div', 'span', 'h1', 'h2', 'h3', 'h4'], {'class': lambda x: x and 'vehicle-form__title' in str(x)})
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Если не нашли, пробуем другие варианты
            if not title:
                title_selectors = [
                    (['h1', 'h2', 'h3', 'h4'], {'class': lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower())}),
                    (['a'], {'class': lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower())}),
                    (['span', 'div'], {'class': lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower())}),
                ]
                
                for tags, attrs in title_selectors:
                    if isinstance(tags, list):
                        for tag in tags:
                            title_elem = element.find(tag, attrs)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                if title and len(title) > 3:  # Минимальная длина заголовка
                                    break
                        if title and len(title) > 3:
                            break
                    else:
                        title_elem = element.find(tags, attrs)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if title and len(title) > 3:
                                break
            
            # Если не нашли заголовок, пробуем из ссылки
            if not title and link:
                title = link.get_text(strip=True)
            
            # Если все еще нет заголовка, пробуем из всего текста элемента
            if not title or len(title) < 3:
                full_text = element.get_text(separator=' ', strip=True)
                # Ищем паттерн "Brand Model Year" или "Brand Model"
                car_pattern = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d{4})?', full_text)
                if car_pattern:
                    title = car_pattern.group(0).strip()
            
            # Извлекаем марку и модель из заголовка, URL и текста элемента
            brand = ''
            model = ''
            
            # Метод 1: Пробуем извлечь из URL (более надежно)
            # Структура URL на ab.onliner.by: /brand/model/id (например: /farizon/supervan/5012250)
            if url:
                url_parts = [p for p in url.split('/') if p and p not in ['car', 'vehicle', 'auto', 'https:', 'http:', 'ab.onliner.by', 'www.onliner.by', 'onliner.by', '']]
                # Структура: /brand/model/id (например: /farizon/supervan/5012250)
                if len(url_parts) >= 1:
                    # Первая часть - обычно brand
                    potential_brand = url_parts[0].replace('-', ' ').title()
                    # Заменяем некоторые известные бренды
                    brand_replacements = {
                        'Mercedes': 'Mercedes-Benz',
                        'Mercedes Benz': 'Mercedes-Benz',
                    }
                    if potential_brand in brand_replacements:
                        potential_brand = brand_replacements[potential_brand]
                    
                    if not potential_brand.isdigit() and len(potential_brand) > 1:
                        brand = potential_brand
                    
                    # Вторая часть - обычно model
                    if len(url_parts) >= 2:
                        potential_model = url_parts[1].replace('-', ' ').title()
                        # Пропускаем части, которые являются ID (только цифры)
                        if not potential_model.isdigit() and len(potential_model) > 1:
                            model = potential_model
            
            # Метод 2: Пробуем извлечь из всего текста элемента (ищем паттерны)
            if not brand or not model:
                full_text = element.get_text(separator=' ', strip=True)
                # Паттерн: "Brand Model" или "Brand Model Year" в начале текста
                # Поддерживаем кириллицу и латиницу
                car_match = re.search(r'^([A-ZА-ЯЁ][a-zа-яё]+(?:\-[A-ZА-ЯЁ][a-zа-яё]+)?)\s+([A-ZА-ЯЁ][a-zа-яё]+(?:\s+[A-ZА-ЯЁ][a-zа-яё]+)?)', full_text)
                if car_match:
                    if not brand:
                        brand = car_match.group(1).strip()
                    if not model:
                        model = car_match.group(2).strip()
            
            # Метод 3: Пробуем из заголовка
            if title:
                # Пропускаем заголовки, которые не являются описанием автомобиля
                title_lower = title.lower()
                skip_keywords = ['главная', 'страница', 'home', 'page', 'onliner', 'автобарахолка', 'авто', 'каталог', 'catalog', 'aerogrill', 'новости', 'люди', 'кошелек']
                if any(keyword in title_lower for keyword in skip_keywords):
                    logger.debug(f"ab.onliner.by: Пропущен элемент с заголовком '{title}' (не является объявлением)")
                    return None
                
                # Пропускаем элементы, где brand или model содержат "onliner", "catalog" и т.д.
                if brand and any(skip in brand.lower() for skip in ['onliner', 'catalog', 'новости', 'люди']):
                    logger.debug(f"ab.onliner.by: Пропущен элемент с brand='{brand}' (не является объявлением)")
                    return None
                if model and any(skip in model.lower() for skip in ['onliner', 'catalog', 'aerogrill', 'новости', 'люди']):
                    logger.debug(f"ab.onliner.by: Пропущен элемент с model='{model}' (не является объявлением)")
                    return None
                
                # Если brand/model не извлечены, пробуем из заголовка
                if not brand or not model:
                    parts = title.split()
                    if len(parts) >= 2:
                        if not brand:
                            # Первое слово - обычно марка
                            brand = parts[0]
                        if not model:
                            # Берем следующие слова для модели, останавливаемся на годах
                            model_parts = []
                            for i in range(1, min(5, len(parts))):
                                word = parts[i]
                                if word.isdigit() and len(word) == 4:
                                    break
                                # Пропускаем короткие слова и служебные
                                if len(word) > 2 and word.lower() not in ['и', 'и', 'с', 'в', 'на', 'для']:
                                    model_parts.append(word)
                            model = ' '.join(model_parts) if model_parts else parts[1] if len(parts) > 1 else ''
            
            # Метод 4: Пробуем найти в data-атрибутах или специальных классах
            if not brand or not model:
                # Ищем элементы с классами, содержащими brand/model
                brand_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and 'brand' in str(x).lower())
                model_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and 'model' in str(x).lower())
                
                if brand_elem and not brand:
                    brand = brand_elem.get_text(strip=True)
                if model_elem and not model:
                    model = model_elem.get_text(strip=True)
            
            # Цена - ищем в vehicle-form__offers-part_price
            price_usd = None
            price_byn = None
            price_part = element.find(['div'], {'class': lambda x: x and 'vehicle-form__offers-part_price' in str(x)})
            if price_part:
                # Ищем кнопку с ценой
                price_button = price_part.find(['div', 'button'], {'class': lambda x: x and 'vehicle-form__button_price' in str(x)})
                if price_button:
                    price_text = price_button.get_text(strip=True)
                    # Извлекаем цену в BYN (например: "95 857 р.")
                    byn_match = re.search(r'([\d\s\xa0]+)\s*р\.', price_text)
                    if byn_match:
                        try:
                            price_byn = float(byn_match.group(1).replace(' ', '').replace('\xa0', ''))
                        except:
                            pass
                
                # Ищем цену в USD/EUR (обычно в описании под кнопкой)
                price_desc = price_part.find(['div'], {'class': lambda x: x and 'vehicle-form__description' in str(x)})
                if price_desc:
                    price_text = price_desc.get_text(strip=True)
                    # Извлекаем цену в USD (например: "32 900 $ / 28 235 €")
                    usd_match = re.search(r'([\d\s\xa0]+)\s*\$', price_text)
                    if usd_match:
                        try:
                            price_usd = float(usd_match.group(1).replace(' ', '').replace('\xa0', ''))
                        except:
                            pass
            
            # Если не нашли, пробуем другие селекторы
            if not price_usd and not price_byn:
                price_selectors = [
                    ('div', {'class': lambda x: x and 'jest-price-other' in str(x)}),
                    ('div', {'class': lambda x: x and 'jest-price-byn' in str(x)}),
                    ('div', {'class': lambda x: x and 'vehicle-form__price' in str(x)}),
                    ('span', {'class': lambda x: x and 'price' in str(x).lower()}),
                ]
                for tag, attrs in price_selectors:
                    price_elem = element.find(tag, attrs)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        usd_match = re.search(r'\$[\s]*([\d\s\xa0]+)', price_text)
                        byn_match = re.search(r'([\d\s\xa0]+)\s*р\.', price_text)
                        if usd_match:
                            try:
                                price_usd = float(usd_match.group(1).replace(' ', '').replace('\xa0', ''))
                            except:
                                pass
                        if byn_match:
                            try:
                                price_byn = float(byn_match.group(1).replace(' ', '').replace('\xa0', ''))
                            except:
                                pass
                        if price_usd or price_byn:
                            break
            
            # Конвертация валют, если одна из цен отсутствует
            price_usd, price_byn = self.normalize_prices(price_usd, price_byn, validate=False)
            
            # Год - ищем в vehicle-form__offers-part_year
            year = None
            year_part = element.find(['div'], {'class': lambda x: x and 'vehicle-form__offers-part_year' in str(x)})
            if year_part:
                year_elem = year_part.find(['div', 'span'], {'class': lambda x: x and 'vehicle-form__description' in str(x)})
                if year_elem:
                    year_text = year_elem.get_text(strip=True)
                    try:
                        year = int(year_text)
                    except:
                        pass
            
            # Если не нашли, пробуем другие селекторы
            if not year:
                year_elem = element.find(['div', 'span'], {'class': lambda x: x and 'jest-year' in str(x)})
                if year_elem:
                    year_text = year_elem.get_text(strip=True)
                    try:
                        year = int(year_text)
                    except:
                        pass
            
            if not year:
                full_text = element.get_text(separator=' ', strip=True)
                year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
                if year_match:
                    try:
                        year = int(year_match.group(0))
                    except:
                        pass
            
            # Пробег - ищем в vehicle-form__offers-part_mileage
            mileage = None
            mileage_part = element.find(['div'], {'class': lambda x: x and 'vehicle-form__offers-part_mileage' in str(x)})
            if mileage_part:
                mileage_elem = mileage_part.find(['div', 'span'], {'class': lambda x: x and 'vehicle-form__description' in str(x)})
                if mileage_elem:
                    mileage_text = mileage_elem.get_text(strip=True)
                    if mileage_text.lower() not in ['новый', 'new']:
                        # Используем parse_mileage для валидации
                        mileage = self.parse_mileage(mileage_text)
            
            # Город - ищем в vehicle-form__offers-part_city
            city = ''
            city_part = element.find(['div'], {'class': lambda x: x and 'vehicle-form__offers-part_city' in str(x)})
            if city_part:
                city_elem = city_part.find(['div', 'span'], {'class': lambda x: x and 'vehicle-form__description' in str(x)})
                if city_elem:
                    city = city_elem.get_text(strip=True)
            
            # Двигатель - ищем в vehicle-form__description_engine
            engine_type = None
            engine_elem = element.find(['div', 'span'], {'class': lambda x: x and 'vehicle-form__description_engine' in str(x)})
            if engine_elem:
                engine_text = engine_elem.get_text(strip=True).lower()
                if 'бензин' in engine_text or 'petrol' in engine_text or 'gasoline' in engine_text:
                    engine_type = 'Бензин'
                elif 'дизель' in engine_text or 'diesel' in engine_text:
                    engine_type = 'Дизель'
                elif 'электро' in engine_text or 'electric' in engine_text:
                    engine_type = 'Электро'
            
            # Объем двигателя - извлекаем из текста двигателя (например: "2 л / Дизель")
            engine_volume = None
            if engine_elem:
                engine_text = engine_elem.get_text(strip=True)
                volume_match = re.search(r'([\d.]+)\s*л', engine_text)
                if volume_match:
                    try:
                        engine_volume = float(volume_match.group(1))
                    except:
                        pass
            
            # Коробка передач - ищем в vehicle-form__description_transmission
            transmission = None
            trans_elem = element.find(['div', 'span'], {'class': lambda x: x and 'vehicle-form__description_transmission' in str(x)})
            if trans_elem:
                trans_text = trans_elem.get_text(strip=True).lower()
                if 'вариатор' in trans_text or 'cvt' in trans_text:
                    transmission = 'Вариатор'
                elif 'автомат' in trans_text or 'automatic' in trans_text:
                    transmission = 'Автомат'
                elif 'механика' in trans_text or 'manual' in trans_text:
                    transmission = 'Механика'
            
            # Тип кузова - извлекаем из текста элемента
            body_type = None
            full_text = element.get_text(separator=' ', strip=True)
            body_type = self.extract_body_type(full_text)
            
            # Фото
            img = element.find('img', src=True)
            image_url = None
            if img:
                image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if image_url and not image_url.startswith('http'):
                    image_url = f"https://ab.onliner.by{image_url}" if image_url.startswith('/') else f"https://ab.onliner.by/{image_url}"
            
            if not ad_id:
                # Генерируем ID из заголовка если нет
                ad_id = str(hash(title[:50])) if title else str(hash(str(element)[:100]))
            
            # Улучшаем title: если он короткий или неполный, формируем из brand + model + год
            if title and len(title) < 10:
                # Если title слишком короткий, формируем более информативный
                title_parts = []
                if brand:
                    title_parts.append(brand)
                if model:
                    title_parts.append(model)
                if year:
                    title_parts.append(str(year))
                if title_parts:
                    title = ' '.join(title_parts)
            elif not title and (brand or model):
                # Если title пустой, формируем из brand + model
                title_parts = []
                if brand:
                    title_parts.append(brand)
                if model:
                    title_parts.append(model)
                if title_parts:
                    title = ' '.join(title_parts)
            
            if not title:
                return None
            
            # Дополнительная проверка - если brand и model пустые, это не объявление
            if not brand and not model:
                return None
            
            # Финальная проверка - пропускаем элементы с некорректными brand/model
            if brand and (len(brand) < 2 or brand.lower() in ['catalog', 'onliner', 'новости', 'люди', 'кошелек'] or 'catalog' in brand.lower() or 'onliner' in brand.lower()):
                return None
            if model and (len(model) < 2 or model.lower() in ['aerogrill', 'catalog', 'onliner'] or 'aerogrill' in model.lower() or 'catalog' in model.lower()):
                return None
            
            return {
                'source': 'ab.onliner.by',
                'ad_id': str(ad_id),
                'title': title,
                'brand': brand,
                'model': model,
                'price_usd': price_usd,
                'price_byn': price_byn,
                'year': year,
                'mileage': mileage,
                'engine_volume': engine_volume,
                'city': city,
                'url': url or f"https://ab.onliner.by/car/{ad_id}",
                'image_url': image_url,
                'transmission': transmission,
                'engine_type': engine_type,
                'body_type': body_type,
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге HTML объявления ab.onliner.by: {e}", exc_info=True)
            return None
