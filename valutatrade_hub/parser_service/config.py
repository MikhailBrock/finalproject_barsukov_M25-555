import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from valutatrade_hub.core.currencies import CurrencyRegistry


@dataclass
class ParserConfig:
    """
    Конфигурация для сервиса парсинга курсов валют.
    Использует dataclass для удобного хранения настроек.
    """
    
    # ==================== API КЛЮЧИ И ЭНДПОИНТЫ ====================
    
    # ExchangeRate-API (для фиатных валют)
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv('EXCHANGERATE_API_KEY', '')
    )
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    
    # CoinGecko API (для криптовалют)
    COINGECKO_API_KEY: str = field(
        default_factory=lambda: os.getenv('COINGECKO_API_KEY', '')
    )
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"
    
    # ==================== ВАЛЮТЫ ДЛЯ ОТСЛЕЖИВАНИЯ ====================
    
    # Базовая валюта для запросов
    BASE_CURRENCY: str = "USD"
    
    # Фиатные валюты для отслеживания
    FIAT_CURRENCIES: Tuple[str, ...] = field(
        default_factory=lambda: (
            'EUR', 'GBP', 'RUB', 'JPY', 'CNY', 'CHF', 'CAD', 'AUD', 'NZD',
            'BRL', 'MXN', 'INR', 'KRW', 'TRY', 'ZAR', 'SEK', 'NOK', 'DKK',
            'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'HRK', 'ILS', 'PHP', 'THB',
            'MYR', 'IDR', 'VND', 'SGD', 'HKD', 'TWD', 'AED', 'SAR', 'QAR',
            'KWD', 'OMR', 'BHD'
        )
    )
    
    # Криптовалюты для отслеживания
    CRYPTO_CURRENCIES: Tuple[str, ...] = field(
        default_factory=lambda: (
            'BTC', 'ETH', 'SOL', 'ADA', 'XRP', 'DOT', 'DOGE', 'SHIB', 'AVAX',
            'MATIC', 'ATOM', 'LTC', 'UNI', 'LINK', 'XLM', 'ALGO', 'VET', 'TRX',
            'ETC', 'XMR', 'EOS', 'XTZ', 'MIOTA', 'NEO', 'DASH', 'ZEC', 'BSV',
            'BCH', 'FIL', 'ICP', 'THETA', 'FTM', 'AAVE', 'CAKE', 'KSM', 'MKR',
            'COMP', 'YFI', 'SNX', 'SUSHI', 'CRV', 'BAT', 'ENJ', 'MANA', 'SAND',
            'AXS', 'CHZ', 'GALA', 'APE'
        )
    )
    
    # Сопоставление кодов криптовалют с ID в CoinGecko
    CRYPTO_ID_MAP: Dict[str, str] = field(
        default_factory=lambda: {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'ADA': 'cardano',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'SHIB': 'shiba-inu',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network',
            'ATOM': 'cosmos',
            'LTC': 'litecoin',
            'UNI': 'uniswap',
            'LINK': 'chainlink',
            'XLM': 'stellar',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'TRX': 'tron',
            'ETC': 'ethereum-classic',
            'XMR': 'monero',
            'EOS': 'eos',
            'XTZ': 'tezos',
            'MIOTA': 'iota',
            'NEO': 'neo',
            'DASH': 'dash',
            'ZEC': 'zcash',
            'BSV': 'bitcoin-cash-sv',
            'BCH': 'bitcoin-cash',
            'FIL': 'filecoin',
            'ICP': 'internet-computer',
            'THETA': 'theta-token',
            'FTM': 'fantom',
            'AAVE': 'aave',
            'CAKE': 'pancakeswap-token',
            'KSM': 'kusama',
            'MKR': 'maker',
            'COMP': 'compound-governance-token',
            'YFI': 'yearn-finance',
            'SNX': 'havven',
            'SUSHI': 'sushi',
            'CRV': 'curve-dao-token',
            'BAT': 'basic-attention-token',
            'ENJ': 'enjincoin',
            'MANA': 'decentraland',
            'SAND': 'the-sandbox',
            'AXS': 'axie-infinity',
            'CHZ': 'chiliz',
            'GALA': 'gala',
            'APE': 'apecoin',
        }
    )
    
    # ==================== ПАРАМЕТРЫ ЗАПРОСОВ ====================
    
    REQUEST_TIMEOUT: int = 30  # Таймаут запросов в секундах
    MAX_RETRIES: int = 3  # Максимальное количество повторных попыток
    RETRY_DELAY: int = 5  # Задержка между попытками в секундах
    
    # User-Agent для запросов
    USER_AGENT: str = "ValutaTrade Parser/1.0 (Educational Project)"
    
    # ==================== ПУТИ К ФАЙЛАМ ====================
    
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"
    PARSER_LOG_FILE: str = "logs/parser.log"
    
    # ==================== ПАРАМЕТРЫ ОБНОВЛЕНИЯ ====================
    
    UPDATE_INTERVAL: int = 300  # Интервал обновления в секундах (5 минут)
    RATES_TTL: int = 300  # Время жизни кэша курсов в секундах (5 минут)
    
    # Минимальный интервал между запросами к одному API
    MIN_REQUEST_INTERVAL: int = 2  # секунды
    
    # ==================== ВАЛИДАЦИЯ И ФИЛЬТРАЦИЯ ====================
    
    # Минимальный допустимый курс (для фильтрации ошибок)
    MIN_RATE_VALUE: float = 1e-10
    
    # Максимальный допустимый курс
    MAX_RATE_VALUE: float = 1e10
    
    # Максимальное изменение курса за один раз (в процентах)
    MAX_RATE_CHANGE_PERCENT: float = 50.0
    
    # ==================== МЕТОДЫ ПРОВЕРКИ ====================
    
    def validate_config(self) -> List[str]:
        """
        Проверяет корректность конфигурации.
        
        Returns:
            Список ошибок конфигурации (пустой если все OK)
        """
        errors = []
        
        # Проверка API ключей
        if not self.EXCHANGERATE_API_KEY:
            errors.append("EXCHANGERATE_API_KEY не установлен. "
                         "Установите переменную окружения EXCHANGERATE_API_KEY")
        
        # Проверка валют
        for currency in self.FIAT_CURRENCIES:
            if not CurrencyRegistry.is_valid_currency(currency):
                errors.append(f"Неизвестная фиатная валюта: {currency}")
        
        for currency in self.CRYPTO_CURRENCIES:
            if not CurrencyRegistry.is_valid_currency(currency):
                errors.append(f"Неизвестная криптовалюта: {currency}")
        
        # Проверка сопоставления криптовалют
        for currency, coin_id in self.CRYPTO_ID_MAP.items():
            if currency not in self.CRYPTO_CURRENCIES:
                errors.append(f"CRYPTO_ID_MAP содержит валюту {currency}, "
                             f"но ее нет в CRYPTO_CURRENCIES")
        
        # Проверка параметров
        if self.REQUEST_TIMEOUT <= 0:
            errors.append("REQUEST_TIMEOUT должен быть положительным числом")
        
        if self.UPDATE_INTERVAL < 60:
            errors.append("UPDATE_INTERVAL должен быть не менее 60 секунд")
        
        if self.RATES_TTL < 60:
            errors.append("RATES_TTL должен быть не менее 60 секунд")
        
        return errors
    
    def get_crypto_ids_for_request(self) -> List[str]:
        """
        Возвращает список ID криптовалют для запроса к CoinGecko.
        
        Returns:
            Список ID криптовалют
        """
        return [
            self.CRYPTO_ID_MAP[currency]
            for currency in self.CRYPTO_CURRENCIES
            if currency in self.CRYPTO_ID_MAP
        ]
    
    def get_fiat_currencies_for_request(self) -> List[str]:
        """
        Возвращает список фиатных валют для запроса к ExchangeRate-API.
        
        Returns:
            Список кодов фиатных валют
        """
        # Исключаем базовую валюту из списка целевых
        return [
            currency for currency in self.FIAT_CURRENCIES
            if currency != self.BASE_CURRENCY
        ]
    
    def get_rate_key(self, from_currency: str, to_currency: str) -> str:
        """
        Генерирует ключ для пары валют.
        
        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            
        Returns:
            Ключ в формате "FROM_TO"
        """
        return f"{from_currency.upper()}_{to_currency.upper()}"
    
    def is_valid_rate(self, rate: float) -> bool:
        """
        Проверяет валидность курса.
        
        Args:
            rate: Курс для проверки
            
        Returns:
            True если курс валиден
        """
        if not isinstance(rate, (int, float)):
            return False
        
        if rate <= self.MIN_RATE_VALUE:
            return False
        
        if rate >= self.MAX_RATE_VALUE:
            return False
        
        return True
    
    def get_exchangerate_api_url(self) -> str:
        """
        Возвращает URL для запроса к ExchangeRate-API.
        
        Returns:
            Полный URL
        """
        return f"{self.EXCHANGERATE_API_URL}/{self.EXCHANGERATE_API_KEY}/latest/{self.BASE_CURRENCY}"
    
    def get_coingecko_api_url(self) -> str:
        """
        Возвращает URL для запроса к CoinGecko API.
        
        Returns:
            Полный URL
        """
        crypto_ids = self.get_crypto_ids_for_request()
        ids_param = ','.join(crypto_ids[:50])  # Ограничиваем 50 валютами за запрос
        return f"{self.COINGECKO_API_URL}/simple/price?ids={ids_param}&vs_currencies={self.BASE_CURRENCY.lower()}"
    
    def get_headers(self) -> Dict[str, str]:
        """
        Возвращает заголовки для HTTP запросов.
        
        Returns:
            Словарь заголовков
        """
        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        # Добавляем API ключ для CoinGecko если есть
        if self.COINGECKO_API_KEY:
            headers['x-cg-pro-api-key'] = self.COINGECKO_API_KEY
        
        return headers
    
    def __str__(self) -> str:
        """
        Строковое представление конфигурации.
        
        Returns:
            Информация о конфигурации
        """
        return (
            f"ParserConfig:\n"
            f"  Base Currency: {self.BASE_CURRENCY}\n"
            f"  Fiat Currencies: {len(self.FIAT_CURRENCIES)} currencies\n"
            f"  Crypto Currencies: {len(self.CRYPTO_CURRENCIES)} currencies\n"
            f"  Update Interval: {self.UPDATE_INTERVAL}s\n"
            f"  Rates TTL: {self.RATES_TTL}s\n"
            f"  Request Timeout: {self.REQUEST_TIMEOUT}s\n"
            f"  ExchangeRate-API Key: {'Set' if self.EXCHANGERATE_API_KEY else 'Not set'}\n"
            f"  CoinGecko API Key: {'Set' if self.COINGECKO_API_KEY else 'Not set'}"
        )
    
    def print_summary(self):
        """Выводит сводку конфигурации."""
        print("=" * 60)
        print("КОНФИГУРАЦИЯ ПАРСЕРА КУРСОВ ВАЛЮТ")
        print("=" * 60)
        print(str(self))
        
        # Проверяем конфигурацию
        errors = self.validate_config()
        if errors:
            print("\n⚠ ОШИБКИ КОНФИГУРАЦИИ:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\n✓ Конфигурация валидна")
        
        print("=" * 60)


# Создаем глобальный экземпляр конфигурации
config = ParserConfig()
