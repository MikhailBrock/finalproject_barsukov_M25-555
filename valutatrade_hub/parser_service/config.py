"""
Конфигурация Parser Service
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


@dataclass
class ParserConfig:
    """Конфигурация парсера курсов"""

    # Ключ API (загружается из переменной окружения)
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # Эндпоинты API
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Базовые параметры
    BASE_CURRENCY: str = "USD"
    REQUEST_TIMEOUT: int = 10

    # Фиатные валюты для отслеживания
    FIAT_CURRENCIES: Tuple[str, ...] = field(
        default_factory=lambda: ("EUR", "GBP", "RUB", "JPY", "CHF", "CAD", "AUD", "CNY")
    )

    # Криптовалюты для отслеживания
    CRYPTO_CURRENCIES: Tuple[str, ...] = field(
        default_factory=lambda: (
            "BTC",
            "ETH",
            "SOL",
            "BNB",
            "XRP",
            "ADA",
            "DOGE",
            "DOT",
        )
    )

    # Соответствие кодов и ID для CoinGecko
    CRYPTO_ID_MAP: Dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "BNB": "binancecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "DOT": "polkadot",
        }
    )

    # Пути к файлам
    @property
    def RATES_FILE_PATH(self) -> Path:
        return Path("data/rates.json")

    @property
    def HISTORY_FILE_PATH(self) -> Path:
        return Path("data/exchange_rates.json")

    def validate(self):
        """Проверяет корректность конфигурации"""
        if not self.EXCHANGERATE_API_KEY:
            print("Предупреждение: EXCHANGERATE_API_KEY не установлен.")
            print("Фиатные курсы не будут обновляться.")
            print(
                "Установите переменную окружения: "
                "export EXCHANGERATE_API_KEY='ваш_ключ'"
            )

        # Проверяем существование директорий
        self.RATES_FILE_PATH.parent.mkdir(exist_ok=True)
        self.HISTORY_FILE_PATH.parent.mkdir(exist_ok=True)


# Глобальный экземпляр конфигурации
config = ParserConfig()
