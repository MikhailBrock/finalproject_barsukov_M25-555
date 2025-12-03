import os
import json
from typing import Any, Dict


class SettingsLoader:
    """
    Singleton для загрузки настроек проекта.
    Использует паттерн Singleton через __new__ для гарантии одного экземпляра.
    """
    _instance = None
    _settings: Dict[str, Any] = {}
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Предотвращаем повторную инициализацию
        if not self._initialized:
            self._load_settings()
            self._initialized = True
    
    def _load_settings(self):
        """Загружает настройки из различных источников"""
        # Базовые настройки по умолчанию
        default_settings = {
            # Пути
            'data_dir': 'data',
            'log_dir': 'logs',
            'config_file': 'config.json',
            
            # База данных/хранилище
            'database_auto_save': True,
            'database_save_interval': 30,  # секунды
            
            # Курсы валют
            'rates_ttl_seconds': 300,  # 5 минут
            'rates_cache_size': 100,
            'default_base_currency': 'USD',
            
            # Логирование
            'log_level': 'INFO',
            'log_file': 'valutatrade.log',
            'log_max_size_mb': 10,
            'log_backup_count': 5,
            'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'log_date_format': '%Y-%m-%d %H:%M:%S',
            
            # Парсер
            'parser_enabled': True,
            'parser_update_interval': 300,  # 5 минут
            'parser_retry_attempts': 3,
            'parser_retry_delay': 5,  # секунды
            
            # API
            'api_timeout': 10,  # секунды
            'api_max_retries': 3,
            'api_user_agent': 'ValutaTrade/1.0',
            
            # Безопасность
            'password_min_length': 4,
            'session_timeout': 3600,  # 1 час
            'max_login_attempts': 5,
            
            # Пользовательский интерфейс
            'cli_prompt': 'valutatrade> ',
            'cli_history_file': '.valutatrade_history',
            'cli_max_history': 1000,
            
            # Валюты
            'supported_fiat_currencies': ['USD', 'EUR', 'GBP', 'RUB', 'JPY', 'CNY'],
            'supported_crypto_currencies': ['BTC', 'ETH', 'SOL', 'ADA'],
            
            # Лимиты
            'max_transaction_amount': 1000000.0,
            'min_transaction_amount': 0.01,
            'max_portfolio_size': 50,
        }
        
        # Начинаем с настроек по умолчанию
        self._settings = default_settings.copy()
        
        # Загружаем из переменных окружения
        self._load_from_env()
        
        # Загружаем из файла конфигурации если он существует
        self._load_from_config_file()
        
        # Создаем необходимые директории
        self._create_directories()
    
    def _load_from_env(self):
        """Загружает настройки из переменных окружения"""
        env_mappings = {
            'VALUTATRADE_DATA_DIR': 'data_dir',
            'VALUTATRADE_LOG_DIR': 'log_dir',
            'VALUTATRADE_LOG_LEVEL': 'log_level',
            'VALUTATRADE_DEFAULT_CURRENCY': 'default_base_currency',
            'VALUTATRADE_RATES_TTL': 'rates_ttl_seconds',
            'VALUTATRADE_API_TIMEOUT': 'api_timeout',
            'EXCHANGERATE_API_KEY': 'exchangerate_api_key',
        }
        
        for env_var, setting_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Преобразуем типы данных
                if setting_key in ['rates_ttl_seconds', 'api_timeout', 'parser_update_interval']:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif setting_key in ['parser_enabled']:
                    value = value.lower() in ['true', '1', 'yes', 'y']
                
                self._settings[setting_key] = value
    
    def _load_from_config_file(self):
        """Загружает настройки из файла конфигурации"""
        config_file = self._settings.get('config_file')
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_settings = json.load(f)
                
                # Обновляем настройки из файла
                for key, value in file_settings.items():
                    if key in self._settings:
                        self._settings[key] = value
                    else:
                        # Разрешаем дополнительные настройки из файла
                        self._settings[key] = value
                
                print(f"Настройки загружены из {config_file}")
            except Exception as e:
                print(f"Ошибка загрузки конфигурации из {config_file}: {e}")
        else:
            # Создаем пример конфигурационного файла
            self._create_example_config()
    
    def _create_example_config(self):
        """Создает пример конфигурационного файла"""
        example_config = {
            "comment": "Пример конфигурационного файла ValutaTrade",
            "data_dir": "data",
            "log_level": "INFO",
            "default_base_currency": "USD",
            "rates_ttl_seconds": 300,
            "parser_update_interval": 300,
            "api_timeout": 10,
            "supported_fiat_currencies": ["USD", "EUR", "GBP", "RUB"],
            "supported_crypto_currencies": ["BTC", "ETH", "SOL"]
        }
        
        config_file = self._settings.get('config_file')
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(example_config, f, indent=2, ensure_ascii=False)
            print(f"Создан пример конфигурационного файла: {config_file}")
            print("Отредактируйте его при необходимости.")
        except Exception as e:
            print(f"Не удалось создать пример конфигурации: {e}")
    
    def _create_directories(self):
        """Создает необходимые директории"""
        directories = [
            self._settings.get('data_dir'),
            self._settings.get('log_dir'),
            'logs',  # Для обратной совместимости
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    print(f"Создана директория: {directory}")
                except Exception as e:
                    print(f"Не удалось создать директорию {directory}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение настройки по ключу.
        
        Args:
            key: Ключ настройки
            default: Значение по умолчанию если ключ не найден
        
        Returns:
            Значение настройки или default
        """
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Устанавливает значение настройки.
        
        Args:
            key: Ключ настройки
            value: Значение
        """
        self._settings[key] = value
    
    def reload(self):
        """Перезагружает настройки из всех источников"""
        print("Перезагрузка настроек...")
        self._initialized = False
        self.__init__()
        print("Настройки перезагружены")
    
    def save_to_file(self, filename: str = None):
        """
        Сохраняет текущие настройки в файл.
        
        Args:
            filename: Имя файла (если None, используется config_file из настроек)
        """
        if filename is None:
            filename = self._settings.get('config_file')
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Не сохраняем некоторые системные настройки
                settings_to_save = {
                    k: v for k, v in self._settings.items()
                    if not k.startswith('_') and k not in ['config_file']
                }
                json.dump(settings_to_save, f, indent=2, ensure_ascii=False)
            print(f"Настройки сохранены в {filename}")
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """Возвращает все настройки в виде словаря"""
        return self._settings.copy()
    
    def __getitem__(self, key: str) -> Any:
        """Позволяет обращаться к настройкам как к словарю"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """Позволяет устанавливать настройки как в словаре"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Проверяет наличие ключа в настройках"""
        return key in self._settings
    
    def __str__(self) -> str:
        """Строковое представление настроек"""
        import pprint
        return pprint.pformat(self._settings, indent=2)
    
    def print_summary(self):
        """Выводит сводку настроек"""
        print("=" * 60)
        print("НАСТРОЙКИ VALUTATRADE HUB")
        print("=" * 60)
        
        categories = {
            'Пути': ['data_dir', 'log_dir', 'config_file'],
            'База данных': ['database_auto_save', 'database_save_interval'],
            'Курсы валют': ['rates_ttl_seconds', 'default_base_currency'],
            'Логирование': ['log_level', 'log_file', 'log_max_size_mb'],
            'Парсер': ['parser_enabled', 'parser_update_interval'],
            'API': ['api_timeout', 'api_max_retries'],
            'Безопасность': ['password_min_length', 'session_timeout'],
            'Валюты': ['supported_fiat_currencies', 'supported_crypto_currencies'],
            'Лимиты': ['max_transaction_amount', 'min_transaction_amount'],
        }
        
        for category, keys in categories.items():
            print(f"\n{category}:")
            print("-" * 40)
            for key in keys:
                if key in self._settings:
                    value = self._settings[key]
                    if isinstance(value, list):
                        value = ', '.join(str(v) for v in value)
                    print(f"  {key}: {value}")
        
        print("\n" + "=" * 60)