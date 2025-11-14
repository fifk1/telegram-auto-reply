"""
Модуль логирования для Telegram Web Userbot
"""

import logging
import sys
from pathlib import Path
from config import LOGGING_CONFIG


def setup_logger(name: str = "userbot") -> logging.Logger:
    """
    Настройка логгера для приложения
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Если логгер уже настроен, возвращаем его
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
    
    # Форматтер
    formatter = logging.Formatter(LOGGING_CONFIG["format"])
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Показываем DEBUG логи в консоли
    console_handler.setFormatter(formatter)
    
    # Устанавливаем кодировку UTF-8 для консоли
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8')
    
    # Файловый обработчик
    file_handler = logging.FileHandler(
        LOGGING_CONFIG["file"], 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Добавляем обработчики
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "userbot") -> logging.Logger:
    """
    Получить логгер по имени
    
    Args:
        name: Имя логгера
        
    Returns:
        Логгер
    """
    return setup_logger(name)








































