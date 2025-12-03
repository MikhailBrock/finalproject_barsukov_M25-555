from abc import ABC, abstractmethod
from typing import Dict


class Currency(ABC):
    def __init__(self, name: str, code: str):
        if not name or not name.strip():
            raise ValueError("Currency name cannot be empty")
        if not (2 <= len(code) <= 5) or not code.isupper() or ' ' in code:
            raise ValueError("Currency code must be 2-5 uppercase letters without spaces")
        
        self.name = name
        self.code = code
    
    @abstractmethod
    def get_display_info(self) -> str:
        pass
    
    def __str__(self):
        return self.get_display_info()


class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country
    
    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} - {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap
    
    def get_display_info(self) -> str:
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap > 1e6 else f"{self.market_cap:,.2f}"
        return f"[CRYPTO] {self.code} - {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"


class CurrencyRegistry:
    _currencies: Dict[str, Currency] = {
        'USD': FiatCurrency("US Dollar", "USD", "United States"),
        'EUR': FiatCurrency("Euro", "EUR", "Eurozone"),
        'GBP': FiatCurrency("British Pound", "GBP", "United Kingdom"),
        'RUB': FiatCurrency("Russian Ruble", "RUB", "Russia"),
        'JPY': FiatCurrency("Japanese Yen", "JPY", "Japan"),
        'CNY': FiatCurrency("Chinese Yuan", "CNY", "China"),
        'BTC': CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
        'ETH': CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
        'SOL': CryptoCurrency("Solana", "SOL", "Proof of History", 7.8e10),
        'ADA': CryptoCurrency("Cardano", "ADA", "Ouroboros", 2.1e10),
    }
    
    @classmethod
    def get_currency(cls, code: str) -> Currency:
        """Получает объект валюты по коду"""
        currency = cls._currencies.get(code.upper())
        if not currency:
            from valutatrade_hub.core.exceptions import CurrencyNotFoundError
            raise CurrencyNotFoundError(code)
        return currency
    
    @classmethod
    def list_currencies(cls) -> list:
        """Возвращает список всех доступных кодов валют"""
        return list(cls._currencies.keys())
    
    @classmethod
    def list_fiat_currencies(cls) -> list:
        """Возвращает список фиатных валют"""
        return [code for code, currency in cls._currencies.items() 
                if isinstance(currency, FiatCurrency)]
    
    @classmethod
    def list_crypto_currencies(cls) -> list:
        """Возвращает список криптовалют"""
        return [code for code, currency in cls._currencies.items() 
                if isinstance(currency, CryptoCurrency)]
    
    @classmethod
    def get_currency_info(cls, code: str) -> str:
        """Возвращает информацию о валюте в виде строки"""
        currency = cls.get_currency(code)
        return currency.get_display_info()
    
    @classmethod
    def is_valid_currency(cls, code: str) -> bool:
        """Проверяет, существует ли валюта"""
        return code.upper() in cls._currencies
    
    @classmethod
    def get_currency_type(cls, code: str) -> str:
        """Возвращает тип валюты: 'fiat' или 'crypto'"""
        currency = cls.get_currency(code)
        return 'fiat' if isinstance(currency, FiatCurrency) else 'crypto'