"""
Парсер для kufar.by (раздел Авто)
Упрощенная версия без дублирования кода
"""
import asyncio
import logging
from typing import List, Dict, Optional

import httpx

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class KufarParser(BaseParser):
    """Парсер объявлений с kufar.by"""
    
    BASE_URL = "https://api.kufar.by/search-api/v1/search/rendered-paginated"
    EXCHANGE_RATE = 2.9
    
    async def search(self, filters: Dict) -> List[Dict]:
        """Поиск объявлений на kufar.by"""
        results = []
        
        try:
            params = {
                'cat': 2010,  # Категория Автомобили
                'size': 50,
                'sort': 'lst.d',  # Сортировка по дате (новые сначала)
            }
            
            # Поисковый запрос
            query_parts = []
            if filters.get('brand'):
                query_parts.append(filters['brand'])
            if filters.get('model'):
                query_parts.append(filters['model'])
            
            if query_parts:
                params['query'] = ' '.join(query_parts)
            
            headers = {
                **self.headers,
                'Referer': 'https://kufar.by/listings',
                'Accept': 'application/json',
            }
            
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
                    first_filtered = None
                    
                    for ad in ads:
                        car_data = self._parse_ad(ad)
                        if car_data:
                            parsed_count += 1
                            if not filters or self.matches_filters(car_data, filters):
                                results.append(car_data)
                            else:
                                filtered_count += 1
                                if filtered_count == 1 and first_filtered is None:
                                    first_filtered = car_data
                    
                    if first_filtered:
                        logger.info(f"kufar.by: Пример отфильтрованного: brand='{first_filtered.get('brand')}', model='{first_filtered.get('model')}', filter_brand='{filters.get('brand')}', filter_model='{filters.get('model')}', year={first_filtered.get('year')}, filter_year_from={filters.get('year_from')}, price_usd={first_filtered.get('price_usd')}, filter_price_to={filters.get('price_to_usd')}")
                    
                    logger.info(f"kufar.by: Распарсено {parsed_count} из {len(ads)}, отфильтровано {filtered_count}, осталось {len(results)}")
                elif response.status_code == 429:
                    logger.warning(f"kufar.by: Rate limit (429), пропускаю этот запрос")
                else:
                    logger.warning(f"kufar.by: HTTP {response.status_code}: {response.text[:200]}")
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге kufar.by: {e}", exc_info=True)
        
        return results
    
    def _parse_ad(self, ad: Dict) -> Optional[Dict]:
        """Парсинг одного объявления"""
        try:
            ad_id = str(ad.get('ad_id', ''))
            if not ad_id:
                return None
            
            title = ad.get('subject') or ad.get('title') or ad.get('ad_title') or ''
            
            # Параметры объявления
            params_dict = self._extract_params(ad)
            
            # Марка и модель
            brand = params_dict.get('brand', '')
            model = params_dict.get('model', '')
            
            if not brand and title:
                parts = title.split()
                if len(parts) >= 2:
                    brand = parts[0]
                    model = ' '.join(parts[1:3]) if len(parts) > 1 else parts[1]
            
            # Улучшаем title
            if not title or len(title) < 10:
                title_parts = []
                if brand:
                    title_parts.append(brand)
                if model:
                    title_parts.append(model)
                if params_dict.get('year'):
                    title_parts.append(str(params_dict['year']))
                if title_parts:
                    title = ' '.join(title_parts)
            
            # Цены
            price_usd, price_byn = self._extract_prices(ad)
            
            # Год
            year = params_dict.get('year')
            if year:
                year = self.parse_year(str(year))
            
            # Пробег
            mileage = params_dict.get('mileage')
            if mileage:
                mileage = self.parse_mileage(str(mileage))
            
            # Объем двигателя
            engine_volume = params_dict.get('engine_volume')
            if engine_volume:
                try:
                    engine_volume = float(str(engine_volume).replace(',', '.'))
                except (ValueError, TypeError):
                    engine_volume = None
            
            # Город
            city = params_dict.get('city') or ad.get('location', {}).get('name', '') or ad.get('city', '')
            
            # Фото
            image_url = self._extract_image(ad)
            
            # Коробка передач
            transmission = self._normalize_transmission(params_dict.get('transmission'))
            
            # Тип двигателя
            engine_type = self._normalize_engine_type(params_dict.get('engine_type'))
            
            # Тип кузова
            body_type = params_dict.get('body_type')
            if not body_type:
                full_text = f"{title} {ad.get('description', '')} {ad.get('ad_text', '')}"
                body_type = self.extract_body_type(full_text, params_dict)
            
            # URL
            url = ad.get('ad_link') or ad.get('link') or ad.get('url') or ad.get('ad_url')
            if not url:
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
    
    def _extract_params(self, ad: Dict) -> Dict:
        """Извлечение параметров из объявления"""
        params = {}
        params_list = ad.get('ad_parameters', []) or ad.get('params', [])
        
        param_mapping = {
            'brand': ['brand', 'brn'],
            'model': ['cars_level_1', 'crl', 'model'],
            'year': ['regdate', 'rgd', 'year'],
            'mileage': ['mileage', 'odometer', 'пробег'],
            'engine_volume': ['engine_volume', 'объем', 'engine'],
            'city': ['city', 'город', 'location'],
            'transmission': ['transmission', 'коробка', 'gearbox'],
            'engine_type': ['fuel_type', 'топливо', 'fuel'],
            'body_type': ['body_type', 'кузов', 'body'],
        }
        
        for p in params_list:
            if not isinstance(p, dict):
                continue
            
            param_code = p.get('p') or p.get('pu')
            param_text = p.get('vl')
            param_value = p.get('v')
            param_label = p.get('pl', '').lower()
            
            param_type = None
            for key, codes in param_mapping.items():
                if param_code in codes or any(code in param_label for code in codes):
                    param_type = key
                    break
            
            if param_type:
                if param_type == 'mileage' and param_value is not None:
                    params[param_type] = param_value
                else:
                    value = param_text if param_text and str(param_text).strip() else param_value
                    if value is not None:
                        params[param_type] = value
        
        return params
    
    def _normalize_price_value(self, price_val: float) -> Optional[float]:
        """Нормализация значения цены (обработка копеек)"""
        if not price_val or price_val <= 0:
            return None
        
        # Если цена очень большая (> 10 млн), возможно это копейки
        if price_val > 10000000:
            price_in_rubles = price_val / 100
            # Если после деления получается разумная цена (10000-100000 рублей)
            if 10000 <= price_in_rubles <= 100000:
                logger.info(f"kufar.by: Цена {price_val} интерпретирована как копейки, конвертирована в рубли: {price_in_rubles}")
                return price_in_rubles
        
        # Ограничиваем максимальную цену
        if price_val <= 50000000:
            return price_val
        
        return None
    
    def _extract_prices(self, ad: Dict) -> tuple:
        """Извлечение цен из объявления"""
        price_usd = None
        price_byn = None
        
        # Пробуем из price_info
        price_info = ad.get('price', {})
        if isinstance(price_info, dict):
            price_byn_raw = price_info.get('byn') or price_info.get('BYN')
            if price_byn_raw:
                try:
                    price_byn = self._normalize_price_value(float(price_byn_raw))
                except (ValueError, TypeError):
                    pass
            
            price_usd_raw = price_info.get('usd') or price_info.get('USD')
            if price_usd_raw:
                try:
                    price_usd_val = float(price_usd_raw)
                    if 0 < price_usd_val <= 1000000:
                        price_usd = price_usd_val
                    elif 1000000 < price_usd_val <= 10000000 and not price_byn:
                        # Возможно это BYN в USD поле
                        price_byn = self._normalize_price_value(price_usd_val)
                        if price_byn:
                            price_usd = round(price_byn / self.EXCHANGE_RATE, 0)
                except (ValueError, TypeError):
                    pass
        
        # Пробуем напрямую из ad
        if not price_usd and not price_byn:
            price_byn_raw = ad.get('price_byn') or ad.get('priceBYN') or ad.get('price')
            if price_byn_raw:
                try:
                    price_byn = self._normalize_price_value(float(price_byn_raw))
                except (ValueError, TypeError):
                    pass
            
            price_usd_raw = ad.get('price_usd') or ad.get('priceUSD')
            if price_usd_raw:
                try:
                    price_usd_val = float(price_usd_raw)
                    if 0 < price_usd_val <= 1000000:
                        price_usd = price_usd_val
                    elif 1000000 < price_usd_val <= 10000000 and not price_byn:
                        price_byn = self._normalize_price_value(price_usd_val)
                        if price_byn:
                            price_usd = round(price_byn / self.EXCHANGE_RATE, 0)
                except (ValueError, TypeError):
                    pass
        
        # Нормализация и конвертация
        price_usd, price_byn = self.normalize_prices(price_usd, price_byn, validate=True)
        
        return price_usd, price_byn
    
    def _extract_image(self, ad: Dict) -> Optional[str]:
        """Извлечение URL изображения"""
        images = ad.get('images', [])
        if images:
            if isinstance(images[0], dict):
                return images[0].get('url') or images[0].get('src') or images[0].get('link')
            elif isinstance(images[0], str):
                return images[0]
        return None
    
    def _normalize_transmission(self, transmission: Optional[str]) -> Optional[str]:
        """Нормализация коробки передач"""
        if not transmission:
            return None
        
        trans_lower = str(transmission).lower()
        if any(x in trans_lower for x in ['автомат', 'automatic', 'авт']):
            return 'Автомат'
        elif any(x in trans_lower for x in ['механика', 'manual', 'мех']):
            return 'Механика'
        return None
    
    def _normalize_engine_type(self, engine_type: Optional[str]) -> Optional[str]:
        """Нормализация типа двигателя"""
        if not engine_type:
            return None
        
        fuel_lower = str(engine_type).lower()
        if any(x in fuel_lower for x in ['бензин', 'petrol', 'gasoline']):
            return 'Бензин'
        elif any(x in fuel_lower for x in ['дизель', 'diesel']):
            return 'Дизель'
        elif any(x in fuel_lower for x in ['электро', 'electric', 'электр']):
            return 'Электро'
        return None
