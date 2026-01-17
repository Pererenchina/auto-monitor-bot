"""
Конфигурация бота
"""
# Стандартная библиотека
import os
from pathlib import Path
from typing import List, Tuple, Dict

# Сторонние библиотеки
from dotenv import load_dotenv

# Загружаем .env из корневой директории проекта
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, encoding='utf-8-sig')

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден в переменных окружения. "
        "Создайте файл .env с BOT_TOKEN=your_token"
    )

# Справочники марок и моделей для выбора по кнопкам
# Популярные марки на белорусском рынке (av.by, kufar.by, onliner.by, abw.by)
BRANDS: List[Tuple[str, str]] = [
    # Премиум сегмент
    ("bmw", "BMW"),
    ("mercedes", "Mercedes-Benz"),
    ("audi", "Audi"),
    ("lexus", "Lexus"),
    ("volvo", "Volvo"),
    ("tesla", "Tesla"),
    # Немецкие марки
    ("volkswagen", "Volkswagen"),
    ("opel", "Opel"),
    # Японские марки
    ("toyota", "Toyota"),
    ("nissan", "Nissan"),
    ("honda", "Honda"),
    ("mazda", "Mazda"),
    ("mitsubishi", "Mitsubishi"),
    ("subaru", "Subaru"),
    ("suzuki", "Suzuki"),
    # Корейские марки
    ("hyundai", "Hyundai"),
    ("kia", "Kia"),
    # Французские марки
    ("renault", "Renault"),
    ("peugeot", "Peugeot"),
    ("citroen", "Citroen"),
    # Чешские марки
    ("skoda", "Skoda"),
    # Американские марки
    ("ford", "Ford"),
    ("chevrolet", "Chevrolet"),
    # Итальянские марки
    ("fiat", "Fiat"),
    # Популярные в Беларуси
    ("belgee", "BelGee"),
    ("lada", "LADA"),
    ("geely", "Geely"),
    ("chery", "Chery"),
    ("byd", "BYD"),
    ("haval", "Haval"),
    ("greatwall", "Great Wall"),
    ("dongfeng", "Dongfeng"),
    ("faw", "FAW"),
    ("changan", "Changan"),
]

# Типы кузовов автомобилей
BODY_TYPES: List[Tuple[str, str]] = [
    ("sedan", "Седан"),
    ("hatchback", "Хэтчбек"),
    ("universal", "Универсал"),
    ("suv", "Внедорожник"),
    ("crossover", "Кроссовер"),
    ("coupe", "Купе"),
    ("cabriolet", "Кабриолет"),
    ("minivan", "Минивэн"),
    ("van", "Фургон"),
    ("pickup", "Пикап"),
    ("liftback", "Лифтбек"),
    ("wagon", "Универсал"),
]

BRAND_MODELS: Dict[str, List[str]] = {
    # BMW
    "bmw": ["1 Series", "2 Series", "3 Series", "4 Series", "5 Series", "6 Series", "7 Series", "8 Series", 
            "X1", "X2", "X3", "X4", "X5", "X6", "X7", "Z4", "i3", "i4", "iX"],
    # Mercedes-Benz
    "mercedes": ["A-Class", "B-Class", "C-Class", "E-Class", "S-Class", "CLA", "CLS", "GLA", "GLB", "GLC", 
                 "GLE", "GLS", "G-Class", "AMG GT", "EQC", "EQS"],
    # Audi
    "audi": ["A1", "A3", "A4", "A5", "A6", "A7", "A8", "Q2", "Q3", "Q5", "Q7", "Q8", "e-tron", "TT", "R8"],
    # Lexus
    "lexus": ["IS", "ES", "GS", "LS", "NX", "RX", "GX", "LX", "UX", "LC"],
    # Volvo
    "volvo": ["S40", "S60", "S80", "S90", "V40", "V60", "V90", "XC40", "XC60", "XC90"],
    # Tesla
    "tesla": ["Model S", "Model 3", "Model X", "Model Y"],
    # Volkswagen
    "volkswagen": ["Polo", "Golf", "Jetta", "Passat", "Arteon", "Tiguan", "Touareg", "T-Cross", "T-Roc", "ID.3", "ID.4"],
    # Opel
    "opel": ["Corsa", "Astra", "Insignia", "Crossland", "Grandland", "Mokka", "Combo"],
    # Toyota
    "toyota": ["Yaris", "Corolla", "Camry", "Prius", "RAV4", "Highlander", "Land Cruiser", "Prado", "C-HR", "bZ4X"],
    # Nissan
    "nissan": ["Almera", "Sentra", "Altima", "Maxima", "Juke", "Qashqai", "X-Trail", "Pathfinder", "Murano", "Patrol", "Leaf"],
    # Honda
    "honda": ["Civic", "Accord", "CR-V", "HR-V", "Pilot", "Passport", "Ridgeline", "e"],
    # Mazda
    "mazda": ["2", "3", "6", "CX-3", "CX-5", "CX-9", "MX-5"],
    # Mitsubishi
    "mitsubishi": ["Lancer", "Outlander", "Pajero", "ASX", "Eclipse Cross"],
    # Subaru
    "subaru": ["Impreza", "Legacy", "Outback", "Forester", "XV", "Ascent", "BRZ"],
    # Suzuki
    "suzuki": ["Swift", "SX4", "Vitara", "Grand Vitara", "Jimny", "S-Cross"],
    # Hyundai
    "hyundai": ["Solaris", "Elantra", "Sonata", "Tucson", "Santa Fe", "Palisade", "Kona", "Nexo", "IONIQ"],
    # Kia
    "kia": ["Rio", "Ceed", "Cerato", "Optima", "Sportage", "Sorento", "Telluride", "Soul", "Niro", "EV6"],
    # Renault
    "renault": ["Logan", "Sandero", "Duster", "Kaptur", "Koleos", "Megane", "Fluence", "Scenic", "Arkana"],
    # Peugeot
    "peugeot": ["208", "308", "408", "508", "2008", "3008", "5008", "Partner"],
    # Citroen
    "citroen": ["C3", "C4", "C5", "Berlingo", "C4 Cactus", "C4 Picasso"],
    # Skoda
    "skoda": ["Fabia", "Rapid", "Octavia", "Superb", "Kamiq", "Karoq", "Kodiaq", "Enyaq"],
    # Ford
    "ford": ["Fiesta", "Focus", "Mondeo", "Kuga", "Edge", "Explorer", "Mustang", "Ranger", "EcoSport"],
    # Chevrolet
    "chevrolet": ["Aveo", "Cruze", "Malibu", "Equinox", "Traverse", "Tahoe", "Camaro", "Corvette"],
    # Fiat
    "fiat": ["500", "Panda", "Tipo", "Bravo", "Doblo", "Ducato"],
    # BelGee (популярные в Беларуси)
    "belgee": ["X50", "X55", "X60", "X70", "X80"],
    # LADA
    "lada": ["Granta", "Vesta", "Largus", "XRAY", "Niva", "4x4"],
    # Geely
    "geely": ["Coolray", "Atlas", "Monjaro", "Tugella", "Emgrand", "Geometry C"],
    # Chery
    "chery": ["Tiggo 2", "Tiggo 4", "Tiggo 7", "Tiggo 8", "Exeed TX", "Exeed VX"],
    # BYD
    "byd": ["F3", "F5", "F6", "S6", "Tang", "Song", "Yuan", "Han", "Atto 3"],
    # Haval
    "haval": ["H2", "H6", "H9", "Jolion", "Dargo", "F7", "F7x"],
    # Great Wall
    "greatwall": ["Hover", "Wingle", "Steed", "Poer", "Tank 300", "Tank 500"],
    # Dongfeng
    "dongfeng": ["AX7", "T5", "SX6", "Fengon", "Mengshi"],
    # FAW
    "faw": ["Besturn", "Oley", "Vita", "V2", "V5"],
    # Changan
    "changan": ["CS35", "CS55", "CS75", "CS95", "UNI-T", "UNI-K", "Eado"],
}
