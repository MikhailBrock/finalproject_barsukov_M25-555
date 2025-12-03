import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.api_clients import BaseApiClient, ApiClientFactory
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.decorators import log_action, retry_on_failure, measure_performance


logger = logging.getLogger('valutatrade.parser')


class RatesUpdater:
    """
    Основной класс для обновления курсов валют.
    Координирует работу API клиентов и сохраняет данные.
    """
    
    def __init__(self, config: ParserConfig, storage: RatesStorage, 
                 clients: Optional[List[BaseApiClient]] = None):
        """
        Args:
            config: Конфигурация парсера
            storage: Хранилище для сохранения данных
            clients: Список API клиентов (если None, создаются автоматически)
        """
        self.config = config
        self.storage = storage
        self.clients = clients or ApiClientFactory.create_all_clients(config)
        
        self.last_update_time = None
        self.update_count = 0
        self.successful_updates = 0
        self.failed_updates = 0
        
        logger.info(f"RatesUpdater initialized with {len(self.clients)} clients")
    
    @log_action('UPDATE_RATES', verbose=True)
    @measure_performance(threshold_ms=10000)  # Предупреждение если дольше 10 секунд
    def run_update(self, parallel: bool = True) -> Dict[str, Any]:
        """
        Выполняет обновление курсов валют.
        
        Args:
            parallel: Если True, выполняет запросы параллельно
            
        Returns:
            Словарь с результатами обновления
        """
        logger.info("=" * 60)
        logger.info("STARTING RATES UPDATE")
        logger.info("=" * 60)
        
        start_time = time.time()
        self.last_update_time = datetime.now()
        self.update_count += 1
        
        try:
            # Получаем курсы от всех клиентов
            if parallel and len(self.clients) > 1:
                all_rates = self._fetch_rates_parallel()
            else:
                all_rates = self._fetch_rates_sequential()
            
            # Проверяем что получили хотя бы некоторые курсы
            if not all_rates:
                raise ApiRequestError("No rates fetched from any source")
            
            # Сохраняем курсы
            saved_count = self._save_rates(all_rates)
            
            # Формируем результат
            execution_time = time.time() - start_time
            result = self._create_update_result(all_rates, saved_count, execution_time)
            
            # Логируем успех
            self.successful_updates += 1
            logger.info("=" * 60)
            logger.info("RATES UPDATE COMPLETED SUCCESSFULLY")
            logger.info(f"Updated {saved_count} rates in {execution_time:.2f}s")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            # Логируем ошибку
            self.failed_updates += 1
            execution_time = time.time() - start_time
            
            logger.error("=" * 60)
            logger.error("RATES UPDATE FAILED")
            logger.error(f"Error: {e}")
            logger.error(f"Failed after {execution_time:.2f}s")
            logger.error("=" * 60)
            
            raise
    
    def _fetch_rates_sequential(self) -> Dict[str, float]:
        """
        Получает курсы от всех клиентов последовательно.
        
        Returns:
            Объединенный словарь курсов
        """
        all_rates = {}
        
        for client in self.clients:
            try:
                logger.info(f"Fetching rates from {client.__class__.__name__}...")
                
                client_rates = client.fetch_rates()
                all_rates.update(client_rates)
                
                logger.info(f"✓ {client.__class__.__name__}: {len(client_rates)} rates")
                
            except ApiRequestError as e:
                logger.error(f"✗ {client.__class__.__name__} failed: {e}")
                continue
            except Exception as e:
                logger.error(f"✗ Unexpected error from {client.__class__.__name__}: {e}")
                continue
        
        return all_rates
    
    def _fetch_rates_parallel(self) -> Dict[str, float]:
        """
        Получает курсы от всех клиентов параллельно.
        
        Returns:
            Объединенный словарь курсов
        """
        all_rates = {}
        
        with ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            # Запускаем все запросы параллельно
            future_to_client = {
                executor.submit(client.fetch_rates): client
                for client in self.clients
            }
            
            # Обрабатываем результаты по мере их поступления
            for future in as_completed(future_to_client):
                client = future_to_client[future]
                
                try:
                    client_rates = future.result(timeout=self.config.REQUEST_TIMEOUT + 5)
                    all_rates.update(client_rates)
                    logger.info(f"✓ {client.__class__.__name__}: {len(client_rates)} rates")
                    
                except ApiRequestError as e:
                    logger.error(f"✗ {client.__class__.__name__} failed: {e}")
                except TimeoutError:
                    logger.error(f"✗ {client.__class__.__name__} timeout")
                except Exception as e:
                    logger.error(f"✗ Unexpected error from {client.__class__.__name__}: {e}")
        
        return all_rates
    
    def _save_rates(self, rates: Dict[str, float]) -> int:
        """
        Сохраняет курсы в хранилище.
        
        Args:
            rates: Словарь курсов для сохранения
            
        Returns:
            Количество сохраненных курсов
        """
        try:
            # Форматируем курсы для сохранения
            formatted_rates = {}
            for rate_key, rate_value in rates.items():
                # Проверяем валидность курса
                if not self.config.is_valid_rate(rate_value):
                    logger.warning(f"Skipping invalid rate: {rate_key}={rate_value}")
                    continue
                
                # Форматируем запись
                formatted_rates[rate_key] = {
                    'rate': rate_value,
                    'updated_at': datetime.now().isoformat(),
                    'source': self._determine_source(rate_key)
                }
            
            # Сохраняем в основное хранилище
            saved_count = self.storage.save_current_rates(formatted_rates)
            
            # Сохраняем в историю
            history_saved = self.storage.save_to_history(formatted_rates)
            
            logger.info(f"Saved {saved_count} current rates and {history_saved} history records")
            return saved_count
            
        except Exception as e:
            logger.error(f"Failed to save rates: {e}")
            raise
    
    def _determine_source(self, rate_key: str) -> str:
        """
        Определяет источник данных для валютной пары.
        
        Args:
            rate_key: Ключ валютной пары (например, "BTC_USD")
            
        Returns:
            Имя источника
        """
        from_currency, to_currency = rate_key.split('_')[:2]
        
        # Определяем тип валют
        from_type = self._get_currency_type(from_currency)
        to_type = self._get_currency_type(to_currency)
        
        # Определяем источник на основе типов валют
        if from_type == 'crypto' or to_type == 'crypto':
            return 'CoinGecko'
        else:
            return 'ExchangeRate-API'
    
    def _get_currency_type(self, currency_code: str) -> str:
        """
        Определяет тип валюты (фиатная или крипто).
        
        Args:
            currency_code: Код валюты
            
        Returns:
            'fiat' или 'crypto'
        """
        from valutatrade_hub.core.currencies import CurrencyRegistry
        
        try:
            currency = CurrencyRegistry.get_currency(currency_code)
            return 'crypto' if hasattr(currency, 'algorithm') else 'fiat'
        except:
            # По умолчанию считаем фиатной
            return 'fiat'
    
    def _create_update_result(self, rates: Dict[str, float], 
                             saved_count: int, execution_time: float) -> Dict[str, Any]:
        """
        Создает словарь с результатами обновления.
        
        Args:
            rates: Полученные курсы
            saved_count: Количество сохраненных курсов
            execution_time: Время выполнения в секундах
            
        Returns:
            Словарь с результатами
        """
        # Анализируем полученные курсы
        crypto_rates = 0
        fiat_rates = 0
        
        for rate_key in rates.keys():
            if '_' in rate_key:
                from_currency = rate_key.split('_')[0]
                currency_type = self._get_currency_type(from_currency)
                
                if currency_type == 'crypto':
                    crypto_rates += 1
                else:
                    fiat_rates += 1
        
        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'execution_time_seconds': round(execution_time, 2),
            'total_rates_fetched': len(rates),
            'rates_saved': saved_count,
            'crypto_rates': crypto_rates,
            'fiat_rates': fiat_rates,
            'clients_used': len(self.clients),
            'update_count': self.update_count,
            'successful_updates': self.successful_updates,
            'failed_updates': self.failed_updates,
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Возвращает текущий статус обновления.
        
        Returns:
            Словарь со статусом
        """
        return {
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'update_count': self.update_count,
            'successful_updates': self.successful_updates,
            'failed_updates': self.failed_updates,
            'clients_count': len(self.clients),
            'clients': [client.__class__.__name__ for client in self.clients],
            'rates_ttl': self.config.RATES_TTL,
            'update_interval': self.config.UPDATE_INTERVAL,
        }
    
    def check_freshness(self) -> Dict[str, Any]:
        """
        Проверяет свежесть текущих курсов.
        
        Returns:
            Словарь с информацией о свежести
        """
        current_time = datetime.now()
        
        if not self.last_update_time:
            return {
                'is_fresh': False,
                'message': 'Never updated',
                'seconds_since_update': None,
                'ttl_seconds': self.config.RATES_TTL,
            }
        
        seconds_since_update = (current_time - self.last_update_time).total_seconds()
        is_fresh = seconds_since_update < self.config.RATES_TTL
        
        if is_fresh:
            message = f"Rates are fresh ({int(seconds_since_update)}s old)"
        else:
            message = f"Rates are outdated ({int(seconds_since_update)}s old)"
        
        return {
            'is_fresh': is_fresh,
            'message': message,
            'seconds_since_update': int(seconds_since_update),
            'ttl_seconds': self.config.RATES_TTL,
            'last_update_time': self.last_update_time.isoformat(),
        }
    
    def run_continuous(self, interval: Optional[int] = None):
        """
        Запускает непрерывное обновление с указанным интервалом.
        
        Args:
            interval: Интервал обновления в секундах (если None, используется из конфига)
        """
        if interval is None:
            interval = self.config.UPDATE_INTERVAL
        
        logger.info(f"Starting continuous updates every {interval} seconds")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                try:
                    self.run_update()
                except Exception as e:
                    logger.error(f"Update failed: {e}")
                
                # Ждем перед следующим обновлением
                logger.info(f"Next update in {interval} seconds...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Continuous updates stopped by user")
        except Exception as e:
            logger.error(f"Continuous updates stopped unexpectedly: {e}")
            raise
    
    @retry_on_failure(max_attempts=3, delay=10)
    def update_with_retry(self) -> Dict[str, Any]:
        """
        Выполняет обновление с повторными попытками при неудаче.
        
        Returns:
            Результаты обновления
        """
        return self.run_update()
