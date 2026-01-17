"""
Обработчики команд и callback для бота
"""
# Локальные импорты
from .commands import register_command_handlers
from .callbacks import register_callback_handlers
from .states import register_state_handlers

__all__ = ['register_command_handlers', 'register_callback_handlers', 'register_state_handlers']
