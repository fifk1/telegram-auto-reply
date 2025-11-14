"""
Менеджер аккаунтов для управления несколькими Telegram сессиями
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from persona_generator import PersonaGenerator
from config import DATA_DIR

ACCOUNTS_CONFIG_FILE = DATA_DIR / "accounts.json"


class AccountManager:
    """Менеджер для управления несколькими аккаунтами"""
    
    def __init__(self):
        self.accounts_file = ACCOUNTS_CONFIG_FILE
        self.accounts: List[Dict] = []
        self.persona_generator = PersonaGenerator()
        self.load_accounts()
    
    def load_accounts(self) -> None:
        """Загрузка списка аккаунтов из файла"""
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Поддержка как старого, так и нового формата
                    if isinstance(data, list):
                        self.accounts = data
                    else:
                        self.accounts = []
            except Exception as e:
                print(f"Ошибка загрузки аккаунтов: {e}")
                self.accounts = []
        else:
            self.accounts = []
    
    def save_accounts(self) -> None:
        """Сохранение списка аккаунтов в файл"""
        try:
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения аккаунтов: {e}")
    
    def add_account(self, name: str, gender: Optional[str] = None) -> Dict:
        """
        Добавление нового аккаунта с автогенерацией персоны
        
        Args:
            name: Пользовательское имя аккаунта (для идентификации)
            gender: 'male' или 'female' (опционально)
        
        Returns:
            Созданный аккаунт
        """
        # Генерируем уникальный ID
        account_id = str(uuid.uuid4())[:8]
        
        # Генерируем персону
        persona = self.persona_generator.generate_persona(gender)
        
        # Создаем аккаунт
        account = {
            "id": account_id,
            "name": name,
            "profile_dir": f"chrome_profile_{account_id}",
            "persona": persona,
            "authorized": False,
            "auth_date": None,
            "enabled": True,
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.accounts.append(account)
        self.save_accounts()
        return account
    
    def remove_account(self, account_id: str) -> bool:
        """
        Удаление аккаунта
        
        Args:
            account_id: ID аккаунта
        
        Returns:
            True если удален, False если не найден
        """
        initial_count = len(self.accounts)
        self.accounts = [acc for acc in self.accounts if acc["id"] != account_id]
        
        if len(self.accounts) < initial_count:
            self.save_accounts()
            return True
        return False
    
    def get_all_accounts(self) -> List[Dict]:
        """Получение списка всех аккаунтов"""
        return self.accounts
    
    def get_authorized_accounts(self) -> List[Dict]:
        """Получение только авторизованных аккаунтов"""
        return [acc for acc in self.accounts if acc.get("authorized", False) and acc.get("enabled", True)]
    
    def get_enabled_accounts(self) -> List[Dict]:
        """Получение только включенных аккаунтов"""
        return [acc for acc in self.accounts if acc.get("enabled", True)]
    
    def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """
        Получение аккаунта по ID
        
        Args:
            account_id: ID аккаунта
        
        Returns:
            Аккаунт или None если не найден
        """
        for account in self.accounts:
            if account["id"] == account_id:
                return account
        return None
    
    def get_account_by_name(self, name: str) -> Optional[Dict]:
        """
        Получение аккаунта по имени
        
        Args:
            name: Имя аккаунта
        
        Returns:
            Аккаунт или None если не найден
        """
        for account in self.accounts:
            if account["name"] == name:
                return account
        return None
    
    def mark_as_authorized(self, account_id: str) -> bool:
        """
        Пометить аккаунт как авторизованный
        
        Args:
            account_id: ID аккаунта
        
        Returns:
            True если помечен, False если не найден
        """
        account = self.get_account_by_id(account_id)
        if account:
            account["authorized"] = True
            account["auth_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_accounts()
            return True
        return False
    
    def mark_as_unauthorized(self, account_id: str) -> bool:
        """
        Снять авторизацию с аккаунта
        
        Args:
            account_id: ID аккаунта
        
        Returns:
            True если изменен, False если не найден
        """
        account = self.get_account_by_id(account_id)
        if account:
            account["authorized"] = False
            account["auth_date"] = None
            self.save_accounts()
            return True
        return False
    
    def toggle_enabled(self, account_id: str) -> Optional[bool]:
        """
        Переключить статус enabled аккаунта
        
        Args:
            account_id: ID аккаунта
        
        Returns:
            Новое значение enabled или None если не найден
        """
        account = self.get_account_by_id(account_id)
        if account:
            account["enabled"] = not account.get("enabled", True)
            self.save_accounts()
            return account["enabled"]
        return None
    
    def get_profile_path(self, account: Dict) -> Path:
        """
        Получение пути к профилю Chrome для аккаунта
        
        Args:
            account: Словарь с данными аккаунта
        
        Returns:
            Path к профилю
        """
        profile_dir = account.get("profile_dir", f"chrome_profile_{account['id']}")
        profile_path = DATA_DIR / profile_dir
        
        # Создаем директорию если не существует
        profile_path.mkdir(exist_ok=True)
        
        return profile_path
    
    def get_system_prompt(self, account: Dict) -> str:
        """
        Получение системного промпта для аккаунта
        
        Args:
            account: Словарь с данными аккаунта
        
        Returns:
            Системный промпт
        """
        persona = account.get("persona")
        if persona:
            return self.persona_generator.generate_system_prompt(persona)
        else:
            # Fallback на стандартный промпт если персоны нет
            from chat.config import get_system_prompt
            return get_system_prompt()
    
    def get_account_info_str(self, account: Dict) -> str:
        """
        Форматированная информация об аккаунте
        
        Args:
            account: Словарь с данными аккаунта
        
        Returns:
            Строка с информацией
        """
        persona = account.get("persona", {})
        auth_status = "✅ Авторизован" if account.get("authorized") else "❌ Не авторизован"
        enabled_status = "✅ Включен" if account.get("enabled", True) else "❌ Выключен"
        
        info = f"""
Аккаунт: {account['name']} (ID: {account['id']})
Статус: {auth_status}, {enabled_status}
Создан: {account.get('created_date', 'N/A')}
Авторизован: {account.get('auth_date', 'N/A')}

Персона:
  Имя: {persona.get('name', 'N/A')}
  Возраст: {persona.get('age', 'N/A')}
  Город: {persona.get('city', 'N/A')}
  Характер: {persona.get('character', {}).get('type', 'N/A')}
  Хобби: {', '.join(persona.get('hobbies', []))}
"""
        return info.strip()


def test_account_manager():
    """Тестовая функция для проверки менеджера"""
    manager = AccountManager()
    
    print("=== Тест менеджера аккаунтов ===\n")
    
    # Добавляем тестовый аккаунт
    print("1. Добавление аккаунта...")
    account = manager.add_account("test_account_1")
    print(f"✅ Аккаунт создан: {account['name']} (ID: {account['id']})")
    print(f"   Персона: {account['persona']['name']} из {account['persona']['city']}")
    print()
    
    # Получаем все аккаунты
    print("2. Получение всех аккаунтов...")
    all_accounts = manager.get_all_accounts()
    print(f"✅ Всего аккаунтов: {len(all_accounts)}")
    print()
    
    # Помечаем как авторизованный
    print("3. Авторизация аккаунта...")
    manager.mark_as_authorized(account['id'])
    print("✅ Аккаунт помечен как авторизованный")
    print()
    
    # Получаем авторизованные
    print("4. Получение авторизованных аккаунтов...")
    authorized = manager.get_authorized_accounts()
    print(f"✅ Авторизованных аккаунтов: {len(authorized)}")
    print()
    
    # Получаем информацию
    print("5. Информация об аккаунте:")
    info = manager.get_account_info_str(account)
    print(info)
    print()
    
    # Получаем промпт
    print("6. Системный промпт (первые 200 символов):")
    prompt = manager.get_system_prompt(account)
    print(prompt[:200] + "...")


if __name__ == "__main__":
    test_account_manager()

