"""
Парсер для abw.by
Переписан с нуля для упрощения и улучшения надежности
"""
# Стандартная библиотека
import asyncio
import logging
import re
from typing import List, Dict, Optional

# Сторонние библиотеки
import cloudscraper
from bs4 import BeautifulSoup

# Локальные импорты
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class AbwParser(BaseParser):
    """Парсер объявлений с abw.by"""
    
    BASE_URL = "https://abw.by/cars"
    MAX_ADS = 50
    
    # Список городов Беларуси для извлечения
    CITIES = [
        'Минск', 'Гомель', 'Могилев', 'Витебск', 'Гродно', 'Брест',
        'Бобруйск', 'Барановичи', 'Борисов', 'Пинск', 'Орша', 'Мозырь',
        'Солигорск', 'Новополоцк', 'Лида', 'Молодечно', 'Полоцк', 'Жлобин',
        'Светлогорск', 'Речица', 'Слуцк', 'Кобрин', 'Волковыск', 'Калинковичи',
        'Сморгонь', 'Рогачев', 'Осиповичи', 'Жодино', 'Слоним', 'Кричев'
    ]
    
    def __init__(self):
        super().__init__()
        self.scraper = cloudscraper.create_scraper()
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на abw.by"""
        results = []
        
        try:
            url = self.BASE_URL
            logger.info(f"abw.by: Используется базовый URL: {url} (фильтры: brand={filters.get('brand')}, model={filters.get('model')}, price_to={filters.get('price_to_usd')})")
            
            await asyncio.sleep(0.5)
            
            response = await self._fetch_page(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                logger.info(f"abw.by: Получен HTML, размер: {len(response.text)} символов")
                
                ads = self._extract_ad_elements(soup)
                logger.info(f"abw.by: Найдено объявлений: {len(ads)}")
                
                results = self._parse_and_filter(ads, filters)
            else:
                logger.warning(f"abw.by: HTTP {response.status_code} для URL: {url}")
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге abw.by: {e}", exc_info=True)
        
        logger.info(f"abw.by: Завершено, найдено {len(results)} объявлений")
        return results
    
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
                    'Referer': 'https://abw.by/',
                }
            )
        )
    
    def _extract_ad_elements(self, soup: BeautifulSoup) -> List:
        """Извлечение элементов объявлений из HTML"""
        ads = []
        
        # Метод 1: Ищем через ссылки на детальные страницы
        detail_links = soup.find_all('a', href=lambda x: x and '/cars/detail/' in str(x))
        for link in detail_links:
            parent = link.find_parent('div', class_=lambda x: x and ('card__wrapper' in str(x) or ('card' in str(x) and 'card__' not in str(x))))
            if parent and parent not in ads:
                ads.append(parent)
        
        # Метод 2: Если не нашли, пробуем через card__wrapper
        if not ads:
            ads = soup.find_all('div', class_='card__wrapper')
        
        # Метод 3: Если все еще не нашли, ищем через card__info
        if not ads:
            card_infos = soup.find_all('div', class_='card__info')
            for info in card_infos:
                parent = info.find_parent('div', class_=lambda x: x and 'card' in str(x))
                if parent and parent not in ads:
                    ads.append(parent)
        
        return ads[:self.MAX_ADS]
    
    def _parse_and_filter(self, ads: List, filters: Dict) -> List[Dict]:
        """Парсинг и фильтрация объявлений"""
        results = []
        parsed_count = 0
        filtered_count = 0
        first_filtered = None
        
        for ad in ads:
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
            logger.info(f"abw.by: Пример отфильтрованного: brand='{first_filtered.get('brand')}', model='{first_filtered.get('model')}', filter_brand='{filters.get('brand')}', filter_model='{filters.get('model')}', year={first_filtered.get('year')}, filter_year_from={filters.get('year_from')}, price_usd={first_filtered.get('price_usd')}, filter_price_to={filters.get('price_to_usd')}")
        
        logger.info(f"abw.by: Распарсено {parsed_count} из {len(ads)}, отфильтровано {filtered_count}, осталось {len(results)}")
        return results
    
    def _parse_ad(self, ad_element) -> Optional[Dict]:
        """Парсинг одного объявления"""
        try:
            full_text = ad_element.get_text(separator=' ', strip=True)
            
            # URL и ID
            url, ad_id = self._extract_url_and_id(ad_element)
            
            # Заголовок
            title = self._extract_title(ad_element, full_text)
            
            # Марка и модель
            brand, model = self._extract_brand_model(ad_element, url, title, full_text)
            
            # Цены
            price_usd, price_byn = self._extract_prices(ad_element, full_text)
            
            # Год
            year = self._extract_year(full_text)
            
            # Пробег
            mileage = self._extract_mileage(full_text)
            
            # Объем двигателя
            engine_volume = self._extract_engine_volume(full_text)
            
            # Коробка передач
            transmission = self._extract_transmission(full_text)
            
            # Тип двигателя
            engine_type = self._extract_engine_type(full_text)
            
            # Тип кузова
            body_type = self.extract_body_type(full_text)
            
            # Фото
            image_url = self._extract_image(ad_element)
            
            # Город
            city = self._extract_city(full_text)
            
            # Улучшаем title
            if not title or len(title) < 10:
                title_parts = []
                if brand:
                    title_parts.append(brand)
                if model:
                    title_parts.append(model)
                if year:
                    title_parts.append(str(year))
                if title_parts:
                    title = ' '.join(title_parts)
            
            return {
                'source': 'abw.by',
                'ad_id': ad_id or str(hash(full_text[:50])),
                'title': title or full_text[:100],
                'brand': brand,
                'model': model,
                'price_usd': price_usd,
                'price_byn': price_byn,
                'year': year,
                'mileage': mileage,
                'engine_volume': engine_volume,
                'city': city,
                'url': url or 'https://abw.by/cars',
                'image_url': image_url,
                'transmission': transmission,
                'engine_type': engine_type,
                'body_type': body_type,
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге объявления abw.by: {e}", exc_info=True)
            return None
    
    def _extract_url_and_id(self, ad_element) -> tuple:
        """Извлечение URL и ID объявления"""
        url = ''
        ad_id = ''
        
        link_elem = ad_element.find('a', href=lambda x: x and '/cars/detail/' in str(x))
        if not link_elem:
            link_elem = ad_element.find('a', href=True)
        
        if link_elem:
            href = link_elem.get('href', '')
            if href:
                if '/cars/detail/' in href:
                    parts = [p for p in href.split('/') if p]
                    if parts:
                        last_part = parts[-1]
                        if last_part.isdigit():
                            ad_id = last_part
                        elif len(parts) > 1 and parts[-2].isdigit():
                            ad_id = parts[-2]
                
                url = href
                if not url.startswith('http'):
                    url = f"https://abw.by{url}" if url.startswith('/') else f"https://abw.by/{url}"
        
        return url, ad_id
    
    def _extract_title(self, ad_element, full_text: str) -> str:
        """Извлечение заголовка"""
        # Пробуем из card__info (самый надежный источник)
        info_elem = ad_element.find('div', class_='card__info')
        if info_elem:
            info_text = info_elem.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in info_text.split('\n') if line.strip()]
            if lines:
                # Берем первую строку, которая обычно содержит марку и модель
                title = lines[0]
                # Очищаем от лишних символов
                title = re.sub(r'\s+', ' ', title).strip()
                if len(title) > 3:
                    return title
        
        # Пробуем из ссылки
        link_elem = ad_element.find('a', href=lambda x: x and '/cars/detail/' in str(x))
        if not link_elem:
            link_elem = ad_element.find('a', href=True)
        if link_elem:
            link_text = link_elem.get_text(strip=True)
            if link_text and len(link_text) > 3:
                return link_text
        
        # Пробуем из текста (первые слова)
        match = re.match(r'^([A-Za-zА-Яа-яЁё\s]+?)(?:\s+[I\d]|,|\d)', full_text)
        if match:
            return match.group(1).strip()
        
        # Берем первые слова
        words = full_text.split()[:3]
        return ' '.join(words) if words else ''
    
    def _extract_brand_model(self, ad_element, url: str, title: str, full_text: str) -> tuple:
        """Извлечение марки и модели"""
        brand = ''
        model = ''
        
        # Метод 1: Из URL
        if url and '/cars/detail/' in url:
            try:
                url_parts = url.split('/cars/detail/')[1].split('/')
                if len(url_parts) >= 2:
                    brand = url_parts[0].capitalize()
                    model = url_parts[1].capitalize()
            except:
                pass
        
        # Метод 2: Из заголовка
        if not brand or not model:
            if title:
                parts = title.split()
                if len(parts) >= 2:
                    brand = parts[0]
                    model_parts = []
                    for i in range(1, min(4, len(parts))):
                        word = parts[i]
                        if word.isdigit() and len(word) == 4:
                            break
                        model_parts.append(word)
                    model = ' '.join(model_parts) if model_parts else parts[1] if len(parts) > 1 else ''
        
        # Метод 3: Из текста (известные марки) - только если не нашли в URL и заголовке
        # Этот метод менее надежен, поэтому используем его только как последний вариант
        # И ТОЛЬКО если title не пустой и содержит известную марку
        if (not brand or not model) and title:
            # Ищем марку только в заголовке, не в полном тексте
            search_text = title
            known_brands = ['BMW', 'Mercedes', 'Audi', 'Toyota', 'Nissan', 'Volkswagen',
                          'Hyundai', 'Kia', 'Renault', 'Skoda', 'Ford', 'Mazda', 'Honda',
                          'Lexus', 'Volvo', 'LADA', 'BelGee', 'Geely', 'Chery', 'Haval',
                          'Opel', 'Peugeot', 'Fiat', 'Subaru', 'Mitsubishi', 'Suzuki',
                          'Citroen', 'Chevrolet', 'Tesla']
            for known_brand in known_brands:
                # Ищем марку в начале заголовка (первые 50 символов)
                brand_lower = known_brand.lower()
                search_lower = search_text.lower()
                brand_pos = search_lower.find(brand_lower)
                # Проверяем, что марка найдена в начале заголовка (первые 50 символов)
                if brand_pos >= 0 and brand_pos < 50:
                    brand = known_brand
                    after_brand = search_text[brand_pos + len(known_brand):].strip()
                    model_parts = []
                    for word in after_brand.split()[:4]:
                        if word.isdigit() and len(word) == 4:
                            break
                        # Пропускаем служебные слова
                        if word.lower() not in ['и', 'с', 'в', 'на', 'для', 'от', 'от']:
                            model_parts.append(word)
                    model = ' '.join(model_parts) if model_parts else ''
                    break
        
        return brand, model
    
    def _extract_prices(self, ad_element, full_text: str) -> tuple:
        """Извлечение цен"""
        price_usd = None
        price_byn = None
        
        # Пробуем найти элемент с ценой
        price_elem = (ad_element.find('div', class_=lambda x: x and 'price' in str(x).lower()) or
                     ad_element.find('span', class_=lambda x: x and 'price' in str(x).lower()) or
                     ad_element.find('div', class_='card__price'))
        
        price_text = price_elem.get_text(strip=True) if price_elem else full_text
        
        # Ищем паттерны цены
        price_patterns = [
            r'(\d[\d\s]+)\s*р\.\s*(\d[\d\s]+)\s*\$',
            r'(\d[\d\s]+)\s*\$\s*(\d[\d\s]+)\s*р\.',
        ]
        
        price_match = None
        for pattern in price_patterns:
            price_match = re.search(pattern, price_text)
            if price_match:
                break
        
        if price_match:
            group1 = price_match.group(1).replace(' ', '').replace('\xa0', '')
            group2 = price_match.group(2).replace(' ', '').replace('\xa0', '')
            match_text = price_match.group(0)
            
            if '$' in match_text and 'р.' in match_text:
                if match_text.index('$') < match_text.index('р.'):
                    try:
                        price_usd = float(group1)
                        price_byn = float(group2)
                    except:
                        pass
                else:
                    try:
                        price_byn = float(group1)
                        price_usd = float(group2)
                    except:
                        pass
        else:
            # Пробуем найти отдельно
            usd_match = re.search(r'(\d[\d\s\xa0]+)\s*\$', price_text)
            if usd_match:
                try:
                    price_usd = float(usd_match.group(1).replace(' ', '').replace('\xa0', ''))
                except:
                    pass
            
            byn_match = re.search(r'(\d[\d\s\xa0]+)\s*р\.', price_text)
            if byn_match:
                try:
                    price_byn = float(byn_match.group(1).replace(' ', '').replace('\xa0', ''))
                except:
                    pass
        
        price_usd, price_byn = self.normalize_prices(price_usd, price_byn, validate=False)
        return price_usd, price_byn
    
    def _extract_year(self, full_text: str) -> Optional[int]:
        """Извлечение года"""
        year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
        if year_match:
            try:
                return int(year_match.group(0))
            except:
                pass
        return None
    
    def _extract_mileage(self, full_text: str) -> Optional[int]:
        """Извлечение пробега"""
        mileage_matches = re.finditer(r'(?<![\d+])([1-9]\d{0,2}(?:\s+\d{3})*)\s*км', full_text)
        for match in mileage_matches:
            mileage_str = match.group(1)
            mileage_cleaned = mileage_str.replace(' ', '').replace('\xa0', '')
            
            # Проверяем, не является ли это годом
            if len(mileage_cleaned) == 4:
                try:
                    year_candidate = int(mileage_cleaned)
                    if 1900 <= year_candidate <= 2100:
                        continue
                except:
                    pass
            
            # Проверяем, не является ли это номером телефона
            if mileage_cleaned.startswith('0') or mileage_cleaned.startswith('375'):
                continue
            
            # Проверяем длину
            if len(mileage_cleaned) > 6:
                continue
            
            mileage = self.parse_mileage(mileage_str)
            if mileage:
                return mileage
        
        return None
    
    def _extract_engine_volume(self, full_text: str) -> Optional[float]:
        """Извлечение объема двигателя"""
        volume_match = re.search(r'(\d+[.,]?\d*)\s*л', full_text)
        if volume_match:
            try:
                return float(volume_match.group(1).replace(',', '.'))
            except:
                pass
        return None
    
    def _extract_transmission(self, full_text: str) -> Optional[str]:
        """Извлечение коробки передач"""
        full_text_lower = full_text.lower()
        if any(x in full_text_lower for x in ['вариатор', 'cvt']):
            return 'Вариатор'
        elif any(x in full_text_lower for x in ['автомат', 'автоматическая']):
            return 'Автомат'
        elif any(x in full_text_lower for x in ['механика', 'мех', 'механическая']):
            return 'Механика'
        return None
    
    def _extract_engine_type(self, full_text: str) -> Optional[str]:
        """Извлечение типа двигателя"""
        full_text_lower = full_text.lower()
        if 'дизель' in full_text_lower:
            return 'Дизель'
        elif 'бензин' in full_text_lower:
            return 'Бензин'
        elif any(x in full_text_lower for x in ['электро', 'электр']):
            return 'Электро'
        return None
    
    def _extract_image(self, ad_element) -> Optional[str]:
        """Извлечение URL изображения"""
        img_elem = ad_element.find('img')
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
            if image_url:
                if not image_url.startswith('http'):
                    image_url = f"https://abw.by{image_url}" if image_url.startswith('/') else f"https://abw.by/{image_url}"
                return image_url
        return None
    
    def _extract_city(self, text: str) -> str:
        """Извлечение города из текста"""
        text_lower = text.lower()
        for city in self.CITIES:
            if city.lower() in text_lower:
                return city
        return ''
