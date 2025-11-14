"""
Базовый класс для обработчиков различных сайтов
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from selenium.webdriver.remote.webdriver import WebDriver
from utils.logger import get_logger

logger = get_logger("base_handler")


class BaseSiteHandler(ABC):
    """Базовый класс для обработчиков сайтов"""
    
    def __init__(self, driver: WebDriver, site_config: Dict[str, Any]):
        self.driver = driver
        self.site_config = site_config
        self.selectors = site_config.get("selectors", {})
        self.url = site_config.get("url", "")
        self.name = site_config.get("name", "Unknown")
        logger.info(f"Инициализирован обработчик для {self.name}")
    
    @abstractmethod
    async def send_message(self, text: str) -> bool:
        """Отправка сообщения"""
        pass
    
    @abstractmethod
    async def get_unread_messages(self) -> List[Dict[str, Any]]:
        """Получение непрочитанных сообщений"""
        pass
    
    @abstractmethod
    async def get_recent_messages(self, max_messages: int = 30) -> List[Dict[str, Any]]:
        """Получение последних сообщений для контекста"""
        pass
    
    @abstractmethod
    async def select_chat_by_name(self, chat_name: str) -> bool:
        """Открытие чата по имени"""
        pass
    
    @abstractmethod
    async def exit_current_chat(self) -> bool:
        """Выход из текущего чата"""
        pass
    
    @abstractmethod
    async def open_archive_folder(self) -> bool:
        """Открытие папки архивных чатов"""
        pass
    
    @abstractmethod
    async def get_archived_chats_with_unread(self) -> List[Dict[str, Any]]:
        """Получение архивных чатов с непрочитанными"""
        pass
    
    @abstractmethod
    async def get_unread_messages_in_current_chat(self) -> List[Dict[str, Any]]:
        """Получение непрочитанных сообщений в текущем чате"""
        pass








































