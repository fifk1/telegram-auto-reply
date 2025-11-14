"""
Адаптер для работы с Telegram Web через undetected-chromedriver
"""

import time
from typing import List, Dict, Optional, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from config import (
    CHAT_SELECTORS, MESSAGE_SELECTORS, 
    HISTORY_SELECTORS, TELEGRAM_CONFIG, ARCHIVE_SELECTORS, TELEGRAM_SITE_CONFIG
)
from bot.base_handler import BaseSiteHandler
from utils.logger import get_logger

logger = get_logger("undetected_telegram")


class UndetectedTelegramHandler(BaseSiteHandler):
    """Класс для работы с Telegram Web через undetected-chromedriver"""
    
    def __init__(self, driver, site_config=None):
        # Если site_config не передан, используем конфигурацию по умолчанию
        if site_config is None:
            site_config = TELEGRAM_SITE_CONFIG
        
        super().__init__(driver, site_config)
        self.wait = WebDriverWait(driver, TELEGRAM_CONFIG["wait_for_selector_timeout"] / 1000)
        self._archive_opened = False  # Флаг состояния архива
        self._element_cache = {}  # Кэш для элементов
        self._cache_timestamp = 0
        self._cache_ttl = 30  # TTL кэша в секундах
    
    def _find_element_cached(self, selectors: List[str], cache_key: str = None) -> Optional[Any]:
        """Поиск элемента с кэшированием"""
        if cache_key and cache_key in self._element_cache:
            element, timestamp = self._element_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                try:
                    # Проверяем, что элемент все еще существует и видим
                    if element and element.is_displayed():
                        return element
                except:
                    # Элемент больше не существует, удаляем из кэша
                    del self._element_cache[cache_key]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    if cache_key:
                        self._element_cache[cache_key] = (element, time.time())
                    return element
            except NoSuchElementException:
                continue
        return None
            
    def _clear_cache(self):
        """Очистка кэша элементов"""
        self._element_cache.clear()
        self._cache_timestamp = time.time()
    
    async def get_current_chat_info(self) -> Dict[str, Any]:
        """Получение информации о текущем чате"""
        try:
            # Ищем название чата
            chat_name = "Неизвестный чат"
            chat_selectors = [
                ".chat-info .peer-title",
                ".chat-header .peer-title", 
                ".chat-title",
                ".peer-title"
            ]
            
            for selector in chat_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.text:
                        chat_name = element.text.strip()
                        break
                except:
                    continue
            
            return {
                "name": chat_name,
                "url": self.driver.current_url
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о чате: {e}")
            return {"name": "Неизвестный чат", "url": ""}

    async def send_message(self, text: str) -> bool:
        """Отправка сообщения в текущий чат"""
        try:
            # Получаем информацию о чате
            chat_info = await self.get_current_chat_info()
            logger.info(f"💬 Чат: {chat_info['name']}")
            logger.info(f"📤 Отправка сообщения: {text}")
            
            # Ищем поле ввода
            input_element = None
            for selector in MESSAGE_SELECTORS["message_input"]:
                try:
                    input_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if input_element and input_element.is_displayed():
                        logger.info(f"Найдено поле ввода по селектору: {selector}")
                        break
                except NoSuchElementException:
                    continue
            
            if not input_element:
                logger.error("Поле ввода сообщения не найдено")
                return False
            
            # Кликаем и очищаем поле
            input_element.click()
            time.sleep(0.2)
            
            # Полная очистка поля (для contenteditable)
            self.driver.execute_script("arguments[0].innerHTML = '';", input_element)
            self.driver.execute_script("arguments[0].textContent = '';", input_element)
            time.sleep(0.1)
            
            # Вводим текст
            input_element.send_keys(text)
            time.sleep(0.3)
            
            # Ищем кнопку отправки
            send_button = None
            for selector in MESSAGE_SELECTORS["send_button"]:
                try:
                    send_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if send_button and send_button.is_displayed():
                        break
                except NoSuchElementException:
                    continue
            
            if not send_button:
                logger.error("Кнопка отправки не найдена")
                return False
            
            # Отправляем ОДИН раз
            send_button.click()  # Используем обычный клик вместо JavaScript
            time.sleep(0.5)
            
            logger.info("✅ Сообщение отправлено")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            return False
        
    async def get_unread_messages(self) -> List[Dict[str, Any]]:
        """Получение непрочитанных сообщений (алиас для совместимости)"""
        return await self.get_archived_chats_with_unread()
    
    async def get_recent_messages(self, max_messages: int = 30) -> List[Dict[str, Any]]:
        """Получение последних сообщений для контекста (алиас для совместимости)"""
        return await self.get_recent_messages_simple(max_messages)
    
    async def get_archived_chats_with_unread(self, prioritize_old: bool = True) -> List[Dict[str, Any]]:
        """Получает список архивных чатов с непрочитанными сообщениями (оптимизированно)"""
        try:
            logger.info("🔍 Поиск архивных чатов с непрочитанными...")
            
            time.sleep(0.2)
            
            # Сначала ищем только чаты с непрочитанными (быстрее)
            unread_elements = []
            for unread_badge_selector in ARCHIVE_SELECTORS['unread_badge']:
                logger.info(f"🔍 Проверяем селектор: {unread_badge_selector}")
                try:
                    selector = f"{ARCHIVE_SELECTORS['chat_item'][0]}:has({unread_badge_selector})"
                    logger.info(f"🔍 Полный селектор: {selector}")
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"🔍 Найдено элементов: {len(elements)}")
                    unread_elements.extend(elements)
                except Exception as e:
                    logger.warning(f"❌ Ошибка с селектором {unread_badge_selector}: {e}")
                    continue
        
            if not unread_elements:
                return []
        
            # УБИРАЕМ ДУБЛИКАТЫ - это ключевое исправление!
            unique_elements = []
            seen_elements = set()
            for element in unread_elements:
                # Используем уникальный идентификатор элемента (data-peer-id)
                try:
                    peer_id = element.get_attribute('data-peer-id')
                    if peer_id and peer_id not in seen_elements:
                        seen_elements.add(peer_id)
                        unique_elements.append(element)
                except:
                    # Если нет data-peer-id, используем позицию элемента как идентификатор
                    element_id = f"{element.location['x']}_{element.location['y']}_{element.size['width']}_{element.size['height']}"
                    if element_id not in seen_elements:
                        seen_elements.add(element_id)
                        unique_elements.append(element)
        
            logger.info(f"🔍 Уникальных элементов после дедупликации: {len(unique_elements)}")
            
            # НОВОЕ: Сортируем элементы по позиции (старые диалоги внизу)
            if prioritize_old:
                # Сортируем по Y-координате (элементы внизу = старые)
                unique_elements.sort(key=lambda el: el.location['y'], reverse=True)
                logger.info("🔄 Сортировка: приоритет старым диалогам")
            else:
                # Сортируем по Y-координате (элементы сверху = новые)
                unique_elements.sort(key=lambda el: el.location['y'])
                logger.info("🔄 Сортировка: приоритет новым диалогам")
        
            unread_chats = []
            
            for element in unique_elements:
                try:
                    # Получаем имя чата
                    name_element = element.find_element(By.CSS_SELECTOR, ARCHIVE_SELECTORS["chat_name"][0])
                    chat_name = name_element.text.strip()
                    
                    # Проверяем, не заглушен ли чат
                    class_name = element.get_attribute("class") or ""
                    is_muted = "is-muted" in class_name
                    
                    # Получаем количество непрочитанных
                    unread_count = 0
                    for badge_selector in ARCHIVE_SELECTORS["unread_badge"]:
                        try:
                            unread_element = element.find_element(By.CSS_SELECTOR, badge_selector)
                            unread_text = unread_element.text.strip()
                            
                            # Если badge найден и видим, значит есть непрочитанные
                            if unread_element.is_displayed():
                                unread_count = 1
                                break
                        except:
                            continue
                    
                    if unread_count > 0:
                        unread_chats.append({
                            "name": chat_name,
                            "unread_count": unread_count,
                            "is_muted": is_muted
                        })
                        logger.info(f"✅ Найден чат с непрочитанными: {chat_name} ({unread_count}) [muted: {is_muted}]")
                    
                except Exception as e:
                    logger.debug(f"Ошибка при обработке чата: {e}")
                    continue
            
            logger.info(f"✅ Найдено {len(unread_chats)} архивных чатов с непрочитанными")
            return unread_chats
            
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске архивных чатов: {e}")
            return []
        
    async def select_chat_by_name(self, chat_name: str) -> bool:
        """Открывает чат по имени (заново находит элемент)"""
        try:
            logger.info(f"🔍 Поиск чата: {chat_name}")
            
            # Ищем чат по имени
            chat_selector = ARCHIVE_SELECTORS["chat_item"][0]
            chat_elements = self.driver.find_elements(By.CSS_SELECTOR, chat_selector)
            
            for element in chat_elements:
                try:
                    name_element = element.find_element(By.CSS_SELECTOR, ARCHIVE_SELECTORS["chat_name"][0])
                    if name_element.text.strip() == chat_name:
                        element.click()
                        time.sleep(2)
                        logger.info(f"✅ Чат '{chat_name}' открыт")
                        return True
                except:
                    continue
            
            logger.error(f"❌ Чат '{chat_name}' не найден")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка при открытии чата '{chat_name}': {e}")
            return False
    
    async def open_archive_folder(self) -> bool:
        """Открывает папку архивных чатов"""
        try:
            # Проверяем флаг состояния
            if self._archive_opened:
                logger.info("📁 Архив уже открыт, пропускаем")
                return True
            
            logger.info("📁 Открытие архива чатов...")
            
            # Шаг 1: Клик по кнопке меню
            menu_button = self._find_element_cached(ARCHIVE_SELECTORS["menu_button"], "menu_button")
            if not menu_button:
                logger.warning("Кнопка меню не найдена или не видна")
                return False
            
            # Кликаем на кнопку меню
            menu_button.click()
            time.sleep(0.3)
            
            # Шаг 2: Поиск пункта "Archived Chats" в меню
            try:
                menu_items = self.driver.find_elements(By.CSS_SELECTOR, ARCHIVE_SELECTORS["archived_chats_item"][0])
                archived_item = None
                
                for item in menu_items:
                    try:
                        text = item.text
                        if "Archived Chats" in text or "Архивные чаты" in text:
                            archived_item = item
                            break
                    except:
                        continue
                
                if archived_item:
                    archived_item.click()
                    logger.info("✅ Пункт 'Archived Chats' нажат")
                    time.sleep(0.5)
                    self._archive_opened = True
                    return True
                else:
                    logger.warning("Пункт 'Archived Chats' не найден в меню")
                    return False
                    
            except Exception as e:
                logger.error(f"Ошибка при поиске пункта архива: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при открытии архива: {e}")
            return False
            
    async def get_unread_messages_in_current_chat(self) -> List[Dict[str, Any]]:
        """Получение последних входящих сообщений в текущем чате (не все подряд)"""
        try:
            logger.info("Поиск последних входящих сообщений...")
            
            # Ищем контейнер с сообщениями с кэшированием
            messages_container = self._find_element_cached(HISTORY_SELECTORS["message_container"], "messages_container")
            
            if not messages_container:
                logger.warning("Контейнер сообщений не найден")
                return []
    
            # Получаем все сообщения
            message_elements = messages_container.find_elements(By.CSS_SELECTOR, HISTORY_SELECTORS["message_item"][0])
            
            if not message_elements:
                logger.warning("Сообщения не найдены")
                return []
            
            # Ищем последние входящие сообщения (не все подряд)
            incoming_messages = []
            
            # Проходим сообщения с конца (последние сначала)
            for element in reversed(message_elements):
                try:
                    # Проверяем, является ли сообщение входящим
                    is_outgoing = "is-out" in (element.get_attribute("class") or "")
                    is_incoming = "is-in" in (element.get_attribute("class") or "")
                    
                    # Если сообщение входящее, получаем его текст
                    if is_incoming and not is_outgoing:
                        text = ""
                        try:
                            text_element = element.find_element(By.CSS_SELECTOR, HISTORY_SELECTORS["message_text"][0])
                            if text_element:
                                text = text_element.text.strip()
                        except NoSuchElementException:
                            pass
                        
                        if text:
                            incoming_messages.append({
                                'text': text,
                                'is_outgoing': False,
                                'element': element
                            })
                            
                            # Берем только последние 3 входящих сообщения
                            if len(incoming_messages) >= 3:
                                break
                
                except Exception as e:
                    logger.debug(f"Ошибка при обработке сообщения: {e}")
                    continue
            
            # Переворачиваем обратно для правильного порядка
            incoming_messages.reverse()
            
            logger.info(f"✅ Найдено {len(incoming_messages)} последних входящих сообщений")
            return incoming_messages
            
        except Exception as e:
            logger.error(f"Ошибка при поиске входящих сообщений: {e}")
            return []
    
    async def get_recent_messages_simple(self, max_messages: int = 30) -> List[Dict[str, Any]]:
        """Получение последних сообщений для контекста (оптимизированная версия)"""
        try:
            # Ищем контейнер с сообщениями
            messages_container = None
            container_selectors = [
                ".scrollable.scrollable-y",
                ".bubbles",
                ".bubbles-inner"
            ]
            
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            messages_inside = element.find_elements(By.CSS_SELECTOR, ".bubble[data-mid]")
                            if messages_inside:
                                messages_container = element
                                break
                    if messages_container:
                        break
                except:
                    continue
            
            if not messages_container:
                logger.warning("Контейнер сообщений не найден")
                return []
            
            # Умная прокрутка для загрузки нужного количества сообщений
            initial_messages = self.driver.find_elements(By.CSS_SELECTOR, ".bubble[data-mid]")
            current_count = len(initial_messages)
            
            # Прокручиваем до тех пор, пока не загрузим нужное количество или не достигнем начала истории
            max_scroll_attempts = 10
            scroll_attempt = 0
            no_new_messages_count = 0
            
            while current_count < max_messages and scroll_attempt < max_scroll_attempts and no_new_messages_count < 3:
                try:
                    # Получаем текущую позицию прокрутки
                    current_scroll_top = self.driver.execute_script("return arguments[0].scrollTop;", messages_container)
                    container_height = self.driver.execute_script("return arguments[0].clientHeight;", messages_container)
                    
                    # Прокручиваем вверх на 80% высоты контейнера
                    new_scroll_top = current_scroll_top - (container_height * 0.8)
                    self.driver.execute_script("arguments[0].scrollTop = arguments[1];", messages_container, new_scroll_top)
                    
                    # Ждем завершения прокрутки
                    wait_time = 0
                    while wait_time < 3:
                        try:
                            bubbles_inner = self.driver.find_element(By.CSS_SELECTOR, ".bubbles-inner")
                            if "is-scrolling" not in bubbles_inner.get_attribute("class"):
                                break
                        except:
                            pass
                        time.sleep(0.2)
                        wait_time += 0.2
                    
                    time.sleep(0.5)
                    
                    # Проверяем, загрузились ли новые сообщения
                    new_messages = self.driver.find_elements(By.CSS_SELECTOR, ".bubble[data-mid]")
                    new_count = len(new_messages)
                    
                    final_scroll_top = self.driver.execute_script("return arguments[0].scrollTop;", messages_container)
                    
                    if new_count > current_count:
                        current_count = new_count
                        no_new_messages_count = 0
                    elif final_scroll_top >= current_scroll_top - 10:
                        no_new_messages_count += 1
                        if no_new_messages_count >= 3:
                            break
                    
                    scroll_attempt += 1
                        
                except Exception as e:
                    break
            
            # Возвращаемся к последним сообщениям
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", messages_container)
            time.sleep(0.3)
            
            # Получаем все сообщения
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, ".bubble[data-mid]")
            
            if not message_elements:
                logger.warning("Сообщения не найдены")
                return []
            
            # Берем последние сообщения
            recent_elements = message_elements[-max_messages:] if len(message_elements) > max_messages else message_elements
            messages = []
            
            # JavaScript код для массового извлечения данных
            js_extract_script = """
            var messages = [];
            var elements = arguments[0];
            
            for (var i = 0; i < elements.length; i++) {
                var element = elements[i];
                var class_name = element.className || '';
                var data_mid = element.getAttribute('data-mid') || '';
                
                // Пропускаем служебные сообщения
                if (class_name.includes('is-date') || class_name.includes('service')) {
                    continue;
                }
                
                // Определяем направление
                var is_outgoing = class_name.includes('is-out');
                
                // Ищем текст сообщения (исключая цитаты)
                var text = '';
                var messageType = 'text';
                
                // Ищем .translatable-message, но НЕ в .reply
                var messageElement = element.querySelector('.message');
                if (messageElement) {
                    // Ищем .translatable-message внутри .message, но НЕ в .reply
                    var translatableElement = messageElement.querySelector('.translatable-message:not(.reply .translatable-message)');
                    if (translatableElement && translatableElement.textContent && translatableElement.textContent.trim()) {
                        text = translatableElement.textContent.trim();
                    } else {
                        // Если нет .translatable-message, берем весь текст .message, но исключаем .reply и .time
                        var clonedElement = messageElement.cloneNode(true);
                        var replyElements = clonedElement.querySelectorAll('.reply');
                        for (var k = 0; k < replyElements.length; k++) {
                            replyElements[k].remove();
                        }
                        
                        // Удаляем элементы времени
                        var timeElements = clonedElement.querySelectorAll('.time');
                        for (var k = 0; k < timeElements.length; k++) {
                            timeElements[k].remove();
                        }
                        
                        // Получаем текст без цитат и времени
                        text = clonedElement.textContent.trim();
                    }
                }
                
                // Если нет текста, проверяем медиа-сообщения
                if (!text) {
                    var bubbleContent = element.querySelector('.bubble-content');
                    if (bubbleContent) {
                        // Проверяем тип медиа
                        if (bubbleContent.querySelector('.media-sticker-wrapper')) {
                            text = '[СТИКЕР]';
                            messageType = 'sticker';
                        } else if (bubbleContent.querySelector('.media-photo')) {
                            text = '[ФОТО]';
                            messageType = 'photo';
                        } else if (bubbleContent.querySelector('.media-video')) {
                            text = '[ВИДЕО]';
                            messageType = 'video';
                        } else if (bubbleContent.querySelector('audio-element')) {
                            text = '[ГОЛОСОВОЕ СООБЩЕНИЕ]';
                            messageType = 'voice';
                        } else if (bubbleContent.querySelector('.attachment')) {
                            text = '[МЕДИА]';
                            messageType = 'media';
                        }
                    }
                }
                
                // Очистка от лишних пробелов
                if (text) {
                    text = text.replace(/\s+/g, ' ').trim();
                }
                
                // Добавляем сообщение если есть текст
                if (text) {
                    messages.push({
                        text: text,
                        is_outgoing: is_outgoing,
                        data_mid: data_mid,
                        class_name: class_name,
                        message_type: messageType
                    });
                }
            }
            
            return messages;
            """
            
            # Выполняем JavaScript для быстрого извлечения
            extracted_messages = self.driver.execute_script(js_extract_script, recent_elements)
            
            # Конвертируем в нужный формат
            for msg_data in extracted_messages:
                messages.append({
                    'text': msg_data['text'],
                    'is_outgoing': msg_data['is_outgoing'],
                    'data_mid': msg_data['data_mid'],
                    'class_name': msg_data['class_name'],
                    'message_type': msg_data['message_type']
                })
            
            # СОРТИРОВКА И ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
            outgoing_messages = [msg for msg in messages if msg['is_outgoing']]
            incoming_messages = [msg for msg in messages if not msg['is_outgoing']]
            
            # Простое логирование результата
            logger.info(f"✅ Загружено {len(messages)} сообщений для контекста")
            return messages
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке сообщений: {e}")
            return []
    
    async def exit_current_chat(self) -> bool:
        """Выход из текущего чата"""
        try:
            logger.info("Выход из текущего чата...")
            
            # Сбрасываем флаг архива при выходе
            self._archive_opened = False
            
            # Очищаем кэш элементов при выходе из чата
            self._clear_cache()
            
            # Простое решение - нажимаем Escape для выхода из чата
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            
            time.sleep(0.3)  # Ждем выхода
            
            logger.info("✅ Выход из чата выполнен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при выходе из чата: {e}")
            return False








































