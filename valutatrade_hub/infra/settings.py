import os
import json
from typing import Any

class SettingsLoader:
    _instance = None
    _settings = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._load_settings()
        return cls._instance
    
    @classmethod
    def _load_settings(cls):
        """Загружает настройки из pyproject.toml и переменных окружения"""
        # Базовые настройки
        cls._settings = {
            'data_dir': 'data',
            'rates_ttl_seconds': 300,  # 5 минут
            'default_base_currency': 'USD',
            'log_file': 'logs/valutatrade.log',
            'log_level': 'INFO',
            'max_log_size_mb': 10,
            'backup_count': 5
        }
        
        # Переменные окружения
        env_data_dir = os.getenv('VALUTATRADE_DATA_DIR')
        if env_data_dir:
            cls._settings['data_dir'] = env_data_dir
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)
    
    def reload(self):
        """Перезагружает настройки"""
        self._load_settings()
    
    def __getitem__(self, key: str) -> Any:
        return self._settings[key]