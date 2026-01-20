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
    
    def _build_url(self, filters: Dict) -> str:
        """Формирование URL с фильтрами"""
        url = self.BASE_URL
        params = []
        
        # abw.by использует параметры в URL для фильтрации
        if filters.get('brand'):
            brand_slug = filters['brand'].lower().replace(' ', '-').replace('mercedes-benz', 'mercedes')
            params.append(f"brand={brand_slug}")
        
        if filters.get('model'):
            model_slug = filters['model'].lower().replace(' ', '-').replace('x-trail', 'x_trail')
            params.append(f"model={model_slug}")
        
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
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на abw.by"""
        results = []
        
        try:
            url = self._build_url(filters)
            logger.info(f"abw.by: Используется URL: {url} (фильтры: brand={filters.get('brand')}, model={filters.get('model')}, price_to={filters.get('price_to_usd')})")
            
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
        seen_urls = set()  # Для отслеживания уникальности объявлений
        
        # Метод 1: Ищем через ссылки на детальные страницы (самый надежный)
        detail_links = soup.find_all('a', href=lambda x: x and '/cars/detail/' in str(x))
        for link in detail_links:
            href = link.get('href', '')
            # Нормализуем URL для проверки уникальности
            if href:
                href_normalized = href.split('?')[0]  # Убираем параметры запроса
                if href_normalized in seen_urls:
                    continue  # Пропускаем дубликаты
                seen_urls.add(href_normalized)
            
            # Ищем родительский элемент с классом card__wrapper или card
            parent = link.find_parent('div', class_=lambda x: x and ('card__wrapper' in str(x) or ('card' in str(x) and 'card__' not in str(x))))
            if parent and parent not in ads:
                ads.append(parent)
        
        # Метод 2: Если не нашли достаточно объявлений, пробуем через card__wrapper
        if len(ads) < 10:
            card_wrappers = soup.find_all('div', class_='card__wrapper')
            for wrapper in card_wrappers:
                # Проверяем, что внутри есть ссылка на объявление
                link = wrapper.find('a', href=lambda x: x and '/cars/detail/' in str(x))
                if link and wrapper not in ads:
                    href = link.get('href', '')
                    if href:
                        href_normalized = href.split('?')[0]
                        if href_normalized not in seen_urls:
                            seen_urls.add(href_normalized)
                            ads.append(wrapper)
        
        logger.info(f"abw.by: Найдено уникальных объявлений: {len(ads)}")
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
            # СНАЧАЛА извлекаем URL - это ключевой элемент для идентификации
            url, ad_id = self._extract_url_and_id(ad_element)
            
            # Если нет URL с /cars/detail/, это может быть не объявление - пропускаем
            if not url or '/cars/detail/' not in url:
                logger.debug(f"abw.by: Пропущен элемент без /cars/detail/ URL: url={url}")
                return None
            
            # Логируем URL для отладки (INFO, так как DEBUG может быть отключен)
            logger.info(f"abw.by: Обработка объявления: url={url[:100]}, ad_id={ad_id}")
            
            # Извлекаем текст из всего элемента для поиска данных
            # Берем текст из card__info, card__params, card__specs и других элементов
            full_text_parts = []
            
            # Основной текст из card__info
            title_elem = ad_element.find('div', class_='card__info')
            if title_elem:
                full_text_parts.append(title_elem.get_text(separator=' ', strip=True))
            
            # Параметры из card__params или card__specs
            params_elem = (ad_element.find('div', class_='card__params') or 
                          ad_element.find('div', class_='card__specs') or
                          ad_element.find('div', class_='card__characteristics'))
            if params_elem:
                full_text_parts.append(params_elem.get_text(separator=' ', strip=True))
            
            # Если нет структурированных элементов, берем весь текст
            if not full_text_parts:
                link_elem = ad_element.find('a', href=lambda x: x and '/cars/detail/' in str(x))
                if link_elem:
                    full_text_parts.append(link_elem.get_text(separator=' ', strip=True))
                else:
                    full_text_parts.append(ad_element.get_text(separator=' ', strip=True))
            
            full_text = ' '.join(full_text_parts)
            
            # Заголовок
            title = self._extract_title(ad_element, full_text)
            
            # Марка и модель - ПРИОРИТЕТ URL
            # Если URL не содержит /cars/detail/, не пытаемся извлекать марку/модель
            brand, model = self._extract_brand_model(ad_element, url, title, full_text)
            
            # Если после извлечения марка все еще не найдена из URL - это проблема
            # Не используем заголовок/текст, так как они могут содержать рекламу
            if not brand or not model:
                logger.warning(f"abw.by: Марка/модель не найдены для URL: {url[:100]}")
            
            # Цены
            price_usd, price_byn = self._extract_prices(ad_element, full_text)
            
            # Год - ищем в HTML элементах и тексте
            year = self._extract_year(ad_element, full_text)
            
            # Пробег - ищем в HTML элементах и тексте
            mileage = self._extract_mileage(ad_element, full_text)
            
            # Объем двигателя - ищем в HTML элементах и тексте
            engine_volume = self._extract_engine_volume(ad_element, full_text)
            
            # Коробка передач - ищем в HTML элементах и тексте
            transmission = self._extract_transmission(ad_element, full_text)
            
            # Тип двигателя - ищем в HTML элементах и тексте
            engine_type = self._extract_engine_type(ad_element, full_text)
            
            # Тип кузова - ищем в HTML элементах и тексте
            body_type = self._extract_body_type_from_element(ad_element, full_text)
            
            # Фото
            image_url = self._extract_image(ad_element)
            
            # Город - ищем в HTML элементах и тексте
            city = self._extract_city(ad_element, full_text)
            
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
        
        # Ищем ссылку с /cars/detail/ - это ключевой признак объявления
        link_elem = ad_element.find('a', href=lambda x: x and '/cars/detail/' in str(x))
        if not link_elem:
            # Пробуем любую ссылку в элементе
            link_elem = ad_element.find('a', href=True)
        
        if link_elem:
            href = link_elem.get('href', '')
            if href:
                if '/cars/detail/' in href:
                    parts = [p for p in href.split('/') if p]
                    if parts:
                        # Последняя часть - обычно ID
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
        """Извлечение марки и модели - ПРИОРИТЕТ URL"""
        brand = ''
        model = ''
        
        # Метод 1: Из URL (самый надежный способ для abw.by)
        if url and '/cars/detail/' in url:
            try:
                url_parts = url.split('/cars/detail/')[1].split('/')
                # Структура: /cars/detail/brand/model/id или /cars/detail/brand/model/
                if len(url_parts) >= 2:
                    brand_raw = url_parts[0]
                    model_raw = url_parts[1]
                    
                    # Проверяем, что это не ID (только цифры)
                    if not brand_raw.isdigit() and not model_raw.isdigit():
                        brand = brand_raw.capitalize()
                        model = model_raw.capitalize()
                        # Заменяем дефисы на пробелы и делаем правильную капитализацию
                        brand = brand.replace('-', ' ').title()
                        model = model.replace('-', ' ').title()
                        
                        # Специальные случаи
                        brand_replacements = {
                            'Mercedes': 'Mercedes-Benz',
                            'Mercedes Benz': 'Mercedes-Benz',
                        }
                        if brand in brand_replacements:
                            brand = brand_replacements[brand]
                        
                        logger.info(f"abw.by: Извлечено из URL: brand={brand}, model={model}, url={url[:100]}")
                    else:
                        logger.warning(f"abw.by: URL содержит цифры вместо марки/модели: url_parts={url_parts}, url={url[:100]}")
            except Exception as e:
                logger.warning(f"abw.by: Ошибка извлечения из URL: {e}, url={url[:100] if url else 'None'}")
        
        # Метод 2: Из заголовка (ТОЛЬКО если URL нет или не содержит /cars/detail/)
        # ВАЖНО: Если URL есть с /cars/detail/, но марка не извлечена - НЕ используем заголовок
        # Заголовок может содержать рекламу или неправильную информацию
        if (not brand or not model) and (not url or '/cars/detail/' not in url):
            # URL нет или не содержит /cars/detail/ - можно попробовать заголовок как последний вариант
            if title:
                # Очищаем заголовок от лишних символов
                title_clean = re.sub(r'\s+', ' ', title).strip()
                parts = title_clean.split()
                if len(parts) >= 2:
                    brand_candidate = parts[0]
                    # Проверяем, что это похоже на марку (начинается с заглавной, не цифра)
                    if brand_candidate and brand_candidate[0].isupper() and not brand_candidate.isdigit():
                        brand = brand_candidate
                        model_parts = []
                        for i in range(1, min(4, len(parts))):
                            word = parts[i]
                            if word.isdigit() and len(word) == 4:
                                break
                            # Пропускаем служебные слова
                            if word.lower() not in ['и', 'с', 'в', 'на', 'для', 'от']:
                                model_parts.append(word)
                        model = ' '.join(model_parts) if model_parts else parts[1] if len(parts) > 1 else ''
                        logger.debug(f"abw.by: Извлечено из заголовка: brand={brand}, model={model}, title={title[:50]}")
        
        # Метод 3 из текста - убран, так как ненадежен
        
        # Метод 3: Из текста (известные марки) - ОТКЛЮЧЕН
        # Этот метод ненадежен, так как может находить марки из рекламы или других объявлений на странице
        # Если URL и заголовок не дали результатов, лучше вернуть пустые значения
        # и позволить фильтрации работать по другим критериям
        
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
    
    def _extract_year(self, ad_element, full_text: str) -> Optional[int]:
        """Извлечение года из HTML элементов и текста"""
        # Сначала ищем в структурированных элементах
        year_elem = (ad_element.find('div', class_=lambda x: x and ('year' in str(x).lower() or 'год' in str(x).lower())) or
                    ad_element.find('span', class_=lambda x: x and ('year' in str(x).lower() or 'год' in str(x).lower())))
        if year_elem:
            year_text = year_elem.get_text(strip=True)
            year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
            if year_match:
                try:
                    return int(year_match.group(0))
                except:
                    pass
        
        # Если не нашли в элементах, ищем в тексте
        year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
        if year_match:
            try:
                return int(year_match.group(0))
            except:
                pass
        return None
    
    def _extract_mileage(self, ad_element, full_text: str) -> Optional[int]:
        """Извлечение пробега из HTML элементов и текста"""
        # Сначала ищем в структурированных элементах
        mileage_elem = (ad_element.find('div', class_=lambda x: x and ('mileage' in str(x).lower() or 'пробег' in str(x).lower() or 'odometer' in str(x).lower())) or
                       ad_element.find('span', class_=lambda x: x and ('mileage' in str(x).lower() or 'пробег' in str(x).lower() or 'odometer' in str(x).lower())))
        if mileage_elem:
            mileage_text = mileage_elem.get_text(strip=True)
            mileage = self.parse_mileage(mileage_text)
            if mileage:
                return mileage
        
        # Если не нашли в элементах, ищем в тексте
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
    
    def _extract_engine_volume(self, ad_element, full_text: str) -> Optional[float]:
        """Извлечение объема двигателя из HTML элементов и текста"""
        # Сначала ищем в структурированных элементах
        volume_elem = (ad_element.find('div', class_=lambda x: x and ('volume' in str(x).lower() or 'объем' in str(x).lower() or 'engine' in str(x).lower() or 'двигатель' in str(x).lower())) or
                      ad_element.find('span', class_=lambda x: x and ('volume' in str(x).lower() or 'объем' in str(x).lower() or 'engine' in str(x).lower() or 'двигатель' in str(x).lower())))
        if volume_elem:
            volume_text = volume_elem.get_text(strip=True)
            volume_match = re.search(r'(\d+[.,]?\d*)\s*л', volume_text)
            if volume_match:
                try:
                    return float(volume_match.group(1).replace(',', '.'))
                except:
                    pass
        
        # Если не нашли в элементах, ищем в тексте
        volume_match = re.search(r'(\d+[.,]?\d*)\s*л', full_text)
        if volume_match:
            try:
                return float(volume_match.group(1).replace(',', '.'))
            except:
                pass
        return None
    
    def _extract_transmission(self, ad_element, full_text: str) -> Optional[str]:
        """Извлечение коробки передач из HTML элементов и текста"""
        # Сначала ищем в структурированных элементах
        trans_elem = (ad_element.find('div', class_=lambda x: x and ('transmission' in str(x).lower() or 'коробка' in str(x).lower() or 'gearbox' in str(x).lower())) or
                     ad_element.find('span', class_=lambda x: x and ('transmission' in str(x).lower() or 'коробка' in str(x).lower() or 'gearbox' in str(x).lower())))
        if trans_elem:
            trans_text = trans_elem.get_text(strip=True).lower()
            if any(x in trans_text for x in ['вариатор', 'cvt']):
                return 'Вариатор'
            elif any(x in trans_text for x in ['автомат', 'автоматическая']):
                return 'Автомат'
            elif any(x in trans_text for x in ['механика', 'мех', 'механическая']):
                return 'Механика'
        
        # Если не нашли в элементах, ищем в тексте
        full_text_lower = full_text.lower()
        if any(x in full_text_lower for x in ['вариатор', 'cvt']):
            return 'Вариатор'
        elif any(x in full_text_lower for x in ['автомат', 'автоматическая']):
            return 'Автомат'
        elif any(x in full_text_lower for x in ['механика', 'мех', 'механическая']):
            return 'Механика'
        return None
    
    def _extract_engine_type(self, ad_element, full_text: str) -> Optional[str]:
        """Извлечение типа двигателя из HTML элементов и текста"""
        # Сначала ищем в структурированных элементах
        engine_elem = (ad_element.find('div', class_=lambda x: x and ('fuel' in str(x).lower() or 'топливо' in str(x).lower() or 'engine' in str(x).lower() or 'двигатель' in str(x).lower())) or
                      ad_element.find('span', class_=lambda x: x and ('fuel' in str(x).lower() or 'топливо' in str(x).lower() or 'engine' in str(x).lower() or 'двигатель' in str(x).lower())))
        if engine_elem:
            engine_text = engine_elem.get_text(strip=True).lower()
            if 'дизель' in engine_text:
                return 'Дизель'
            elif 'бензин' in engine_text:
                return 'Бензин'
            elif any(x in engine_text for x in ['электро', 'электр']):
                return 'Электро'
        
        # Если не нашли в элементах, ищем в тексте
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
    
    def _extract_city(self, ad_element, text: str) -> str:
        """Извлечение города из HTML элементов и текста"""
        # Сначала ищем в структурированных элементах
        city_elem = (ad_element.find('div', class_=lambda x: x and ('city' in str(x).lower() or 'город' in str(x).lower() or 'location' in str(x).lower())) or
                    ad_element.find('span', class_=lambda x: x and ('city' in str(x).lower() or 'город' in str(x).lower() or 'location' in str(x).lower())))
        if city_elem:
            city_text = city_elem.get_text(strip=True)
            city_text_lower = city_text.lower()
            for city in self.CITIES:
                if city.lower() in city_text_lower:
                    return city
        
        # Если не нашли в элементах, ищем в тексте
        text_lower = text.lower()
        for city in self.CITIES:
            if city.lower() in text_lower:
                return city
        return ''
    
    def _extract_body_type_from_element(self, ad_element, text: str) -> Optional[str]:
        """Извлечение типа кузова из HTML элементов и текста"""
        # Сначала ищем в структурированных элементах
        body_elem = (ad_element.find('div', class_=lambda x: x and ('body' in str(x).lower() or 'кузов' in str(x).lower())) or
                    ad_element.find('span', class_=lambda x: x and ('body' in str(x).lower() or 'кузов' in str(x).lower())))
        if body_elem:
            body_text = body_elem.get_text(strip=True)
            body_type = self.extract_body_type(body_text)
            if body_type:
                return body_type
        
        # Если не нашли в элементах, используем базовый метод из текста
        return self.extract_body_type(text)
