import json
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from valutatrade_hub.core.models import User, Portfolio
from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """
    Singleton для управления JSON-хранилищем данных.
    Обеспечивает потокобезопасный доступ к данным.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Инициализация базы данных (только один раз)"""
        with self._lock:
            if not self._initialized:
                self.settings = SettingsLoader()
                self.data_dir = Path(self.settings.get('data_dir', 'data'))
                self._init_database()
                self._initialized = True
    
    def _init_database(self):
        """Инициализация базы данных и создание необходимых файлов"""
        # Создаем директорию данных
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализируем файлы если их нет
        self._init_file('users.json', [])
        self._init_file('portfolios.json', [])
        self._init_file('rates.json', {
            "pairs": {},
            "last_refresh": datetime.now().isoformat(),
            "source": "Manual"
        })
        self._init_file('exchange_rates.json', [])
        self._init_file('transactions.json', [])
        self._init_file('session.json', {})
        
        print(f"✓ База данных инициализирована в {self.data_dir}")
    
    def _init_file(self, filename: str, default_content: Any):
        """Инициализирует файл с содержимым по умолчанию"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            self._write_json(filepath, default_content)
    
    def _read_json(self, filepath: Path) -> Any:
        """
        Читает JSON файл с обработкой ошибок.
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            Данные из файла или значение по умолчанию
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка чтения файла {filepath}: {e}")
            # Возвращаем значение по умолчанию в зависимости от имени файла
            if filepath.name in ['users.json', 'portfolios.json', 'transactions.json', 'exchange_rates.json']:
                return []
            elif filepath.name == 'rates.json':
                return {"pairs": {}, "last_refresh": "", "source": "Manual"}
            else:
                return {}
    
    def _write_json(self, filepath: Path, data: Any):
        """
        Записывает данные в JSON файл.
        
        Args:
            filepath: Путь к файлу
            data: Данные для записи
        """
        try:
            # Создаем временный файл для атомарной записи
            temp_filepath = filepath.with_suffix('.tmp')
            
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Атомарно заменяем старый файл новым
            temp_filepath.replace(filepath)
            
        except Exception as e:
            print(f"Ошибка записи в файл {filepath}: {e}")
            raise
    
    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ====================
    
    def save_user(self, user: User) -> None:
        """Сохраняет пользователя в базу данных"""
        with self._lock:
            users_data = self._read_json(self.data_dir / 'users.json')
            
            # Преобразуем в список если нужно
            if isinstance(users_data, dict):
                users_data = list(users_data.values())
            
            # Ищем существующего пользователя
            user_index = -1
            for i, user_data in enumerate(users_data):
                if user_data.get('user_id') == user.user_id:
                    user_index = i
                    break
            
            # Обновляем или добавляем пользователя
            user_dict = user.to_dict()
            if user_index >= 0:
                users_data[user_index] = user_dict
            else:
                users_data.append(user_dict)
            
            # Сохраняем
            self._write_json(self.data_dir / 'users.json', users_data)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получает пользователя по ID"""
        users_data = self._read_json(self.data_dir / 'users.json')
        
        if isinstance(users_data, dict):
            users_data = list(users_data.values())
        
        for user_data in users_data:
            if user_data.get('user_id') == user_id:
                try:
                    return User.from_dict(user_data)
                except Exception as e:
                    print(f"Ошибка создания User из данных: {e}")
                    return None
        
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Получает пользователя по имени пользователя"""
        users_data = self._read_json(self.data_dir / 'users.json')
        
        if isinstance(users_data, dict):
            users_data = list(users_data.values())
        
        for user_data in users_data:
            if user_data.get('username') == username:
                try:
                    return User.from_dict(user_data)
                except Exception as e:
                    print(f"Ошибка создания User из данных: {e}")
                    return None
        
        return None
    
    def get_all_users(self) -> List[User]:
        """Получает всех пользователей"""
        users_data = self._read_json(self.data_dir / 'users.json')
        
        if isinstance(users_data, dict):
            users_data = list(users_data.values())
        
        users = []
        for user_data in users_data:
            try:
                users.append(User.from_dict(user_data))
            except Exception as e:
                print(f"Ошибка создания User из данных: {e}")
                continue
        
        return users
    
    def delete_user(self, user_id: int) -> bool:
        """Удаляет пользователя по ID"""
        with self._lock:
            users_data = self._read_json(self.data_dir / 'users.json')
            
            if isinstance(users_data, dict):
                users_data = list(users_data.values())
            
            # Фильтруем пользователей
            original_count = len(users_data)
            users_data = [u for u in users_data if u.get('user_id') != user_id]
            
            if len(users_data) < original_count:
                self._write_json(self.data_dir / 'users.json', users_data)
                return True
            
            return False
    
    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ПОРТФЕЛЯМИ ====================
    
    def save_portfolio(self, portfolio: Portfolio) -> None:
        """Сохраняет портфель в базу данных"""
        with self._lock:
            portfolios_data = self._read_json(self.data_dir / 'portfolios.json')
            
            if isinstance(portfolios_data, dict):
                portfolios_data = list(portfolios_data.values())
            
            # Ищем существующий портфель
            portfolio_index = -1
            for i, portfolio_data in enumerate(portfolios_data):
                if portfolio_data.get('user_id') == portfolio.user_id:
                    portfolio_index = i
                    break
            
            # Обновляем или добавляем портфель
            portfolio_dict = portfolio.to_dict()
            if portfolio_index >= 0:
                portfolios_data[portfolio_index] = portfolio_dict
            else:
                portfolios_data.append(portfolio_dict)
            
            # Сохраняем
            self._write_json(self.data_dir / 'portfolios.json', portfolios_data)
    
    def get_portfolio_by_user_id(self, user_id: int) -> Optional[Portfolio]:
        """Получает портфель пользователя по ID"""
        portfolios_data = self._read_json(self.data_dir / 'portfolios.json')
        
        if isinstance(portfolios_data, dict):
            portfolios_data = list(portfolios_data.values())
        
        for portfolio_data in portfolios_data:
            if portfolio_data.get('user_id') == user_id:
                try:
                    return Portfolio.from_dict(portfolio_data)
                except Exception as e:
                    print(f"Ошибка создания Portfolio из данных: {e}")
                    return None
        
        return None
    
    def get_all_portfolios(self) -> List[Portfolio]:
        """Получает все портфели"""
        portfolios_data = self._read_json(self.data_dir / 'portfolios.json')
        
        if isinstance(portfolios_data, dict):
            portfolios_data = list(portfolios_data.values())
        
        portfolios = []
        for portfolio_data in portfolios_data:
            try:
                portfolios.append(Portfolio.from_dict(portfolio_data))
            except Exception as e:
                print(f"Ошибка создания Portfolio из данных: {e}")
                continue
        
        return portfolios
    
    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С КУРСАМИ ВАЛЮТ ====================
    
    def save_exchange_rates(self, rates: Dict[str, Dict[str, Any]]) -> None:
        """Сохраняет курсы валют в базу данных"""
        with self._lock:
            rates_data = {
                "pairs": rates,
                "last_refresh": datetime.now().isoformat(),
                "source": "ParserService"
            }
            self._write_json(self.data_dir / 'rates.json', rates_data)
    
    def get_exchange_rates(self) -> Dict[str, Dict[str, Any]]:
        """Получает все курсы валют"""
        rates_data = self._read_json(self.data_dir / 'rates.json')
        return rates_data.get('pairs', {})
    
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Получает курс обмена для пары валют"""
        rates = self.get_exchange_rates()
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Прямая пара
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key in rates:
            return rates[rate_key].get('rate')
        
        # Обратная пара
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in rates:
            rate = rates[reverse_key].get('rate')
            if rate and rate > 0:
                return 1.0 / rate
        
        # Попробуем через USD как промежуточную валюту
        if from_currency != 'USD' and to_currency != 'USD':
            from_usd = self.get_exchange_rate(from_currency, 'USD')
            usd_to = self.get_exchange_rate('USD', to_currency)
            
            if from_usd and usd_to:
                return from_usd * usd_to
        
        return None
    
    def save_exchange_rate_history(self, rate_data: Dict[str, Any]) -> None:
        """Сохраняет историческую запись курса валюты"""
        with self._lock:
            history_data = self._read_json(self.data_dir / 'exchange_rates.json')
            
            if isinstance(history_data, dict):
                history_data = list(history_data.values())
            
            # Добавляем новую запись
            history_data.append(rate_data)
            
            # Сохраняем
            self._write_json(self.data_dir / 'exchange_rates.json', history_data)
    
    def get_exchange_rate_history(self, from_currency: str = None, 
                                 to_currency: str = None, 
                                 limit: int = 100) -> List[Dict[str, Any]]:
        """Получает историю курсов валют с фильтрацией"""
        history_data = self._read_json(self.data_dir / 'exchange_rates.json')
        
        if isinstance(history_data, dict):
            history_data = list(history_data.values())
        
        # Фильтрация
        filtered_history = []
        for record in history_data:
            if from_currency and record.get('from_currency') != from_currency:
                continue
            if to_currency and record.get('to_currency') != to_currency:
                continue
            filtered_history.append(record)
        
        # Сортировка по времени (новые сначала)
        filtered_history.sort(
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        # Ограничение количества
        return filtered_history[:limit]
    
    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ТРАНЗАКЦИЯМИ ====================
    
    def save_transaction(self, transaction_data: Dict[str, Any]) -> None:
        """Сохраняет транзакцию в базу данных"""
        with self._lock:
            transactions_data = self._read_json(self.data_dir / 'transactions.json')
            
            if isinstance(transactions_data, dict):
                transactions_data = list(transactions_data.values())
            
            # Добавляем ID и timestamp если их нет
            if 'transaction_id' not in transaction_data:
                transaction_data['transaction_id'] = len(transactions_data) + 1
            if 'timestamp' not in transaction_data:
                transaction_data['timestamp'] = datetime.now().isoformat()
            
            transactions_data.append(transaction_data)
            self._write_json(self.data_dir / 'transactions.json', transactions_data)
    
    def get_user_transactions(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получает транзакции пользователя"""
        transactions_data = self._read_json(self.data_dir / 'transactions.json')
        
        if isinstance(transactions_data, dict):
            transactions_data = list(transactions_data.values())
        
        # Фильтруем транзакции пользователя
        user_transactions = [
            t for t in transactions_data
            if t.get('user_id') == user_id
        ]
        
        # Сортировка по времени (новые сначала)
        user_transactions.sort(
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        return user_transactions[:limit]
    
    # ==================== СЛУЖЕБНЫЕ МЕТОДЫ ====================
    
    def backup_database(self, backup_dir: str = "backups") -> str:
        """Создает резервную копию базы данных"""
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"valutatrade_backup_{timestamp}.zip"
        
        try:
            import zipfile
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in self.data_dir.glob("*.json"):
                    zipf.write(file, file.name)
            
            print(f"Резервная копия создана: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            print(f"Ошибка создания резервной копии: {e}")
            return ""
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Возвращает статистику базы данных"""
        stats = {
            "users": 0,
            "portfolios": 0,
            "exchange_rates": 0,
            "transactions": 0,
            "total_size_kb": 0,
        }
        
        # Подсчет записей
        stats["users"] = len(self.get_all_users())
        stats["portfolios"] = len(self.get_all_portfolios())
        stats["exchange_rates"] = len(self.get_exchange_rates())
        
        transactions_data = self._read_json(self.data_dir / 'transactions.json')
        if isinstance(transactions_data, dict):
            transactions_data = list(transactions_data.values())
        stats["transactions"] = len(transactions_data)
        
        # Подсчет размера файлов
        total_size = 0
        for file in self.data_dir.glob("*.json"):
            total_size += file.stat().st_size
        stats["total_size_kb"] = total_size / 1024
        
        # Время последнего обновления курсов
        rates_data = self._read_json(self.data_dir / 'rates.json')
        stats["last_rates_update"] = rates_data.get('last_refresh', 'Never')
        
        return stats
    
    def clear_database(self, confirm: bool = False) -> bool:
        """Очищает базу данных (только для тестирования)"""
        if not confirm:
            print("Для очистки базы данных установите confirm=True")
            return False
        
        with self._lock:
            try:
                # Удаляем все файлы данных
                for file in self.data_dir.glob("*.json"):
                    file.unlink()
                
                # Переинициализируем базу
                self._init_database()
                
                print("База данных очищена")
                return True
                
            except Exception as e:
                print(f"Ошибка очистки базы данных: {e}")
                return False
    
    def __str__(self) -> str:
        """Строковое представление DatabaseManager"""
        stats = self.get_database_stats()
        return (
            f"DatabaseManager:\n"
            f"Data directory: {self.data_dir}\n"
            f"Users: {stats['users']}\n"
            f"Portfolios: {stats['portfolios']}\n"
            f"Exchange rates: {stats['exchange_rates']}\n"
            f"Transactions: {stats['transactions']}\n"
            f"Total size: {stats['total_size_kb']:.2f} KB\n"
            f"Last rates update: {stats['last_rates_update']}"
        )