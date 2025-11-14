"""
Модуль для работы с браузером через undetected-chromedriver
"""

import asyncio
import time
from typing import Optional
from pathlib import Path
import undetected_chromedriver as uc
import platform

try:
    # Доступно только на Windows
    import winreg  # type: ignore
except Exception:  # pragma: no cover
    winreg = None  # type: ignore

from config import (
    BROWSER_CONFIG, TELEGRAM_CONFIG, CHROME_PROFILE_DIR
)
from utils.logger import get_logger

logger = get_logger("undetected_browser")


class UndetectedBrowserManager:
    """Менеджер браузера с использованием undetected-chromedriver"""
    
    def __init__(self, profile_dir: Optional[Path] = None):
        self.driver: Optional[uc.Chrome] = None
        self.is_running = False
        self.profile_dir = profile_dir  # Поддержка кастомного профиля
    
    async def start(self) -> None:
        """Запуск браузера с улучшенной обработкой ошибок"""
        try:
            logger.info("Запуск undetected браузера...")
            
            # Проверяем, не запущен ли уже браузер
            if self.driver and self.is_running:
                logger.info("Браузер уже запущен")
                return
            
            # Настройки Chrome
            options = uc.ChromeOptions()
            
            # Базовые настройки для стабильности
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument(f'--window-size={BROWSER_CONFIG["viewport"]["width"]},{BROWSER_CONFIG["viewport"]["height"]}')
            
            # Настройки для скрытия автоматизации
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-translate')
            options.add_argument('--disable-background-timer-throttling')
            
            # Отключаем индикаторы активности в панели задач
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-background-mode')
            options.add_argument('--disable-component-extensions-with-background-pages')
            options.add_argument('--disable-notifications')
            
            # Настройки для разрешения всплывающих окон и новых вкладок
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-features=TranslateUI')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--metrics-recording-only')
            options.add_argument('--no-report-upload')
            options.add_argument('--disable-hang-monitor')
            options.add_argument('--disable-prompt-on-repost')
            options.add_argument('--disable-domain-reliability')
            options.add_argument('--disable-component-extensions-with-background-pages')
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-features=TranslateUI')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--exclude-switches=enable-automation')
            options.add_argument('--password-store=basic')
            options.add_argument('--use-mock-keychain')
            
            # Настройки профиля
            if self.profile_dir:
                user_data_dir = str(self.profile_dir)
            else:
                user_data_dir = BROWSER_CONFIG.get("user_data_dir", str(CHROME_PROFILE_DIR))
            options.add_argument(f'--user-data-dir={user_data_dir}')
            
            # Дополнительные настройки для стабильности
            options.add_argument('--disable-logging')
            options.add_argument('--disable-gpu-logging')
            options.add_argument('--log-level=3')
            options.add_argument('--silent')
            options.add_argument('--disable-background-mode')
            
            # Таймауты
            options.add_argument('--timeout=30000')
            options.add_argument('--page-load-strategy=normal')
            
            logger.info("Создание драйвера Chrome...")

            # Пытаемся определить основную версию установленного Chrome (важно для совместимости с ChromeDriver)
            version_main_detected: Optional[int] = None

            def get_chrome_major_version() -> Optional[int]:
                # На Windows читаем реестр: HKCU/HKLM Software\\Google\\Chrome\\BLBeacon -> version
                if platform.system() != "Windows" or winreg is None:
                    return None
                registry_paths = [
                    (winreg.HKEY_CURRENT_USER, r"Software\\Google\\Chrome\\BLBeacon"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\\Google\\Chrome\\BLBeacon"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\\WOW6432Node\\Google\\Chrome\\BLBeacon"),
                ]
                for hive, subkey in registry_paths:
                    try:
                        with winreg.OpenKey(hive, subkey) as key:  # type: ignore[attr-defined]
                            version_str, _ = winreg.QueryValueEx(key, "version")  # type: ignore[attr-defined]
                            if isinstance(version_str, str) and version_str:
                                major_str = version_str.split(".")[0]
                                if major_str.isdigit():
                                    return int(major_str)
                    except Exception:
                        continue
                return None

            try:
                version_main_detected = get_chrome_major_version()
                if version_main_detected:
                    logger.info(f"Обнаружена версия Chrome: {version_main_detected}")
                else:
                    logger.info("Не удалось определить версию Chrome через реестр; используем автоопределение")
            except Exception as detect_err:
                logger.warning(f"Ошибка определения версии Chrome: {detect_err}")
                version_main_detected = None
            
            # Создаем драйвер с таймаутом
            try:
                self.driver = uc.Chrome(
                    options=options,
                    version_main=version_main_detected,  # Совместим с установленным Chrome, если удалось определить
                    driver_executable_path=None,  # Автопоиск драйвера
                    browser_executable_path=None,  # Автопоиск браузера
                    headless=False,  # Показываем окно
                    use_subprocess=True,  # Используем подпроцесс
                    debug=False  # Отключаем отладку
                )
                
                # Устанавливаем таймауты
                self.driver.set_page_load_timeout(15)
                self.driver.implicitly_wait(5)
                
                self.is_running = True
                
                # Устанавливаем размер окна
                self.driver.set_window_size(
                    BROWSER_CONFIG["viewport"]["width"], 
                    BROWSER_CONFIG["viewport"]["height"]
                )
                
                # Отключаем фоновые процессы, которые вызывают мигание в панели задач
                try:
                    # Отключаем фокус окна
                    self.driver.execute_script("window.blur();")
                    
                    # Отключаем все фоновые процессы
                    self.driver.execute_script("""
                        // Отключаем все фоновые процессы
                        if (window.chrome && window.chrome.runtime) {
                            window.chrome.runtime.onConnect = null;
                            window.chrome.runtime.onMessage = null;
                        }
                        
                        // Отключаем все таймеры
                        for (let i = 1; i < 10000; i++) {
                            clearTimeout(i);
                            clearInterval(i);
                        }
                    """)
                    
                    logger.info("Фоновые процессы отключены")
                except Exception as e:
                    logger.warning(f"Не удалось отключить фоновые процессы: {e}")
                
                logger.info("Undetected браузер успешно запущен")
                
            except Exception as driver_error:
                logger.error(f"Ошибка создания драйвера: {driver_error}")
                
                # Попробуем альтернативный способ
                logger.info("Пробуем альтернативный способ запуска...")
                
                # Упрощенные настройки
                simple_options = uc.ChromeOptions()
                simple_options.add_argument('--no-sandbox')
                simple_options.add_argument('--disable-dev-shm-usage')
                simple_options.add_argument('--disable-gpu')
                simple_options.add_argument('--disable-blink-features=AutomationControlled')
                simple_options.add_argument('--exclude-switches=enable-automation')
                
                self.driver = uc.Chrome(
                    options=simple_options,
                    version_main=version_main_detected
                )
                self.driver.set_page_load_timeout(15)
                self.driver.implicitly_wait(5)
                self.is_running = True
                
                logger.info("Браузер запущен альтернативным способом")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при запуске браузера: {e}")
            logger.error("Возможные причины:")
            logger.error("1. Chrome не установлен или устарел")
            logger.error("2. Конфликт с другими процессами Chrome")
            logger.error("3. Проблемы с правами доступа")
            logger.error("4. Антивирус блокирует запуск")
            
            # Попробуем закрыть все процессы Chrome
            try:
                import subprocess
                
                if platform.system() == "Windows":
                    subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                                 capture_output=True, check=False)
                    subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], 
                                 capture_output=True, check=False)
                    logger.info("Попытка закрыть все процессы Chrome...")
                    await asyncio.sleep(2)
                    
            except Exception as cleanup_error:
                logger.warning(f"Ошибка при очистке процессов: {cleanup_error}")
            
            raise Exception(f"Не удалось запустить браузер: {e}")
    
    async def navigate_to_telegram(self) -> None:
        """Переход на Telegram Web (для обратной совместимости)"""
        await self.navigate_to_site(TELEGRAM_CONFIG["url"])
    
    async def navigate_to_site(self, url: str) -> None:
        """Переход на указанный сайт с поддержкой вкладок"""
        try:
            if not self.driver:
                raise Exception("Драйвер не инициализирован")
            
            logger.info(f"Переход на сайт: {url}")
            
            # Проверяем, не находимся ли мы уже на этом сайте
            current_url = self.driver.current_url
            if url in current_url or current_url in url:
                logger.info(f"✅ Уже на сайте {url}")
                return
            
            # Открываем новую вкладку для сайта
            self.driver.execute_script("window.open('');")
            
            # Переключаемся на новую вкладку
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # Переходим на сайт
            self.driver.get(url)
            
            # Ждем загрузки страницы
            time.sleep(3)
            logger.info(f"Сайт {url} загружен")
            
        except Exception as e:
            logger.error(f"Ошибка при переходе на сайт {url}: {e}")
            raise
    
    async def switch_to_tab(self, tab_index: int = -1) -> None:
        """Переключение на указанную вкладку"""
        try:
            if not self.driver:
                raise Exception("Драйвер не инициализирован")
            
            handles = self.driver.window_handles
            if not handles:
                raise Exception("Нет доступных вкладок")
            
            # Если tab_index = -1, переключаемся на последнюю вкладку
            if tab_index == -1:
                tab_index = len(handles) - 1
            
            if tab_index >= len(handles):
                raise Exception(f"Вкладка {tab_index} не существует")
            
            self.driver.switch_to.window(handles[tab_index])
            logger.info(f"Переключение на вкладку {tab_index}")
            
        except Exception as e:
            logger.error(f"Ошибка при переключении на вкладку {tab_index}: {e}")
            raise
    
    async def close_other_tabs(self, keep_current: bool = True) -> None:
        """Закрытие всех вкладок кроме текущей"""
        try:
            if not self.driver:
                raise Exception("Драйвер не инициализирован")
            
            handles = self.driver.window_handles
            if len(handles) <= 1:
                return  # Только одна вкладка
            
            current_handle = self.driver.current_window_handle
            
            for handle in handles:
                if handle != current_handle:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
            
            # Возвращаемся на текущую вкладку
            if keep_current:
                self.driver.switch_to.window(current_handle)
            
            logger.info("Остальные вкладки закрыты")
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии вкладок: {e}")
            raise
    
    async def close(self) -> None:
        """Закрытие браузера"""
        try:
            if self.driver and self.is_running:
                # Закрываем браузер
                try:
                    self.driver.quit()
                    self.is_running = False
                    logger.info("Браузер закрыт")
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии драйвера: {e}")
                    # Принудительно устанавливаем флаг
                    self.is_running = False
            
        except Exception as e:
            logger.warning(f"Ошибка при закрытии браузера: {e}")
            self.is_running = False








































