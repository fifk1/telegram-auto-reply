"""
Конфигурация Telegram Userbot - Упрощенная версия только для Telegram
"""

import os
from pathlib import Path

# =============================================================================
# ОСНОВНЫЕ НАСТРОЙКИ
# =============================================================================

# Настройки приложения
APP_CONFIG = {
    "name": "Telegram Userbot",
    "version": "3.0.0",
    "auth_wait_timeout": 300  # 5 минут ожидания авторизации
}

# Настройки браузера
BROWSER_CONFIG = {
    "viewport": {
        "width": 1280,
        "height": 720
    },
    "user_data_dir": None  # Автоматически определяется
}

# Настройки Telegram
TELEGRAM_CONFIG = {
    "url": "https://web.telegram.org/k",
    "wait_for_selector_timeout": 5,
    "page_load_timeout": 15
}

# =============================================================================
# ПУТИ И ФАЙЛЫ
# =============================================================================

# Основные директории
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
CHROME_PROFILE_DIR = DATA_DIR / "chrome_profile"

# Создаем директории если не существуют
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
CHROME_PROFILE_DIR.mkdir(exist_ok=True)

# Файлы
LOG_FILE = LOG_DIR / "userbot.log"
SESSION_FILE = DATA_DIR / "session.json"

# =============================================================================
# CSS СЕЛЕКТОРЫ для Telegram Web K
# =============================================================================

# Селекторы для чатов (Telegram Web K)
CHAT_SELECTORS = {
    "chat_list": [".chatlist-chat"],
    "chat_name": [".peer-title"],
    "last_message_preview": [".dialog-subtitle"],
    "chat_element": [".ListItem"],
    "unread_badge": [
        ".dialog-subtitle-badge.unread",  # Основной селектор
        ".badge.unread",
        "[class*='unread']"
    ],
}

# Селекторы для архивных чатов (Telegram Web K)
ARCHIVE_SELECTORS = {
    "menu_button": ["button.btn-menu-toggle.sidebar-tools-button"],
    "menu_container": [".btn-menu"],
    "archived_chats_item": [".btn-menu-item"],  # Ищем по тексту "Archived Chats"
    "archived_count": [".archived-count"],
    "chat_item": ["a.chatlist-chat[data-peer-id]"],
    "chat_name": [".peer-title"],
    "chat_peer_id": ["data-peer-id"],
    "unread_badge": [
        ".dialog-subtitle-badge.unread",
        ".badge.unread",
        "[class*='unread']"
    ],
    "chat_is_muted": [".is-muted"]
}

# Селекторы для сообщений (Telegram Web K)
MESSAGE_SELECTORS = {
    "message_input": [
        ".input-message-container > .input-message-input[contenteditable='true'][dir='auto'][tabindex='-1']:not(.input-field-input-fake)",
        ".input-message-input[contenteditable='true'][dir='auto'][tabindex='-1']:not(.input-field-input-fake)"
    ],
    "send_button": [
        ".btn-send",
        "button[aria-label='Send']"
    ],
    "messages_container": [".bubbles"],
    "message_text": [".translatable-message", ".message"],
    "message_element": [".bubble"],
    "last_message": [".bubble:last-child"],
    "message_time": [".time"],
    "outgoing_indicator": [".is-out"]
}

# Селекторы для авторизации (Telegram Web K)
AUTH_SELECTORS = {
    "main_container": ["main"],
    "sidebar": [".sidebar"],
    "chatlist_container": [".chatlist", ".chatlist-container", ".sidebar-left"],
    "chat_list": [".chatlist-chat"],
    "input_field": [".input-message-container"],
    "login_phone_input": [".input-field", "input[type='tel']", "input[placeholder*='phone']"],
    "auth_form": [".auth-form", ".login-form", ".qr-login"],
    "qr_code": [".qr-canvas", ".qr-code", ".auth-image"]
}

# Селекторы для истории чата (Telegram Web K)
HISTORY_SELECTORS = {
    "message_container": [".scrollable.scrollable-y", ".bubbles", ".bubbles-inner"],
    "message_item": [".bubble[data-mid]", ".bubble"],
    "message_text": [".translatable-message", ".message"],
    "message_time": [".time"],
    "outgoing_indicator": [".is-out"],
    "incoming_indicator": [".is-in"],
    "message_id": ["[data-mid]", "[data-message-id]", "[data-id]"],
    "message_author": [".message-author", ".peer-title"],
    "text_messages": [".translatable-message", ".message"],
    "media_messages": [".media", ".photo", ".video", ".media-photo"],
    "file_messages": [".file", ".document"],
    "voice_messages": [".voice", ".audio"],
    "sticker_messages": [".sticker", ".media-sticker-wrapper"],
    "reply_messages": [".reply", ".reply-to"],
    "forwarded_messages": [".forwarded"],
    "system_messages": [".system-message", ".service"],
    "load_more": [".backwards-trigger", ".load-more"]
}

# Селекторы для прокрутки
SCROLL_SELECTORS = {
    "scroll_containers": [".bubbles-inner", ".bubbles", ".messages-container", ".chat-container"],
    "chat_hover_targets": [".chatlist-chat", ".ListItem", ".sidebar"],
    "calendar_elements": [".calendar", ".date-picker", ".time-picker"],
    "load_more_triggers": [".backwards-trigger", ".load-more", ".load-older"]
}

# Конфигурация улучшенной прокрутки
IMPROVED_SCROLL_CONFIG = {
    "enable_hover_activation": False,
    "hover_delay": 0.1,
    "use_javascript_scroll": True,
    "use_keyboard_scroll": False,
    "use_mouse_scroll": False,
    "scroll_attempts": 5,
    "scroll_delay": 0.2,
    "max_no_new_messages": 2,
    "load_more_delay": 0.5
}

# =============================================================================
# НАСТРОЙКИ ЛОГИРОВАНИЯ
# =============================================================================

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": str(LOG_FILE),
    "max_size": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5
}

# =============================================================================
# КОНФИГУРАЦИЯ ТЕЛЕГРАМ
# =============================================================================

TELEGRAM_SITE_CONFIG = {
    "name": "Telegram",
    "url": "https://web.telegram.org/k",
    "handler_class": "UndetectedTelegramHandler",
    "selectors": {
        "chat": CHAT_SELECTORS,
        "archive": ARCHIVE_SELECTORS,
        "message": MESSAGE_SELECTORS,
        "history": HISTORY_SELECTORS,
        "auth": AUTH_SELECTORS,
        "scroll": SCROLL_SELECTORS
    }
}

# =============================================================================
# НАСТРОЙКИ AI
# =============================================================================

AI_CONFIG = {
    "enabled": True,
    "provider": "local",
    "model": "local",
    "max_tokens": 150,
    "temperature": 0.7
}
























































