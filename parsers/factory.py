"""
Фабрика для создания парсеров (Factory Pattern)
"""
# Стандартная библиотека
from typing import Dict, Optional

# Локальные импорты
from .base_parser import BaseParser
from .av_by_parser import AvByParser
from .kufar_parser import KufarParser
from .onliner_parser import OnlinerParser
from .abw_parser import AbwParser


class ParserFactory:
    """Фабрика для создания парсеров"""
    
    _parsers: Dict[str, BaseParser] = {}
    
    @classmethod
    def get_parser(cls, source: str) -> Optional[BaseParser]:
        """
        Получить парсер для указанного источника
        
        Args:
            source: Название источника ('av.by', 'kufar.by', 'ab.onliner.by', 'abw.by')
            
        Returns:
            Экземпляр парсера или None, если источник не поддерживается
        """
        if source not in cls._parsers:
            parser = cls._create_parser(source)
            if parser:
                cls._parsers[source] = parser
        
        return cls._parsers.get(source)
    
    @classmethod
    def _create_parser(cls, source: str) -> Optional[BaseParser]:
        """Создать парсер для указанного источника"""
        parsers_map = {
            'av.by': AvByParser,
            'kufar.by': KufarParser,
            'ab.onliner.by': OnlinerParser,
            'abw.by': AbwParser,
        }
        
        parser_class = parsers_map.get(source.lower())
        if parser_class:
            return parser_class()
        
        return None
    
    @classmethod
    def get_all_parsers(cls) -> Dict[str, BaseParser]:
        """Получить все доступные парсеры"""
        sources = ['av.by', 'kufar.by', 'ab.onliner.by', 'abw.by']
        return {source: cls.get_parser(source) for source in sources if cls.get_parser(source)}
