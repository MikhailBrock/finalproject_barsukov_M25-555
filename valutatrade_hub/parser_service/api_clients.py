import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.decorators import retry_on_failure


logger = logging.getLogger('valutatrade.api')


class BaseApiClient(ABC):
    """Абстрактный базовый класс для API клиентов."""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.last_request_time = 0
        self.request_count = 0
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())
    
    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы валют от API.
        
        Returns:
            Словарь {валютная_пара: курс}
        
        Raises:
            ApiRequestError: Если произошла ошибка при запросе
        """
        pass
    
    def _make_request(self, url: str, method: str = 'GET', 
                     params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос с обработкой ошибок и ограничением частоты.
        
        Args:
            url: URL для запроса
            method: HTTP метод
            params: Параметры запроса
            
        Returns:
            Ответ от API в виде словаря
            
        Raises:
            ApiRequestError: Если произошла ошибка при запросе
        """
        # Ограничение частоты запросов
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.config.MIN_REQUEST_INTERVAL:
            sleep_time = self.config.MIN_REQUEST_INTERVAL - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        try:
            logger.info(f"Making {method} request to {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            self.last_request_time = time.time()
            self.request_count += 1
            
            # Проверяем статус код
            response.raise_for_status()
            
            # Парсим JSON
            data = response.json()
            
            logger.debug(f"Request successful. Status: {response.status_code}")
            return data
            
        except Timeout:
            error_msg = f"Request timeout after {self.config.REQUEST_TIMEOUT}s"
            logger.error(error_msg)
            raise ApiRequestError(error_msg, status_code=408)
            
        except ConnectionError:
            error_msg = "Network connection error"
            logger.error(error_msg)
            raise ApiRequestError(error_msg, status_code=0)
            
        except RequestException as e:
            status_code = e.response.status_code if e.response else 0
            error_msg = f"HTTP error {status_code}: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestError(error_msg, status_code=status_code)
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestError(error_msg, status_code=response.status_code)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestError(error_msg)
    
    def _validate_response(self, data: Dict[str, Any]) -> bool:
        """
        Проверяет валидность ответа от API.
        
        Args:
            data: Данные ответа
            
        Returns:
            True если ответ валиден
        """
        if not data:
            return False
        
        return True


class CoinGeckoClient(BaseApiClient):
    """Клиент для работы с CoinGecko API."""
    
    @retry_on_failure(max_attempts=3, delay=5, exceptions=(ApiRequestError,))
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы криптовалют от CoinGecko API.
        
        Returns:
            Словарь {криптовалюта_USD: курс}
        """
        logger.info("Fetching cryptocurrency rates from CoinGecko...")
        
        try:
            # Получаем URL для запроса
            url = self.config.get_coingecko_api_url()
            
            # Выполняем запрос
            data = self._make_request(url)
            
            # Валидируем ответ
            if not self._validate_response(data):
                raise ApiRequestError("Invalid response from CoinGecko")
            
            # Парсим и преобразуем данные
            rates = {}
            
            for coin_id, coin_data in data.items():
                # Находим код валюты по ID
                currency_code = None
                for code, cid in self.config.CRYPTO_ID_MAP.items():
                    if cid == coin_id:
                        currency_code = code
                        break
                
                if not currency_code:
                    logger.warning(f"Unknown coin ID: {coin_id}")
                    continue
                
                # Получаем курс к USD
                usd_rate = coin_data.get('usd')
                if usd_rate is None:
                    logger.warning(f"No USD rate for {currency_code}")
                    continue
                
                # Проверяем валидность курса
                if not self.config.is_valid_rate(usd_rate):
                    logger.warning(f"Invalid rate for {currency_code}: {usd_rate}")
                    continue
                
                # Сохраняем курс
                rate_key = self.config.get_rate_key(currency_code, 'USD')
                rates[rate_key] = usd_rate
                
                # Также сохраняем обратный курс
                reverse_key = self.config.get_rate_key('USD', currency_code)
                if usd_rate > 0:
                    rates[reverse_key] = 1.0 / usd_rate
            
            logger.info(f"Successfully fetched {len(rates)} cryptocurrency rates")
            return rates
            
        except ApiRequestError:
            raise  # Пробрасываем дальше
        except Exception as e:
            error_msg = f"Failed to fetch rates from CoinGecko: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestError(error_msg)
    
    def _validate_response(self, data: Dict[str, Any]) -> bool:
        """
        Специализированная валидация для CoinGecko.
        """
        if not super()._validate_response(data):
            return False
        
        # Проверяем структуру данных CoinGecko
        if not isinstance(data, dict):
            return False
        
        # Должен быть хотя бы один курс
        if len(data) == 0:
            return False
        
        return True


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для работы с ExchangeRate-API."""
    
    @retry_on_failure(max_attempts=3, delay=5, exceptions=(ApiRequestError,))
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы фиатных валют от ExchangeRate-API.
        
        Returns:
            Словарь {фиатная_валюта_USD: курс}
        """
        logger.info("Fetching fiat currency rates from ExchangeRate-API...")
        
        try:
            # Получаем URL для запроса
            url = self.config.get_exchangerate_api_url()
            
            # Выполняем запрос
            data = self._make_request(url)
            
            # Валидируем ответ
            if not self._validate_response(data):
                raise ApiRequestError("Invalid response from ExchangeRate-API")
            
            # Проверяем статус
            if data.get('result') != 'success':
                error_msg = data.get('error-type', 'Unknown error')
                raise ApiRequestError(f"ExchangeRate-API error: {error_msg}")
            
            # Парсим и преобразуем данные
            rates = {}
            base_currency = data.get('base_code', 'USD').upper()
            rates_data = data.get('rates', {})
            
            for currency_code, rate in rates_data.items():
                currency_code = currency_code.upper()
                
                # Пропускаем базовую валюту
                if currency_code == base_currency:
                    continue
                
                # Проверяем что валюта поддерживается
                if currency_code not in self.config.FIAT_CURRENCIES:
                    continue
                
                # Проверяем валидность курса
                if not self.config.is_valid_rate(rate):
                    logger.warning(f"Invalid rate for {currency_code}: {rate}")
                    continue
                
                # Сохраняем курс
                rate_key = self.config.get_rate_key(currency_code, base_currency)
                rates[rate_key] = rate
                
                # Также сохраняем обратный курс
                reverse_key = self.config.get_rate_key(base_currency, currency_code)
                if rate > 0:
                    rates[reverse_key] = 1.0 / rate
            
            # Добавляем курсы между фиатными валютами (через USD)
            self._add_cross_rates(rates, base_currency)
            
            logger.info(f"Successfully fetched {len(rates)} fiat currency rates")
            return rates
            
        except ApiRequestError:
            raise  # Пробрасываем дальше
        except Exception as e:
            error_msg = f"Failed to fetch rates from ExchangeRate-API: {str(e)}"
            logger.error(error_msg)
            raise ApiRequestError(error_msg)
    
    def _validate_response(self, data: Dict[str, Any]) -> bool:
        """
        Специализированная валидация для ExchangeRate-API.
        """
        if not super()._validate_response(data):
            return False
        
        # Проверяем обязательные поля
        required_fields = ['result', 'base_code', 'rates']
        for field in required_fields:
            if field not in data:
                return False
        
        # Проверяем rates
        rates = data.get('rates', {})
        if not isinstance(rates, dict) or len(rates) == 0:
            return False
        
        return True
    
    def _add_cross_rates(self, rates: Dict[str, float], base_currency: str):
        """
        Добавляет кросс-курсы между фиатными валютами.
        
        Args:
            rates: Словарь с курсами
            base_currency: Базовая валюта
        """
        # Получаем все фиатные валюты
        fiat_currencies = [
            currency for currency in self.config.FIAT_CURRENCIES
            if currency != base_currency
        ]
        
        # Добавляем кросс-курсы между всеми парами фиатных валют
        for i, from_currency in enumerate(fiat_currencies):
            for to_currency in fiat_currencies[i+1:]:
                if from_currency == to_currency:
                    continue
                
                # Вычисляем кросс-курс через USD
                from_usd_key = self.config.get_rate_key(from_currency, base_currency)
                usd_to_key = self.config.get_rate_key(base_currency, to_currency)
                
                if from_usd_key in rates and usd_to_key in rates:
                    from_usd_rate = rates[from_usd_key]
                    usd_to_rate = rates[usd_to_key]
                    
                    if from_usd_rate > 0 and usd_to_rate > 0:
                        cross_rate = from_usd_rate * usd_to_rate
                        
                        # Проверяем валидность
                        if self.config.is_valid_rate(cross_rate):
                            cross_key = self.config.get_rate_key(from_currency, to_currency)
                            rates[cross_key] = cross_rate
                            
                            # Обратный курс
                            reverse_key = self.config.get_rate_key(to_currency, from_currency)
                            rates[reverse_key] = 1.0 / cross_rate


class MockApiClient(BaseApiClient):
    """
    Mock клиент для тестирования без реальных API запросов.
    Генерирует реалистичные тестовые данные.
    """
    
    def __init__(self, config: ParserConfig, client_type: str = 'both'):
        """
        Args:
            config: Конфигурация
            client_type: Тип клиента ('crypto', 'fiat', или 'both')
        """
        super().__init__(config)
        self.client_type = client_type
        self.mock_data = self._generate_mock_data()
    
    def fetch_rates(self) -> Dict[str, float]:
        """
        Возвращает mock курсы валют.
        
        Returns:
            Словарь с тестовыми курсами
        """
        logger.info("Using mock API client (no real API calls)")
        
        rates = {}
        
        if self.client_type in ['crypto', 'both']:
            # Mock данные для криптовалют
            crypto_rates = {
                'BTC_USD': 50000.0 + (hash('BTC') % 1000),
                'ETH_USD': 3000.0 + (hash('ETH') % 100),
                'SOL_USD': 100.0 + (hash('SOL') % 10),
                'ADA_USD': 0.5 + (hash('ADA') % 0.1),
                'XRP_USD': 0.6 + (hash('XRP') % 0.1),
            }
            
            # Добавляем обратные курсы
            for pair, rate in crypto_rates.items():
                rates[pair] = rate
                from_curr, to_curr = pair.split('_')
                reverse_pair = f"{to_curr}_{from_curr}"
                rates[reverse_pair] = 1.0 / rate if rate > 0 else 0
        
        if self.client_type in ['fiat', 'both']:
            # Mock данные для фиатных валют
            fiat_rates = {
                'EUR_USD': 0.93 + (hash('EUR') % 0.01),
                'GBP_USD': 0.79 + (hash('GBP') % 0.01),
                'RUB_USD': 0.011 + (hash('RUB') % 0.001),
                'JPY_USD': 0.0068 + (hash('JPY') % 0.0001),
                'CNY_USD': 0.14 + (hash('CNY') % 0.01),
            }
            
            # Добавляем обратные курсы
            for pair, rate in fiat_rates.items():
                rates[pair] = rate
                from_curr, to_curr = pair.split('_')
                reverse_pair = f"{to_curr}_{from_curr}"
                rates[reverse_pair] = 1.0 / rate if rate > 0 else 0
        
        # Добавляем случайные колебания
        import random
        for pair in list(rates.keys()):
            if random.random() < 0.3:  # 30% chance to fluctuate
                fluctuation = random.uniform(-0.02, 0.02)  # ±2%
                rates[pair] *= (1 + fluctuation)
        
        logger.info(f"Generated {len(rates)} mock rates")
        return rates
    
    def _generate_mock_data(self) -> Dict[str, Any]:
        """
        Генерирует реалистичные тестовые данные.
        
        Returns:
            Словарь с тестовыми данными
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'source': 'MockAPI',
            'note': 'This is mock data for testing'
        }
    
    def _validate_response(self, data: Dict[str, Any]) -> bool:
        """Всегда возвращает True для mock клиента."""
        return True


class ApiClientFactory:
    """Фабрика для создания API клиентов."""
    
    @staticmethod
    def create_client(config: ParserConfig, client_type: str = 'real') -> BaseApiClient:
        """
        Создает API клиент указанного типа.
        
        Args:
            config: Конфигурация
            client_type: Тип клиента ('coingecko', 'exchangerate', 'mock', 'all')
            
        Returns:
            Экземпляр API клиента
            
        Raises:
            ValueError: Если указан неизвестный тип клиента
        """
        client_type = client_type.lower()
        
        if client_type == 'coingecko':
            return CoinGeckoClient(config)
        elif client_type == 'exchangerate':
            return ExchangeRateApiClient(config)
        elif client_type == 'mock':
            return MockApiClient(config, 'both')
        elif client_type == 'mock_crypto':
            return MockApiClient(config, 'crypto')
        elif client_type == 'mock_fiat':
            return MockApiClient(config, 'fiat')
        elif client_type == 'all':
            # Возвращаем список всех реальных клиентов
            # (используется специальным образом в RatesUpdater)
            from valutatrade_hub.parser_service.updater import MultiApiClient
            return MultiApiClient(config, [
                CoinGeckoClient(config),
                ExchangeRateApiClient(config)
            ])
        else:
            raise ValueError(f"Unknown client type: {client_type}")
    
    @staticmethod
    def create_all_clients(config: ParserConfig) -> list:
        """
        Создает все доступные API клиенты.
        
        Returns:
            Список экземпляров API клиентов
        """
        clients = []
        
        # Пытаемся создать реальные клиенты, если есть ключи
        if config.EXCHANGERATE_API_KEY:
            clients.append(ExchangeRateApiClient(config))
        else:
            logger.warning("ExchangeRate-API key not set, using mock client for fiat")
            clients.append(MockApiClient(config, 'fiat'))
        
        if config.COINGECKO_API_KEY:
            clients.append(CoinGeckoClient(config))
        else:
            logger.warning("CoinGecko API key not set, using mock client for crypto")
            clients.append(MockApiClient(config, 'crypto'))
        
        return clients


class MultiApiClient(BaseApiClient):
    """
    Клиент, который объединяет несколько API клиентов.
    Позволяет получать данные из нескольких источников одновременно.
    """
    
    def __init__(self, config: ParserConfig, clients: list):
        """
        Args:
            config: Конфигурация
            clients: Список API клиентов
        """
        super().__init__(config)
        self.clients = clients
    
    def fetch_rates(self) -> Dict[str, float]:
        """
        Получает курсы от всех клиентов и объединяет их.
        
        Returns:
            Объединенный словарь курсов
        """
        all_rates = {}
        
        for client in self.clients:
            try:
                client_rates = client.fetch_rates()
                all_rates.update(client_rates)
                logger.info(f"Added {len(client_rates)} rates from {client.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to fetch rates from {client.__class__.__name__}: {e}")
                continue
        
        return all_rates
