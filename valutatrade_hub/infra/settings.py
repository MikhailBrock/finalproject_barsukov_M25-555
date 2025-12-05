"""
Singleton для загрузки конфигурации
"""

import json
from pathlib import Path
from typing import Any, Optional

import toml


class Singleton(type):
    """Метакласс для реализации паттерна Singleton"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class SettingsLoader(metaclass=Singleton):
    """Загрузчик конфигурации (Singleton)"""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or Path("pyproject.toml")
        self._config = {}
        self._load_config()

    def _load_config(self):
        """Загружает конфигурацию из файла"""
        try:
            if self._config_path.exists():
                if self._config_path.suffix == ".toml":
                    data = toml.load(self._config_path)
                    self._config = data.get("tool", {}).get("valutatrade", {})
                elif self._config_path.suffix == ".json":
                    with open(self._config_path, "r", encoding="utf-8") as f:
                        self._config = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            self._config = {}

        # Устанавливаем значения по умолчанию
        defaults = {
            "data_dir": "data",
            "rates_ttl_seconds": 300,  # 5 минут
            "default_base_currency": "USD",
            "log_level": "INFO",
            "log_file": "logs/actions.log",
        }

        for key, value in defaults.items():
            if key not in self._config:
                self._config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение конфигурации по ключу"""
        return self._config.get(key, default)

    def reload(self):
        """Перезагружает конфигурацию"""
        self._load_config()

    @property
    def data_dir(self) -> Path:
        return Path(self.get("data_dir", "data"))

    @property
    def users_file(self) -> Path:
        return self.data_dir / "users.json"

    @property
    def portfolios_file(self) -> Path:
        return self.data_dir / "portfolios.json"

    @property
    def rates_file(self) -> Path:
        return self.data_dir / "rates.json"

    @property
    def exchange_rates_file(self) -> Path:
        return self.data_dir / "exchange_rates.json"

    @property
    def rates_ttl_seconds(self) -> int:
        return int(self.get("rates_ttl_seconds", 300))

    @property
    def default_base_currency(self) -> str:
        return self.get("default_base_currency", "USD")

    @property
    def log_level(self) -> str:
        return self.get("log_level", "INFO")

    @property
    def log_file(self) -> Path:
        return Path(self.get("log_file", "logs/actions.log"))
