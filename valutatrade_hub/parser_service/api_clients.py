"""
Клиенты для работы с внешними API
"""

from abc import ABC, abstractmethod
from typing import Dict

import requests

from ..core.exceptions import ApiRequestError
from .config import config


class BaseApiClient(ABC):
    """Базовый класс API-клиента"""

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы валют"""
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент для CoinGecko API"""

    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы криптовалют"""
        if not config.CRYPTO_CURRENCIES:
            return {}

        # Подготавливаем параметры запроса
        crypto_ids = []
        for code in config.CRYPTO_CURRENCIES:
            if code in config.CRYPTO_ID_MAP:
                crypto_ids.append(config.CRYPTO_ID_MAP[code])

        if not crypto_ids:
            return {}

        params = {"ids": ",".join(crypto_ids), "vs_currencies": "usd"}

        try:
            response = requests.get(
                config.COINGECKO_URL, params=params, timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            rates = {}

            # Преобразуем ответ в стандартный формат
            for code in config.CRYPTO_CURRENCIES:
                if code in config.CRYPTO_ID_MAP:
                    crypto_id = config.CRYPTO_ID_MAP[code]
                    if crypto_id in data and "usd" in data[crypto_id]:
                        pair = f"{code}_{config.BASE_CURRENCY}"
                        rates[pair] = float(data[crypto_id]["usd"])

            return rates

        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise ApiRequestError(f"CoinGecko: ошибка парсинга ответа - {e}")


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для ExchangeRate-API"""

    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы фиатных валют"""
        if not config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("Не указан API ключ для ExchangeRate-API")

        if not config.FIAT_CURRENCIES:
            return {}

        url = (
            f"{config.EXCHANGERATE_API_URL}/{config.EXCHANGERATE_API_KEY}/"
            f"latest/{config.BASE_CURRENCY}"
        )

        try:
            response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            if data.get("result") != "success":
                error_type = data.get("error-type", "unknown error")
                raise ApiRequestError(f"ExchangeRate-API: {error_type}")

            rates = {}
            base_code = data.get("base_code", config.BASE_CURRENCY)

            for code in config.FIAT_CURRENCIES:
                if code in data.get("rates", {}):
                    if code != base_code:  # Не включаем базовую валюту
                        pair = f"{code}_{base_code}"
                        rates[pair] = float(data["rates"][code])

            return rates

        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise ApiRequestError(f"ExchangeRate-API: ошибка парсинга ответа - {e}")


class MockApiClient(BaseApiClient):
    """Мок-клиент для тестирования (использует фиксированные курсы)"""

    def fetch_rates(self) -> Dict[str, float]:
        """Возвращает фиксированные курсы для демонстрации"""
        return {
            "EUR_USD": 1.0786,
            "GBP_USD": 1.2543,
            "RUB_USD": 0.01016,
            "JPY_USD": 0.0067,
            "BTC_USD": 59337.21,
            "ETH_USD": 3720.00,
            "SOL_USD": 145.12,
        }
