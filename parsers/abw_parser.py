"""
Парсер для abw.by

Использует HTML-парсинг через BeautifulSoup и cloudscraper.
Объявления находятся в элементах с классом 'card' и 'card--hover'.
"""
import asyncio
import logging
import cloudscraper
from bs4 import BeautifulSoup
import re
from typing import List, Dict
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class AbwParser(BaseParser):
    """Парсер объявлений с abw.by"""
    
    BASE_URL = "https://abw.by/cars"
    
    def __init__(self):
        super().__init__()
        # Используем cloudscraper для обхода защиты
        self.scraper = cloudscraper.create_scraper()
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на abw.by"""
        results = []
        
        try:
            # Формируем URL - abw.by не поддерживает фильтры в URL, используем базовый URL
            # Фильтрация будет происходить локально после парсинга
            url = self.BASE_URL
            logger.info(f"abw.by: Используется базовый URL: {url} (фильтры: brand={filters.get('brand')}, model={filters.get('model')}, price_to={filters.get('price_to_usd')})")
            
            # Выполняем запрос синхронно через cloudscraper
            # Добавляем задержку для избежания rate limiting
            await asyncio.sleep(0.5)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
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
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                logger.info(f"abw.by: Получен HTML, размер: {len(response.text)} символов")
                
                # Ищем объявления через ссылки на детальные страницы
                detail_links = soup.find_all('a', href=lambda x: x and '/cars/detail/' in str(x))
                logger.info(f"abw.by: Найдено ссылок на объявления: {len(detail_links)}")
                ads = []
                
                # Получаем родительские элементы для каждой ссылки
                for link in detail_links:
                    # Ищем родительский элемент с классом card__wrapper или card
                    parent = link.find_parent('div', class_=lambda x: x and ('card__wrapper' in str(x) or ('card' in str(x) and 'card__' not in str(x))))
                    if parent and parent not in ads:
                        ads.append(parent)
                
                # Если не нашли через ссылки, пробуем через card__wrapper
                if not ads:
                    ads = soup.find_all('div', class_='card__wrapper')
                
                # Если все еще не нашли, ищем через card__info
                if not ads:
                    card_infos = soup.find_all('div', class_='card__info')
                    for info in card_infos:
                        parent = info.find_parent('div', class_=lambda x: x and 'card' in str(x))
                        if parent and parent not in ads:
                            ads.append(parent)
                
                parsed_count = 0
                filtered_count = 0
                first_filtered = None
                for ad in ads[:50]:  # Ограничиваем 50 объявлениями
                    car_data = self._parse_ad(ad)
                    if car_data:
                        parsed_count += 1
                        if self.matches_filters(car_data, filters):
                            results.append(car_data)
                        else:
                            filtered_count += 1
                            # Сохраняем первый отфильтрованный для логирования
                            if filtered_count == 1 and first_filtered is None:
                                first_filtered = car_data
                
                # Логируем первый отфильтрованный после цикла
                if first_filtered:
                    logger.info(f"abw.by: Пример отфильтрованного: brand='{first_filtered.get('brand')}', model='{first_filtered.get('model')}', filter_brand='{filters.get('brand')}', filter_model='{filters.get('model')}', year={first_filtered.get('year')}, filter_year_from={filters.get('year_from')}, price_usd={first_filtered.get('price_usd')}, filter_price_to={filters.get('price_to_usd')}")
                
                logger.info(f"abw.by: Распарсено {parsed_count} из {len(ads)}, отфильтровано {filtered_count}, осталось {len(results)}")
        
            elif response.status_code != 200:
                logger.warning(f"abw.by: HTTP {response.status_code} для URL: {url}")
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге abw.by: {e}", exc_info=True)
        
        logger.info(f"abw.by: Завершено, найдено {len(results)} объявлений")
        return results
    
    def _parse_ad(self, ad_element) -> Dict:
        """Парсинг одного объявления"""
        try:
            # Получаем весь текст элемента
            full_text = ad_element.get_text(separator=' ', strip=True)
            
            # ID объявления из ссылки
            ad_id = ''
            url = ''
            
            # Ищем ссылку на детальную страницу объявления
            link_elem = None
            
            # Сначала ищем ссылку с /cars/detail/
            detail_link = ad_element.find('a', href=lambda x: x and '/cars/detail/' in str(x))
            if detail_link:
                link_elem = detail_link
            else:
                # Пробуем любую ссылку
                link_elem = (ad_element.find('a', href=True) or 
                            ad_element.find('a', class_=lambda x: x and ('link' in str(x).lower() or 'card' in str(x).lower())) or
                            ad_element.find('a'))
            
            if link_elem:
                href = link_elem.get('href', '')
                if href:
                    # Извлекаем ID из URL вида /cars/detail/volvo/xc90/19001535
                    if '/cars/detail/' in href:
                        parts = [p for p in href.split('/') if p]
                        if parts:
                            # Последняя часть - это ID
                            last_part = parts[-1]
                            if last_part.isdigit():
                                ad_id = last_part
                            # Или предпоследняя, если последняя - модель
                            elif len(parts) > 1 and parts[-2].isdigit():
                                ad_id = parts[-2]
                    
                    # Сохраняем полный href для URL
                    url = href
            
            # Заголовок - ищем в разных местах
            title = ''
            
            # Пробуем найти в card__info (там обычно название)
            info_elem = ad_element.find('div', class_='card__info')
            if info_elem:
                # Берем первую строку из card__info, которая содержит название
                info_text = info_elem.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in info_text.split('\n') if line.strip()]
                if lines:
                    # Первая строка обычно содержит марку и модель
                    title = lines[0]
            
            # Если не нашли, пробуем найти ссылку с текстом
            if not title and link_elem:
                link_text = link_elem.get_text(strip=True)
                if link_text and len(link_text) > 3:
                    title = link_text
            
            # Если заголовок пустой, пробуем извлечь из текста
            if not title:
                # Ищем паттерн "Марка Модель" в начале текста
                match = re.match(r'^([A-Za-zА-Яа-яЁё\s]+?)(?:\s+[I\d]|,|\d)', full_text)
                if match:
                    title = match.group(1).strip()
            
            # Если все еще пусто, берем первые слова из текста
            if not title:
                words = full_text.split()[:3]
                if words:
                    title = ' '.join(words)
            
            # Извлекаем марку и модель из заголовка, URL или текста
            brand = ''
            model = ''
            
            # Сначала пробуем из URL вида /cars/detail/volvo/xc90/19001535
            if url and '/cars/detail/' in url:
                try:
                    url_parts = url.split('/cars/detail/')[1].split('/')
                    if len(url_parts) >= 2:
                        brand = url_parts[0].capitalize()
                        model = url_parts[1].capitalize()
                except:
                    pass
            
            # Если не нашли в URL, пробуем из заголовка
            if not brand or not model:
                if title:
                    parts = title.split()
                    if len(parts) >= 2:
                        brand = parts[0]
                        # Берем следующие слова для модели, но останавливаемся на годах
                        model_parts = []
                        for i in range(1, min(4, len(parts))):
                            word = parts[i]
                            # Останавливаемся на годах
                            if word.isdigit() and len(word) == 4:
                                break
                            model_parts.append(word)
                        model = ' '.join(model_parts) if model_parts else parts[1] if len(parts) > 1 else ''
            
            # Если все еще не нашли, пробуем из полного текста
            if not brand or not model:
                # Ищем известные марки в тексте
                known_brands = ['BMW', 'Mercedes', 'Audi', 'Toyota', 'Nissan', 'Volkswagen', 
                              'Hyundai', 'Kia', 'Renault', 'Skoda', 'Ford', 'Mazda', 'Honda',
                              'Lexus', 'Volvo', 'LADA', 'BelGee', 'Geely', 'Chery', 'Haval',
                              'Opel', 'Peugeot', 'Fiat', 'Subaru', 'Mitsubishi', 'Suzuki',
                              'Citroen', 'Chevrolet', 'Tesla']
                for known_brand in known_brands:
                    if known_brand.lower() in full_text.lower():
                        brand = known_brand
                        # Пробуем найти модель после марки
                        brand_pos = full_text.lower().find(known_brand.lower())
                        if brand_pos >= 0:
                            after_brand = full_text[brand_pos + len(known_brand):].strip()
                            model_parts = []
                            for word in after_brand.split()[:4]:  # Первые 4 слова после марки
                                # Останавливаемся на годах или других числовых значениях
                                if word.isdigit() and len(word) == 4:
                                    break
                                model_parts.append(word)
                            model = ' '.join(model_parts) if model_parts else ''
                        break
            
            # Цена - ищем в специальных элементах или в тексте
            price_usd = None
            price_byn = None
            
            # Пробуем найти элемент с ценой
            price_elem = (ad_element.find('div', class_=lambda x: x and 'price' in str(x).lower()) or
                         ad_element.find('span', class_=lambda x: x and 'price' in str(x).lower()) or
                         ad_element.find('div', class_='card__price'))
            
            price_text = ''
            if price_elem:
                price_text = price_elem.get_text(strip=True)
            else:
                # Ищем цену в полном тексте
                price_text = full_text
            
            # Ищем паттерны цены: "52 495 р.18 000 $" или "18 000 $52 495 р." или "52 495 р. 18 000 $"
            # Пробуем разные варианты разделителей
            price_patterns = [
                r'(\d[\d\s]+)\s*р\.\s*(\d[\d\s]+)\s*\$',  # "52 495 р. 18 000 $"
                r'(\d[\d\s]+)\s*\$\s*(\d[\d\s]+)\s*р\.',  # "18 000 $ 52 495 р."
                r'(\d[\d\s]+)\s*р\.\s*(\d[\d\s]+)\s*\$',  # без пробела
            ]
            
            price_match = None
            for pattern in price_patterns:
                price_match = re.search(pattern, price_text)
                if price_match:
                    break
            
            if price_match:
                # Определяем, какая группа USD, а какая BYN
                group1 = price_match.group(1).replace(' ', '').replace('\xa0', '')
                group2 = price_match.group(2).replace(' ', '').replace('\xa0', '')
                
                # Проверяем, какая группа содержит $ или р.
                match_text = price_match.group(0)
                if '$' in match_text and 'р.' in match_text:
                    # Определяем порядок
                    if match_text.index('$') < match_text.index('р.'):
                        # $ идет первым
                        try:
                            price_usd = float(group1)
                            price_byn = float(group2)
                        except:
                            pass
                    else:
                        # р. идет первым
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
            
            # Конвертация валют, если одна из цен отсутствует (примерный курс: 1 USD = 3.3 BYN)
            if price_usd and not price_byn:
                price_byn = price_usd * 3.3
            elif price_byn and not price_usd:
                price_usd = price_byn / 3.3
            
            # Год - ищем в тексте (например, "2011")
            year = None
            year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
            if year_match:
                try:
                    year = int(year_match.group(0))
                except:
                    pass
            
            # Пробег - ищем "64 816 км" или подобное
            # Важно: не захватывать год (например, "2022 180 000 км" -> только "180 000")
            mileage = None
            # Ищем все возможные варианты пробега перед "км"
            mileage_matches = re.finditer(r'(\d{1,3}(?:\s+\d{3})*)\s*км', full_text)
            for match in mileage_matches:
                mileage_str = match.group(1)
                # Проверяем, не является ли это годом (19xx или 20xx)
                mileage_cleaned = mileage_str.replace(' ', '').replace('\xa0', '')
                if len(mileage_cleaned) == 4:
                    # Если 4 цифры, проверяем, не год ли это
                    try:
                        year_candidate = int(mileage_cleaned)
                        if 1900 <= year_candidate <= 2100:
                            # Это год, пропускаем
                            continue
                    except:
                        pass
                
                # Пробуем распарсить через parse_mileage
                mileage = self.parse_mileage(mileage_str)
                if mileage:
                    # Если успешно распарсили и валидация прошла, используем это значение
                    break
            
            # Объем двигателя - ищем "2.4 л" или подобное
            engine_volume = None
            volume_match = re.search(r'(\d+[.,]?\d*)\s*л', full_text)
            if volume_match:
                try:
                    engine_volume = float(volume_match.group(1).replace(',', '.'))
                except:
                    pass
            
            # Коробка передач
            transmission = None
            full_text_lower = full_text.lower()
            if 'вариатор' in full_text_lower or 'cvt' in full_text_lower:
                transmission = 'Вариатор'
            elif 'автомат' in full_text_lower or 'автоматическая' in full_text_lower:
                transmission = 'Автомат'
            elif 'механика' in full_text_lower or 'мех' in full_text_lower or 'механическая' in full_text_lower:
                transmission = 'Механика'
            
            # Тип двигателя
            engine_type = None
            if 'дизель' in full_text.lower():
                engine_type = 'Дизель'
            elif 'бензин' in full_text.lower():
                engine_type = 'Бензин'
            elif 'электро' in full_text.lower() or 'электр' in full_text.lower():
                engine_type = 'Электро'
            
            # Тип кузова - извлекаем из текста
            body_type = self.extract_body_type(full_text)
            
            # Фото
            image_url = None
            img_elem = ad_element.find('img')
            if img_elem:
                image_url = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
                if image_url:
                    if not image_url.startswith('http'):
                        image_url = 'https://abw.by' + image_url
            
            # URL - обрабатываем извлеченный href
            if url:
                if not url.startswith('http'):
                    # Если относительный путь, добавляем домен
                    if url.startswith('/'):
                        url = 'https://abw.by' + url
                    else:
                        url = 'https://abw.by/' + url
            elif ad_id:
                # Если URL не найден, но есть ID, формируем URL
                # Пробуем разные форматы URL для abw.by
                if brand and model:
                    # Формат: /cars/detail/brand/model/id
                    brand_slug = brand.lower().replace(' ', '-')
                    model_slug = model.lower().replace(' ', '-')
                    url = f"https://abw.by/cars/detail/{brand_slug}/{model_slug}/{ad_id}"
                else:
                    # Простой формат с ID
                    url = f"https://abw.by/cars/{ad_id}"
            
            # Если все еще нет URL, используем fallback
            if not url:
                url = 'https://abw.by/cars'
            
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
                title = f"{brand} {model}".strip()
                if year:
                    title = f"{title} {year}".strip()
            
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
                'city': self._extract_city(full_text),  # Извлекаем город из текста
                'url': url or 'https://abw.by/cars',
                'image_url': image_url,
                'transmission': transmission,
                'engine_type': engine_type,
                'body_type': body_type,
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге объявления abw.by: {e}", exc_info=True)
            return None
    
    def _extract_city(self, text: str) -> str:
        """Извлечение города из текста объявления"""
        # Список городов Беларуси
        cities = [
            'Минск', 'Гомель', 'Могилев', 'Витебск', 'Гродно', 'Брест',
            'Бобруйск', 'Барановичи', 'Борисов', 'Пинск', 'Орша', 'Мозырь',
            'Солигорск', 'Новополоцк', 'Лида', 'Молодечно', 'Полоцк', 'Жлобин',
            'Светлогорск', 'Речица', 'Слуцк', 'Кобрин', 'Волковыск', 'Калинковичи',
            'Сморгонь', 'Рогачев', 'Осиповичи', 'Жодино', 'Слоним', 'Кричев'
        ]
        
        text_lower = text.lower()
        for city in cities:
            if city.lower() in text_lower:
                return city
        
        return ''
