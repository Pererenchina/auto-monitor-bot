"""
Главный файл для запуска бота
"""
import asyncio
import logging
import sys
from bot import dp, bot
from db_manager import init_db
from monitor import MonitorService
from notifications import bot_instance

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция"""
    monitor = None
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await init_db()
        logger.info("База данных инициализирована")
        
        # Создание и запуск сервиса мониторинга
        logger.info("Запуск сервиса мониторинга...")
        monitor = MonitorService()
        monitor.start(interval_minutes=15)  # Проверка каждые 15 минут
        
        # Запускаем первую проверку через небольшую задержку
        async def initial_check():
            await asyncio.sleep(5)  # Даем боту время на запуск
            await monitor.check_ads()
        
        asyncio.create_task(initial_check())
        
        # Запуск бота
        logger.info("Запуск Telegram-бота...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
        if monitor:
            monitor.stop()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        if monitor:
            monitor.stop()
    finally:
        await bot.session.close()
        await bot_instance.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
