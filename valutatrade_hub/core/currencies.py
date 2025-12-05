"""
Иерархия валют: Currency, FiatCurrency, CryptoCurrency
"""

from abc import ABC, abstractmethod
from typing import Dict

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс валюты"""

    def __init__(self, name: str, code: str):
        if not name or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

        code = code.upper().strip()
        if not (2 <= len(code) <= 5):
            raise ValueError("Код валюты должен содержать от 2 до 5 символов")
        if " " in code:
            raise ValueError("Код валюты не должен содержать пробелы")

        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов"""
        pass

    def __str__(self) -> str:
        return self.get_display_info()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} code={self.code}>"


class FiatCurrency(Currency):
    """Фиатная валюта"""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта"""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        mcap_str = (
            f"{self.market_cap:.2e}"
            if self.market_cap > 1e6
            else f"{self.market_cap:,.2f}"
        )
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {mcap_str})"
        )


# Реестр валют
_CURRENCY_REGISTRY: Dict[str, Currency] = {}


def register_currency(currency: Currency):
    """Регистрирует валюту в реестре"""
    _CURRENCY_REGISTRY[currency.code] = currency


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду"""
    code = code.upper()
    currency = _CURRENCY_REGISTRY.get(code)
    if not currency:
        raise CurrencyNotFoundError(code)
    return currency


def get_all_currencies() -> Dict[str, Currency]:
    """Возвращает все зарегистрированные валюты"""
    return _CURRENCY_REGISTRY.copy()


# Инициализация реестра с демонстрационными валютами
def init_currency_registry():
    """Инициализирует реестр валют"""
    # Фиатные валюты
    register_currency(FiatCurrency("US Dollar", "USD", "United States"))
    register_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
    register_currency(FiatCurrency("British Pound", "GBP", "United Kingdom"))
    register_currency(FiatCurrency("Russian Ruble", "RUB", "Russia"))

    # Криптовалюты
    register_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
    register_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11))
    register_currency(CryptoCurrency("Solana", "SOL", "Proof of History", 6.5e10))


# Инициализируем при импорте
init_currency_registry()
