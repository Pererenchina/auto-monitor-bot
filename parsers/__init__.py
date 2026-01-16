"""
Парсеры для различных сайтов с объявлениями
"""
from .av_by_parser import AvByParser
from .kufar_parser import KufarParser
from .onliner_parser import OnlinerParser
from .abw_parser import AbwParser

__all__ = ['AvByParser', 'KufarParser', 'OnlinerParser', 'AbwParser']
