#!/usr/bin/env python3
"""
Telegram Userbot - Автоматический ответчик для архивных чатов Telegram
Multi-account версия с поддержкой уникальных персон
"""

import asyncio
import sys
import os
import random
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

# Устанавливаем кодировку UTF-8 для Windows консоли
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from bot.browser import UndetectedBrowserManager
from bot.telegram import UndetectedTelegramHandler
from utils.logger import get_logger, setup_logger
from config import APP_CONFIG, TELEGRAM_SITE_CONFIG
from account_manager import AccountManager
from selenium.webdriver.common.by import By

# Инициализируем логгер
logger = setup_logger("main")
logger.info("Telegram Userbot - Автоматический ответчик загружен")

# Глобальный менеджер аккаунтов
account_manager = AccountManager()

# Словарь запущенных ботов для динамического добавления
running_bots: Dict[str, 'TelegramArchiveBot'] = {}


class TelegramArchiveBot:
    """Бот для автоматических ответов в архивных чатах Telegram"""
    
    def __init__(self, account: Dict):
        self.account = account
        self.account_id = account['id']
        self.account_name = account['name']
        
        logger.info(f"[{self.account_name}] Инициализация бота...")
        
        # Получаем путь к профилю и кастомный промпт
        profile_path = account_manager.get_profile_path(account)
        custom_prompt = account_manager.get_system_prompt(account)
        
        self.browser_manager = UndetectedBrowserManager(profile_dir=profile_path)
        self.site_handler = None
        self.is_running = False
        self.ai_model = None
        self.custom_prompt = custom_prompt
        
        logger.info(f"[{self.account_name}] Бот инициализирован для работы с Telegram")
    
    async def check_telegram_auth(self, wait_for_user: bool = True) -> bool:
        """
        Проверка авторизации в Telegram
        
        Args:
            wait_for_user: Ждать подтверждения от пользователя
        """
        try:
            logger.info(f"[{self.account_name}] 🔐 Проверка авторизации в Telegram...")
            
            # Открываем Telegram
            await self.browser_manager.navigate_to_site(TELEGRAM_SITE_CONFIG["url"])
            await asyncio.sleep(3)
            
            # Проверяем наличие элементов авторизации
            driver = self.browser_manager.driver
            auth_indicators = [
                ".sidebar",
                ".chatlist",
                "main",
            ]
            
            is_authorized = False
            for selector in auth_indicators:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        is_authorized = True
                        break
                except:
                    continue
            
            # Если не авторизован
            if not is_authorized:
                logger.info(f"[{self.account_name}] ⚠️ Telegram не авторизован. Браузер открыт для авторизации...")
                logger.info(f"[{self.account_name}] 🌐 Пожалуйста, авторизуйтесь в открывшемся браузере")
                
                if wait_for_user:
                    # Ждем авторизации БЕЗ ограничения времени
                    print(f"\n[{self.account_name}] ⏳ Ожидание авторизации... (проверка каждые 5 секунд)")
                    
                    while True:
                        await asyncio.sleep(5)
                    
                        # Проверяем снова
                        for selector in auth_indicators:
                            try:
                                element = driver.find_element(By.CSS_SELECTOR, selector)
                                if element and element.is_displayed():
                                    is_authorized = True
                                    break
                            except:
                                continue
                        
                        if is_authorized:
                            break
                        print(f"[{self.account_name}] ⏳ Всё ещё ожидаю авторизации...")
            
            if is_authorized:
                logger.info(f"[{self.account_name}] ✅ Telegram авторизован!")
                
                if wait_for_user:
                    # Запрашиваем подтверждение в консоли
                    print("\n" + "="*60)
                    print(f"[{self.account_name}] ✅ Авторизация в Telegram обнаружена!")
                    print(f"Персона: {self.account['persona']['name']} из {self.account['persona']['city']}")
                    print("="*60)
                    
                    while True:
                        response = input(f"\n[{self.account_name}] Авторизовали? (y/n): ").strip().lower()
                        if response == 'y':
                            logger.info(f"[{self.account_name}] ✅ Пользователь подтвердил авторизацию")
                            # Помечаем аккаунт как авторизованный
                            account_manager.mark_as_authorized(self.account_id)
                            return True
                        elif response == 'n':
                            logger.warning(f"[{self.account_name}] ⚠️ Пользователь не подтвердил авторизацию")
                            return False
                        else:
                            print("❌ Пожалуйста, введите 'y' или 'n'")
                else:
                    return True
            else:
                logger.error(f"[{self.account_name}] ❌ Авторизация не выполнена")
                return False
                
        except Exception as e:
            logger.error(f"[{self.account_name}] ❌ Ошибка при проверке авторизации: {e}")
            return False
    
    async def start(self, check_auth: bool = True) -> None:
        """Запуск бота"""
        try:
            logger.info(f"[{self.account_name}] 🚀 Запуск {APP_CONFIG['name']} v{APP_CONFIG['version']}...")
            
            # Запускаем браузер
            logger.info(f"[{self.account_name}] 🌐 Запуск браузера...")
            await self.browser_manager.start()
            logger.info(f"[{self.account_name}] ✅ Браузер запущен")
            
            # Проверяем авторизацию если требуется
            if check_auth:
                auth_result = await self.check_telegram_auth(wait_for_user=True)
            if not auth_result:
                    logger.error(f"[{self.account_name}] ❌ Авторизация не подтверждена. Завершаю работу.")
                    await self.browser_manager.close()
                    return
            else:
                # Просто переходим на Telegram без проверки
                await self.browser_manager.navigate_to_site(TELEGRAM_SITE_CONFIG["url"])
                await asyncio.sleep(3)
            
            # Переходим на Telegram
            logger.info(f"[{self.account_name}] 📱 Переход на Telegram...")
            await self.browser_manager.navigate_to_site(TELEGRAM_SITE_CONFIG["url"])
            logger.info(f"[{self.account_name}] ✅ Telegram загружен")
            
            # Создаем обработчик для Telegram
            logger.info(f"[{self.account_name}] 🔧 Создание обработчика для Telegram...")
            self.site_handler = UndetectedTelegramHandler(self.browser_manager.driver, TELEGRAM_SITE_CONFIG)
            logger.info(f"[{self.account_name}] ✅ Обработчик создан")
            
            # Загружаем AI модель
            await self.load_ai_model()
            
            # Устанавливаем флаг запуска
            self.is_running = True
            logger.info(f"[{self.account_name}] ✅ Бот готов к работе!")
            
        except Exception as e:
            logger.error(f"[{self.account_name}] ❌ Ошибка при запуске бота: {e}")
            raise
    
    async def load_ai_model(self) -> None:
        """Загрузка AI модели с кастомным промптом"""
        try:
            logger.info(f"[{self.account_name}] 🤖 Загрузка AI модели...")
            
            from chat.ai import AIModel
            
            # Передаем кастомный промпт в модель
            self.ai_model = AIModel(custom_system_prompt=self.custom_prompt)
            
            if self.ai_model.load_model():
                logger.info(f"[{self.account_name}] ✅ AI модель загружена успешно")
                logger.info(f"[{self.account_name}] 👤 Персона: {self.account['persona']['name']} ({self.account['persona']['character']['type']})")
            else:
                logger.error(f"[{self.account_name}] ❌ Не удалось загрузить AI модель")
                raise Exception("Ошибка загрузки AI модели")
                
        except Exception as e:
            logger.error(f"[{self.account_name}] ❌ Ошибка при загрузке AI модели: {e}")
            raise
    
    async def stop(self) -> None:
        """Остановка бота"""
        try:
            logger.info(f"[{self.account_name}] 🛑 Остановка бота...")
            self.is_running = False
            
            if self.browser_manager:
                await self.browser_manager.close()
            
            logger.info(f"[{self.account_name}] ✅ Бот остановлен")
            
        except Exception as e:
            logger.error(f"[{self.account_name}] ❌ Ошибка при остановке бота: {e}")
    
    async def auto_reply_loop(self) -> None:
        """Основной цикл автоматических ответов"""
        if not self.is_running:
            logger.warning(f"[{self.account_name}] ⚠️ Бот не запущен")
            return

        logger.info(f"[{self.account_name}] 🔄 Запуск основного цикла автоответов...")
        
        # Открываем архив
        logger.info(f"[{self.account_name}] 📁 Открытие архива чатов...")
        archive_opened = await self.site_handler.open_archive_folder()
        
        if not archive_opened:
            logger.error(f"[{self.account_name}] ❌ Не удалось открыть архив, завершаю работу")
            return
        
        logger.info(f"[{self.account_name}] ✅ Архив открыт, начинаю мониторинг...")
        
        iteration = 0
        
        while self.is_running:
            try:
                iteration += 1
                logger.info(f"[{self.account_name}] 🔄 Поиск непрочитанных #{iteration}")
                
                # Получаем список архивных чатов с непрочитанными
                unread_chats = await self.site_handler.get_archived_chats_with_unread()
                
                if not unread_chats:
                    logger.info(f"[{self.account_name}] 📭 Нет непрочитанных сообщений в архиве")
                    wait_time = random.randint(10, 30)
                    logger.info(f"[{self.account_name}] ⏳ Жду {wait_time} секунд...")
                    await asyncio.sleep(wait_time)
                    continue
                
                # Обрабатываем первый чат с непрочитанными
                chat = unread_chats[0]
                logger.info(f"[{self.account_name}] 📬 Обработка чата: {chat['name']} ({chat['unread_count']} непрочитанных)")
                
                # Открываем чат
                success = await self.site_handler.select_chat_by_name(chat['name'])
                if not success:
                    logger.error(f"[{self.account_name}] ❌ Ошибка при открытии чата: {chat['name']}")
                    await self.site_handler.exit_current_chat()
                    continue
                
                # Получаем историю сообщений
                messages = await self.site_handler.get_recent_messages(max_messages=30)
                
                if not messages:
                    logger.warning(f"[{self.account_name}] ⚠️ Не удалось загрузить историю сообщений")
                    await self.site_handler.exit_current_chat()
                    continue
                
                logger.info(f"[{self.account_name}] ✅ Загружено {len(messages)} сообщений")
                
                # Получаем непрочитанные входящие
                unread_messages = await self.site_handler.get_unread_messages_in_current_chat()
                
                if not unread_messages:
                    logger.info(f"[{self.account_name}] ℹ️ Непрочитанных входящих не найдено")
                    await self.site_handler.exit_current_chat()
                    continue
                
                # Генерируем ответ через AI
                last_message_text = messages[-1]['text'] if messages else ""
                logger.info(f"[{self.account_name}] 🤖 Генерация ответа через AI...")
                response = await self.ai_model.generate_response(messages, last_message_text)
                
                if response is None:
                    logger.info(f"[{self.account_name}] 🚫 AI решил не отвечать")
                    await self.site_handler.exit_current_chat()
                    await asyncio.sleep(random.randint(3, 10))
                    continue
                
                if not response or response.startswith("❌"):
                    logger.warning(f"[{self.account_name}] ⚠️ AI не смог сгенерировать ответ")
                    await self.site_handler.exit_current_chat()
                    continue
                
                logger.info(f"[{self.account_name}] 💬 Ответ: {response}")
                
                # Отправляем ответ
                send_success = await self.site_handler.send_message(response)
                
                if send_success:
                    logger.info(f"[{self.account_name}] ✅ Ответ отправлен")
                else:
                    logger.warning(f"[{self.account_name}] ⚠️ Не удалось отправить ответ")
                
                # Выходим из чата
                await self.site_handler.exit_current_chat()
                
                # Пауза
                wait_time = random.randint(3, 15)
                logger.info(f"[{self.account_name}] ⏳ Пауза {wait_time} секунд...")
                await asyncio.sleep(wait_time)
                
            except KeyboardInterrupt:
                logger.info(f"[{self.account_name}] ⚠️ Получен сигнал прерывания")
                break
            except Exception as e:
                logger.error(f"[{self.account_name}] ❌ Ошибка в цикле автоответов: {e}")
                try:
                    await self.site_handler.exit_current_chat()
                except:
                    pass
                await asyncio.sleep(30)


def show_main_menu():
    """Показать главное меню"""
    print("\n" + "="*60)
    print(f"🤖 {APP_CONFIG['name']} v{APP_CONFIG['version']}")
    print("="*60)
    print("1. Запустить один аккаунт")
    print("2. Запустить все авторизованные аккаунты")
    print("3. Добавить новый аккаунт")
    print("4. Управление аккаунтами")
    print("5. Выход")
    print("="*60)


async def run_single_account():
    """Запуск одного выбранного аккаунта"""
    accounts = account_manager.get_authorized_accounts()
    
    if not accounts:
        print("\n❌ Нет авторизованных аккаунтов!")
        print("Сначала добавьте и авторизуйте аккаунт через меню 'Добавить новый аккаунт'.")
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\n📋 Выберите аккаунт для запуска:")
    print("="*60)
    for i, acc in enumerate(accounts, 1):
        persona = acc['persona']
        print(f"{i}. {acc['name']} - {persona['name']} из {persona['city']}")
        print(f"   Характер: {persona['character']['type']}, Авторизован: {acc.get('auth_date', 'N/A')}")
    print("="*60)
    
    try:
        choice = int(input("\nВведите номер аккаунта: ")) - 1
        if 0 <= choice < len(accounts):
            account = accounts[choice]
            print(f"\n✅ Запуск аккаунта: {account['name']}")
            
            bot = TelegramArchiveBot(account)
            
            try:
                await bot.start(check_auth=False)  # Не проверяем авторизацию, уже авторизован
                await bot.auto_reply_loop()
            except KeyboardInterrupt:
                print(f"\n⚠️ [{account['name']}] Прерывание работы...")
            finally:
                await bot.stop()
        else:
            print("❌ Неверный номер")
    except ValueError:
        print("❌ Введите число")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске аккаунта: {e}")
    
    input("\nНажмите Enter для продолжения...")


async def run_all_authorized_accounts():
    """Запуск всех авторизованных аккаунтов параллельно с поддержкой динамического добавления"""
    accounts = account_manager.get_authorized_accounts()
    
    if not accounts:
        print("\n❌ Нет авторизованных аккаунтов!")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\n✅ Найдено авторизованных аккаунтов: {len(accounts)}")
    for acc in accounts:
        persona = acc['persona']
        print(f"   - {acc['name']}: {persona['name']} из {persona['city']}")
    
    print("\n💡 Система поддерживает динамическое добавление аккаунтов!")
    print("   Вы можете добавлять новые аккаунты через другой терминал,")
    print("   и они автоматически запустятся в течение 30 секунд.")
    
    # Флаг для остановки мониторинга
    monitoring_active = True
    
    # Создаем ботов для начальных аккаунтов
    for account in accounts:
        bot = TelegramArchiveBot(account)
        running_bots[account['id']] = bot
    
    # Функция запуска одного бота
    async def run_bot(bot):
        try:
            await bot.start(check_auth=False)
            await bot.auto_reply_loop()
        except Exception as e:
            logger.error(f"[{bot.account_name}] ❌ Ошибка: {e}")
        finally:
            await bot.stop()
            if bot.account_id in running_bots:
                del running_bots[bot.account_id]
    
    # Фоновая задача для мониторинга новых аккаунтов
    async def monitor_new_accounts():
        """Мониторинг и автоматический запуск новых авторизованных аккаунтов"""
        logger.info("🔍 Запущен мониторинг новых аккаунтов")
        
        while monitoring_active:
            try:
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
                
                if not monitoring_active:
                    break
                
                # Перезагружаем список аккаунтов
                account_manager.load_accounts()
                current_accounts = account_manager.get_authorized_accounts()
                
                # Ищем новые аккаунты (которых еще нет в running_bots)
                for account in current_accounts:
                    if account['id'] not in running_bots:
                        logger.info(f"🆕 Обнаружен новый авторизованный аккаунт: {account['name']}")
                        print(f"\n🆕 Автоматический запуск нового аккаунта: {account['name']}")
                        
                        # Создаем и запускаем нового бота
                        new_bot = TelegramArchiveBot(account)
                        running_bots[account['id']] = new_bot
                        
                        # Запускаем бота как отдельную задачу
                        asyncio.create_task(run_bot(new_bot))
                
                # Проверяем отключенные аккаунты
                current_account_ids = {acc['id'] for acc in current_accounts}
                for bot_id in list(running_bots.keys()):
                    if bot_id not in current_account_ids:
                        logger.info(f"⏸️ Аккаунт {bot_id} был отключен или удален")
                        bot = running_bots.get(bot_id)
                        if bot:
                            bot.is_running = False  # Останавливаем цикл бота
                
            except Exception as e:
                logger.error(f"❌ Ошибка в мониторинге новых аккаунтов: {e}")
    
    try:
        # Запускаем всех ботов и мониторинг параллельно
        print("\n🚀 Запуск всех ботов и мониторинга...")
        
        # Создаем задачи для всех ботов
        bot_tasks = [run_bot(bot) for bot in running_bots.values()]
        
        # Добавляем задачу мониторинга
        monitor_task = asyncio.create_task(monitor_new_accounts())
        
        # Запускаем все вместе
        await asyncio.gather(*bot_tasks)
        
    except KeyboardInterrupt:
        print("\n⚠️ Прерывание работы всех ботов...")
        monitoring_active = False
        
        for bot in list(running_bots.values()):
            try:
                await bot.stop()
            except:
                pass
    finally:
        monitoring_active = False
        running_bots.clear()
    
    input("\nНажмите Enter для продолжения...")


async def add_new_account():
    """Добавление нового аккаунта"""
    print("\n" + "="*60)
    print("➕ ДОБАВЛЕНИЕ НОВОГО АККАУНТА")
    print("="*60)
    
    name = input("Введите имя аккаунта (для идентификации): ").strip()
    if not name:
        print("❌ Имя не может быть пустым")
        input("\nНажмите Enter для продолжения...")
        return
    
    # Проверяем, не существует ли уже
    if account_manager.get_account_by_name(name):
        print(f"❌ Аккаунт с именем '{name}' уже существует")
        input("\nНажмите Enter для продолжения...")
        return
    
    # Создаем аккаунт
    print("\n🎲 Генерация уникальной персоны...")
    account = account_manager.add_account(name)
    
    persona = account['persona']
    print(f"\n✅ Аккаунт создан!")
    print(f"ID: {account['id']}")
    print(f"Персона: {persona['name']}, {persona['age']} лет")
    print(f"Город: {persona['city']}")
    print(f"Характер: {persona['character']['type']} - {persona['character']['description']}")
    print(f"Хобби: {', '.join(persona['hobbies'])}")
    
    # Запускаем авторизацию
    print(f"\n🌐 Открываю браузер для авторизации аккаунта '{name}'...")
    print("⚠️ Авторизуйтесь в открывшемся окне браузера")
    
    bot = TelegramArchiveBot(account)
    
    try:
        await bot.start(check_auth=True)  # Проверяем и ждем авторизации
        print(f"\n✅ Аккаунт '{name}' успешно авторизован и готов к работе!")
    except Exception as e:
        print(f"\n❌ Ошибка при авторизации: {e}")
        print("⚠️ Аккаунт создан, но не авторизован. Вы можете переавторизовать его позже через меню управления.")
    finally:
        await bot.stop()
    
    input("\nНажмите Enter для продолжения...")


def manage_accounts():
    """Меню управления аккаунтами"""
    while True:
        print("\n" + "="*60)
        print("⚙️ УПРАВЛЕНИЕ АККАУНТАМИ")
        print("="*60)
        print("1. Просмотреть все аккаунты")
        print("2. Просмотреть детали аккаунта")
        print("3. Удалить аккаунт")
        print("4. Включить/выключить аккаунт")
        print("5. Переавторизовать аккаунт")
        print("6. Назад")
        print("="*60)
        
        choice = input("\nВыберите действие (1-6): ").strip()
        
        if choice == "1":
            # Просмотр всех аккаунтов
            accounts = account_manager.get_all_accounts()
            if not accounts:
                print("\n❌ Нет аккаунтов")
            else:
                print("\n📋 Список всех аккаунтов:")
                print("="*60)
                for i, acc in enumerate(accounts, 1):
                    auth_status = "✅ Авторизован" if acc.get("authorized") else "❌ Не авторизован"
                    enabled_status = "✅ Включен" if acc.get("enabled", True) else "⏸️ Выключен"
                    persona = acc['persona']
                    print(f"{i}. {acc['name']} (ID: {acc['id']})")
                    print(f"   Статус: {auth_status}, {enabled_status}")
                    print(f"   Персона: {persona['name']} из {persona['city']}")
                    print(f"   Создан: {acc.get('created_date', 'N/A')}")
                    print()
            input("Нажмите Enter для продолжения...")
        
        elif choice == "2":
            # Детали аккаунта
            accounts = account_manager.get_all_accounts()
            if not accounts:
                print("\n❌ Нет аккаунтов")
                input("Нажмите Enter для продолжения...")
                continue
            
            print("\n📋 Выберите аккаунт:")
            for i, acc in enumerate(accounts, 1):
                print(f"{i}. {acc['name']}")
            
            try:
                idx = int(input("\nВведите номер: ")) - 1
                if 0 <= idx < len(accounts):
                    account = accounts[idx]
                    print("\n" + "="*60)
                    print(account_manager.get_account_info_str(account))
                    print("="*60)
                else:
                    print("❌ Неверный номер")
            except ValueError:
                print("❌ Введите число")
            input("\nНажмите Enter для продолжения...")
        
        elif choice == "3":
            # Удаление аккаунта
            accounts = account_manager.get_all_accounts()
            if not accounts:
                print("\n❌ Нет аккаунтов для удаления")
                input("Нажмите Enter для продолжения...")
                continue
            
            print("\n📋 Выберите аккаунт для удаления:")
            for i, acc in enumerate(accounts, 1):
                print(f"{i}. {acc['name']}")
            
            try:
                idx = int(input("\nВведите номер: ")) - 1
                if 0 <= idx < len(accounts):
                    account = accounts[idx]
                    confirm = input(f"⚠️ Удалить аккаунт '{account['name']}'? (y/n): ").strip().lower()
                    if confirm == 'y':
                        account_manager.remove_account(account['id'])
                        print(f"✅ Аккаунт '{account['name']}' удален")
                    else:
                        print("❌ Отменено")
                else:
                    print("❌ Неверный номер")
            except ValueError:
                print("❌ Введите число")
            input("\nНажмите Enter для продолжения...")
        
        elif choice == "4":
            # Включить/выключить аккаунт
            accounts = account_manager.get_all_accounts()
            if not accounts:
                print("\n❌ Нет аккаунтов")
                input("Нажмите Enter для продолжения...")
                continue
            
            print("\n📋 Выберите аккаунт:")
            for i, acc in enumerate(accounts, 1):
                status = "✅ Включен" if acc.get("enabled", True) else "⏸️ Выключен"
                print(f"{i}. {acc['name']} - {status}")
            
            try:
                idx = int(input("\nВведите номер: ")) - 1
                if 0 <= idx < len(accounts):
                    account = accounts[idx]
                    new_status = account_manager.toggle_enabled(account['id'])
                    status_text = "включен" if new_status else "выключен"
                    print(f"✅ Аккаунт '{account['name']}' {status_text}")
                else:
                    print("❌ Неверный номер")
            except ValueError:
                print("❌ Введите число")
            input("\nНажмите Enter для продолжения...")
        
        elif choice == "5":
            # Переавторизация
            accounts = account_manager.get_all_accounts()
            if not accounts:
                print("\n❌ Нет аккаунтов")
                input("Нажмите Enter для продолжения...")
                continue
            
            print("\n📋 Выберите аккаунт для переавторизации:")
            for i, acc in enumerate(accounts, 1):
                print(f"{i}. {acc['name']}")
            
            try:
                idx = int(input("\nВведите номер: ")) - 1
                if 0 <= idx < len(accounts):
                    account = accounts[idx]
                    print(f"\n🌐 Открываю браузер для переавторизации '{account['name']}'...")
                    
                    # Сбрасываем статус авторизации
                    account_manager.mark_as_unauthorized(account['id'])
                    
                    # Запускаем авторизацию
                    bot = TelegramArchiveBot(account)
                    try:
                        asyncio.run(bot.start(check_auth=True))
                        print(f"✅ Аккаунт '{account['name']}' переавторизован")
                    except Exception as e:
                        print(f"❌ Ошибка: {e}")
                    finally:
                        asyncio.run(bot.stop())
                else:
                    print("❌ Неверный номер")
            except ValueError:
                print("❌ Введите число")
            input("\nНажмите Enter для продолжения...")
        
        elif choice == "6":
            break
        
        else:
            print("❌ Неверный выбор")
            input("Нажмите Enter для продолжения...")


async def main():
    """Главная функция"""
    logger.info("🚀 Запуск главной функции...")
    
    while True:
        show_main_menu()
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == "1":
            await run_single_account()
        
        elif choice == "2":
            await run_all_authorized_accounts()
        
        elif choice == "3":
            await add_new_account()
        
        elif choice == "4":
            manage_accounts()
        
        elif choice == "5":
            print("\n👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
            input("\nНажмите Enter для продолжения...")


if __name__ == "__main__":
    logger.info("🎬 Запуск скрипта...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Программа прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
