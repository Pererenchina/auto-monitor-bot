"""
Парсер для kufar.by (раздел Авто)

ВАЖНО: Реальный API kufar.by может использовать GraphQL или другие эндпоинты.
Возможно потребуется:
- Анализ реальных запросов через DevTools браузера
- Обновление формата запросов (GraphQL vs REST)
- Проверка актуальных параметров фильтрации
"""
# Стандартная библиотека
import asyncio
import logging
import re
from typing import List, Dict

# Сторонние библиотеки
import httpx

# Локальные импорты
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class KufarParser(BaseParser):
    """Парсер объявлений с kufar.by"""
    
    # ВАЖНО: Проверьте актуальный эндпоинт через DevTools браузера
    BASE_URL = "https://api.kufar.by/search-api/v1/search/rendered-paginated"
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на kufar.by"""
        results = []
        
        try:
            # Формируем параметры запроса
            # cat=1010 - это недвижимость! Для авто нужна другая категория
            # Попробуем cat=2010 (Автомобили) или использовать другой подход
            params = {
                'cat': 2010,  # Категория Автомобили (проверено)
                'size': 50,
                'sort': 'lst.d',
            }
            # Убрали 'cur': 'USD' и 'rgn': 0 - они вызывают пустые ответы
            
            # Фильтры через query параметры
            query_parts = []
            if filters.get('brand'):
                # Пробуем разные варианты написания бренда
                brand = filters['brand']
                query_parts.append(brand)
            if filters.get('model'):
                model = filters['model']
                query_parts.append(model)
            
            # Год и цена через отдельные параметры
            if filters.get('year_from'):
                # Kufar использует параметр prc для цены, но для года нужно искать в query или параметрах
                pass  # Год будет фильтроваться после получения результатов
            
            if filters.get('price_from_usd'):
                params['prc'] = f"{int(filters['price_from_usd'])}:{int(filters.get('price_to_usd', 999999))}"
            
            if query_parts:
                params['query'] = ' '.join(query_parts)
            
            headers = {
                **self.headers,
                'Referer': 'https://kufar.by/listings',
                'Accept': 'application/json',
            }
            
            # Добавляем задержку для избежания rate limiting
            await asyncio.sleep(1)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ads = data.get('ads', [])
                    
                    logger.info(f"kufar.by: Получено {len(ads)} объявлений из API")
                    
                    parsed_count = 0
                    filtered_count = 0
                    
                    # Парсим все объявления, фильтрация будет позже через matches_filters
                    for ad in ads:
                        car_data = self._parse_ad(ad)
                        if car_data:
                            parsed_count += 1
                            # Применяем фильтры только если они заданы
                            if not filters or self.matches_filters(car_data, filters):
                                results.append(car_data)
                            else:
                                filtered_count += 1
                                logger.debug(f"kufar.by: Объявление отфильтровано: {car_data.get('title', 'N/A')[:50]}")
                        else:
                            logger.debug(f"kufar.by: Не удалось распарсить объявление (ad_id: {ad.get('ad_id', 'N/A')})")
                    
                    logger.info(f"kufar.by: Распарсено {parsed_count} из {len(ads)}, отфильтровано {filtered_count}, осталось {len(results)}")
                elif response.status_code == 429:
                    logger.warning(f"kufar.by: Rate limit (429), пропускаю этот запрос")
                else:
                    logger.warning(f"kufar.by: HTTP {response.status_code}")
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге kufar.by: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
        
        return results
    
    def _parse_ad(self, ad: Dict) -> Dict:
        """Парсинг одного объявления"""
        try:
            ad_id = str(ad.get('ad_id', ''))
            if not ad_id:
                return None
            
            # Заголовок - пробуем разные ключи
            title = ad.get('subject') or ad.get('title') or ad.get('ad_title') or ''
            
            # Извлекаем марку и модель из параметров (более надежно)
            brand = ''
            model = ''
            
            # Параметры - пробуем разные варианты структуры
            params = {}
            # Пробуем ad_parameters (новый формат kufar.by)
            params_list = ad.get('ad_parameters', []) or ad.get('params', [])
            
            # Обрабатываем параметры в разных форматах
            for p in params_list:
                if isinstance(p, dict):
                    # Формат kufar.by: {'pl': 'Марка', 'vl': 'BMW', 'p': 'brand', 'v': '5', 'pu': 'brn'}
                    param_code = p.get('p') or p.get('pu')  # Код параметра (brand, cars_level_1, regdate и т.д.)
                    param_value = p.get('v')  # Числовое/кодовое значение
                    param_text = p.get('vl')  # Текстовое значение (предпочтительно)
                    param_label = p.get('pl')  # Метка (для отладки)
                    
                    # Используем текстовое значение, если есть, иначе числовое
                    final_value = param_text if param_text else param_value
                    
                    if param_code and final_value:
                        params[param_code] = final_value
                        
                        # Извлекаем марку и модель из текстовых значений
                        if param_code == 'brand' or param_code == 'brn':
                            # Используем текстовое значение (vl), если оно есть
                            brand = param_text if param_text else (param_label if 'марка' in str(param_label).lower() else '')
                        elif param_code == 'cars_level_1' or param_code == 'crl':
                            # Используем текстовое значение (vl), если оно есть
                            model = param_text if param_text else (param_label if 'модель' in str(param_label).lower() else '')
                elif isinstance(p, (list, tuple)) and len(p) >= 2:
                    # Формат: ['year', '2011']
                    params[p[0]] = p[1]
            
            # Если не нашли марку/модель в параметрах, пробуем из заголовка
            if not brand and title:
                parts = title.split()
                if len(parts) >= 2:
                    brand = parts[0]
                    model = ' '.join(parts[1:3]) if len(parts) > 1 else parts[1]
            
            # Год - пробуем разные ключи (kufar использует 'regdate' или 'rgd')
            year = None
            year_val = params.get('regdate') or params.get('rgd') or params.get('year') or params.get('год') or ad.get('year')
            if year_val:
                year = self.parse_year(str(year_val))
            
            # Если год не найден, пробуем извлечь из ad_parameters напрямую
            if not year:
                for p in params_list:
                    if isinstance(p, dict):
                        param_code = p.get('p') or p.get('pu')
                        if param_code in ['regdate', 'rgd', 'year']:
                            year_val = p.get('vl') or p.get('v')
                            if year_val:
                                year = self.parse_year(str(year_val))
                                break
            
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
            
            # Цена - пробуем разные форматы
            price_usd = None
            price_byn = None
            
            # Сначала пробуем извлечь из ad_parameters (более надежно для kufar.by)
            # В kufar.by цена обычно в price_info, но может быть и в ad_parameters
            for p in params_list:
                if isinstance(p, dict):
                    param_code = p.get('p') or p.get('pu')
                    param_label = p.get('pl', '').lower()
                    param_value = p.get('v')
                    param_text = p.get('vl')
                    
                    # Ищем цену по метке (pl) или коду (p/pu)
                    if 'цена' in param_label or 'price' in param_label or param_code in ['price', 'prc', 'price_usd', 'price_byn']:
                        try:
                            # Пробуем извлечь числовое значение
                            if param_text:
                                param_text_str = str(param_text)
                                
                                # Ищем первое число в строке (чтобы не объединять несколько чисел)
                                # Используем регулярное выражение для поиска числа с разделителями тысяч
                                # Ищем число с возможными разделителями тысяч (пробелы, запятые, точки)
                                # Формат: 55 650, 55,650, 55.650, 55650
                                price_match = re.search(r'(\d[\d\s,\.]*\d|\d)', param_text_str)
                                if not price_match:
                                    continue
                                
                                price_str = price_match.group(1)
                                # Убираем пробелы и неразрывные пробелы (разделители тысяч)
                                price_str = price_str.replace(' ', '').replace('\xa0', '')
                                
                                # Обрабатываем запятую и точку
                                if '.' in price_str and ',' in price_str:
                                    # Если есть и точка и запятая, определяем что есть что
                                    dot_pos = price_str.rindex('.')
                                    comma_pos = price_str.rindex(',')
                                    if dot_pos > comma_pos:
                                        # Точка - десятичный разделитель, запятая - разделитель тысяч
                                        price_str = price_str.replace(',', '')
                                    else:
                                        # Запятая - десятичный разделитель, точка - разделитель тысяч
                                        price_str = price_str.replace('.', '').replace(',', '.')
                                elif ',' in price_str:
                                    # Если только запятая, проверяем позицию
                                    comma_pos = price_str.rindex(',')
                                    digits_after = len(price_str) - comma_pos - 1
                                    if digits_after > 3:
                                        # Если после запятой больше 3 цифр, это разделитель тысяч
                                        price_str = price_str.replace(',', '')
                                    else:
                                        # Иначе это десятичный разделитель
                                        price_str = price_str.replace(',', '.')
                                elif '.' in price_str:
                                    # Если только точка, проверяем позицию
                                    dot_pos = price_str.rindex('.')
                                    digits_after = len(price_str) - dot_pos - 1
                                    if digits_after > 3:
                                        # Если после точки больше 3 цифр, это разделитель тысяч
                                        price_str = price_str.replace('.', '')
                                    # Иначе это десятичный разделитель, оставляем как есть
                                
                                if price_str:
                                    price_val = float(price_str)
                                    
                                    # ВАЛИДАЦИЯ: проверяем разумность цены сразу после парсинга
                                    if price_val > 1000000:  # Если больше 1 млн, вероятно ошибка
                                        logger.warning(f"kufar.by: Подозрительно большая цена при парсинге: {price_val} (исходная строка: '{param_text_str}'), пропускаем")
                                        continue
                                    
                                    # Определяем валюту по метке или контексту
                                    param_text_lower = param_text_str.lower()
                                    if 'usd' in param_label or '$' in param_text_lower or 'долл' in param_text_lower or param_code == 'price_usd':
                                        if not price_usd:  # Не перезаписываем, если уже есть
                                            price_usd = price_val
                                    elif 'byn' in param_label or 'р.' in param_text_lower or 'бел' in param_text_lower or 'руб' in param_text_lower or param_code == 'price_byn':
                                        if not price_byn:  # Не перезаписываем, если уже есть
                                            price_byn = price_val
                                    # Если валюта не определена, НЕ делаем предположений - оставляем None
                                    # Это предотвращает неправильную интерпретацию цен в BYN как USD
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Ошибка парсинга цены из kufar.by: {e}, param_text={param_text}")
                            pass
            
            # Если не нашли в ad_parameters, пробуем из price
            if not price_usd and not price_byn:
                price_info = ad.get('price', {})
                if price_info:
                    if isinstance(price_info, dict):
                        price_usd_raw = price_info.get('usd') or price_info.get('USD')
                        price_byn_raw = price_info.get('byn') or price_info.get('BYN')
                        # Преобразуем в числа, если они строки
                        try:
                            price_usd = float(price_usd_raw) if price_usd_raw else None
                            # Валидация: если цена больше 1 млн USD, вероятно ошибка
                            if price_usd and price_usd > 1000000:
                                logger.warning(f"kufar.by: Подозрительно большая цена USD из price_info: {price_usd}, пропускаем")
                                price_usd = None
                        except (ValueError, TypeError):
                            price_usd = None
                        try:
                            price_byn = float(price_byn_raw) if price_byn_raw else None
                            # Валидация: если цена больше 10 млн BYN, вероятно ошибка
                            if price_byn and price_byn > 10000000:
                                logger.warning(f"kufar.by: Подозрительно большая цена BYN из price_info: {price_byn}, пропускаем")
                                price_byn = None
                        except (ValueError, TypeError):
                            price_byn = None
                    elif isinstance(price_info, (int, float)):
                        price_byn = float(price_info)
                        # Валидация
                        if price_byn > 10000000:
                            logger.warning(f"kufar.by: Подозрительно большая цена BYN из price_info (число): {price_byn}, пропускаем")
                            price_byn = None
            
            # Также пробуем напрямую из ad
            if not price_usd and not price_byn:
                price_usd_raw = ad.get('price_usd') or ad.get('priceUSD')
                price_byn_raw = ad.get('price_byn') or ad.get('priceBYN') or ad.get('price')
                try:
                    price_usd = float(price_usd_raw) if price_usd_raw else None
                    # Валидация
                    if price_usd and price_usd > 1000000:
                        logger.warning(f"kufar.by: Подозрительно большая цена USD из ad: {price_usd}, пропускаем")
                        price_usd = None
                except (ValueError, TypeError):
                    price_usd = None
                try:
                    price_byn = float(price_byn_raw) if price_byn_raw else None
                    # Валидация
                    if price_byn and price_byn > 10000000:
                        logger.warning(f"kufar.by: Подозрительно большая цена BYN из ad: {price_byn}, пропускаем")
                        price_byn = None
                except (ValueError, TypeError):
                    price_byn = None
            
            # Конвертация валют, если одна из цен отсутствует (примерный курс: 1 USD = 3.3 BYN)
            # Но только если цены разумные (проверка на ошибки парсинга)
            if price_usd and not price_byn:
                if price_usd < 1000000:  # Проверка на разумность (максимум 1 млн USD)
                    price_byn = round(price_usd * 3.3, 0)
                else:
                    logger.warning(f"kufar.by: Подозрительно большая цена USD: {price_usd}, пропускаем конвертацию")
                    price_usd = None
            elif price_byn and not price_usd:
                if price_byn < 10000000:  # Проверка на разумность (максимум 10 млн BYN)
                    price_usd = round(price_byn / 3.3, 0)
                else:
                    logger.warning(f"kufar.by: Подозрительно большая цена BYN: {price_byn}, пропускаем конвертацию")
                    price_byn = None
            
            # Дополнительная проверка: если обе цены есть, но они несоответствуют курсу - исправляем
            if price_usd and price_byn:
                expected_byn = price_usd * 3.3
                expected_usd = price_byn / 3.3
                # Если разница больше 50%, вероятно ошибка парсинга
                if abs(price_byn - expected_byn) / max(expected_byn, 1) > 0.5:
                    logger.warning(f"kufar.by: Несоответствие цен: USD={price_usd}, BYN={price_byn}, ожидалось BYN={expected_byn:.0f}")
                    # Оставляем ту цену, которая более вероятна
                    if price_byn < 10000000:  # Если BYN разумная, используем её
                        price_usd = round(price_byn / 3.3, 0)
                    elif price_usd < 1000000:  # Если USD разумная, используем её
                        price_byn = round(price_usd * 3.3, 0)
                    else:
                        # Обе цены подозрительные, сбрасываем
                        price_usd = None
                        price_byn = None
            
            # Пробег - пробуем разные ключи
            mileage = params.get('mileage') or params.get('пробег') or params.get('odometer') or ad.get('mileage')
            if mileage:
                mileage = self.parse_mileage(str(mileage))
            
            # Объем двигателя - пробуем разные ключи
            engine_volume = params.get('engine_volume') or params.get('объем') or params.get('engine') or ad.get('engine_volume')
            if engine_volume:
                try:
                    engine_volume = float(str(engine_volume).replace(',', '.'))
                except (ValueError, TypeError):
                    engine_volume = None
            
            # Город
            city = params.get('city') or params.get('город') or ad.get('location', {}).get('name', '') or ad.get('city', '')
            
            # Фото
            image_url = None
            images = ad.get('images', [])
            if images:
                if isinstance(images[0], dict):
                    image_url = images[0].get('url') or images[0].get('src') or images[0].get('link')
                elif isinstance(images[0], str):
                    image_url = images[0]
            
            # Коробка передач - пробуем разные ключи
            transmission = params.get('transmission') or params.get('коробка') or params.get('gearbox') or ad.get('transmission')
            if transmission:
                trans_lower = str(transmission).lower()
                if 'автомат' in trans_lower or 'automatic' in trans_lower or 'авт' in trans_lower:
                    transmission = 'Автомат'
                elif 'механика' in trans_lower or 'manual' in trans_lower or 'мех' in trans_lower:
                    transmission = 'Механика'
            
            # Тип двигателя - пробуем разные ключи
            engine_type = params.get('fuel_type') or params.get('топливо') or params.get('fuel') or ad.get('fuel_type')
            if engine_type:
                fuel_lower = str(engine_type).lower()
                if 'бензин' in fuel_lower or 'petrol' in fuel_lower or 'gasoline' in fuel_lower:
                    engine_type = 'Бензин'
                elif 'дизель' in fuel_lower or 'diesel' in fuel_lower:
                    engine_type = 'Дизель'
                elif 'электро' in fuel_lower or 'electric' in fuel_lower or 'электр' in fuel_lower:
                    engine_type = 'Электро'
            
            # Тип кузова - извлекаем из параметров или текста
            body_type = params.get('body_type') or params.get('кузов') or params.get('body') or ad.get('body_type')
            if not body_type:
                # Пробуем извлечь из текста объявления
                full_text = f"{title} {ad.get('description', '')} {ad.get('ad_text', '')}"
                body_type = self.extract_body_type(full_text, params)
            
            # URL - пробуем разные варианты полей
            url = ad.get('ad_link') or ad.get('link') or ad.get('url') or ad.get('ad_url')
            if not url:
                # Формируем URL из ID
                url = f"https://kufar.by/item/{ad_id}"
            elif not url.startswith('http'):
                url = f"https://kufar.by{url}" if url.startswith('/') else f"https://kufar.by/{url}"
            
            return {
                'source': 'kufar.by',
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
            logger.error(f"Ошибка при парсинге объявления kufar.by: {e}", exc_info=True)
            return None
