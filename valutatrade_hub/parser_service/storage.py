import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from uuid import uuid4

from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.core.currencies import CurrencyRegistry


logger = logging.getLogger('valutatrade.parser.storage')


class RatesStorage:
    """
    Класс для работы с хранилищем курсов валют.
    Управляет как текущими курсами, так и историческими данными.
    """
    
    def __init__(self, config: ParserConfig):
        """
        Args:
            config: Конфигурация парсера
        """
        self.config = config
        self.db = DatabaseManager()
        
        # Пути к файлам
        self.rates_file = Path(self.config.RATES_FILE_PATH)
        self.history_file = Path(self.config.HISTORY_FILE_PATH)
        
        # Создаем директории если нужно
        self.rates_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("RatesStorage initialized")
        logger.info(f"  Current rates: {self.rates_file}")
        logger.info(f"  History: {self.history_file}")
    
    def save_current_rates(self, rates: Dict[str, Dict[str, Any]]) -> int:
        """
        Сохраняет текущие курсы валют в основное хранилище.
        
        Args:
            rates: Словарь курсов в формате {pair: {rate: float, updated_at: str, source: str}}
            
        Returns:
            Количество сохраненных курсов
        """
        try:
            # Загружаем существующие курсы
            existing_rates = self.load_current_rates()
            
            # Обновляем или добавляем новые курсы
            updated_count = 0
            for pair, rate_data in rates.items():
                # Проверяем валидность пары
                if not self._is_valid_currency_pair(pair):
                    logger.warning(f"Invalid currency pair: {pair}")
                    continue
                
                # Проверяем свежесть данных
                if self._should_update_rate(pair, rate_data, existing_rates):
                    existing_rates[pair] = rate_data
                    updated_count += 1
            
            # Сохраняем обновленные курсы
            rates_data = {
                'pairs': existing_rates,
                'last_refresh': datetime.now().isoformat(),
                'source': 'ParserService',
                'total_pairs': len(existing_rates),
            }
            
            # Сохраняем через DatabaseManager
            self.db.save_exchange_rates(existing_rates)
            
            # Также сохраняем в файл для совместимости
            self._save_to_file(self.rates_file, rates_data)
            
            logger.info(f"Saved {updated_count} current rates (total: {len(existing_rates)})")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to save current rates: {e}")
            raise
    
    def load_current_rates(self) -> Dict[str, Dict[str, Any]]:
        """
        Загружает текущие курсы валют.
        
        Returns:
            Словарь текущих курсов
        """
        try:
            # Пробуем загрузить из DatabaseManager
            rates = self.db.get_exchange_rates()
            
            if rates:
                logger.debug(f"Loaded {len(rates)} rates from database")
                return rates
            
            # Если в базе нет, пробуем загрузить из файла
            if self.rates_file.exists():
                with open(self.rates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                rates = data.get('pairs', {})
                logger.debug(f"Loaded {len(rates)} rates from file")
                return rates
            
            # Если файла нет, возвращаем пустой словарь
            return {}
            
        except Exception as e:
            logger.error(f"Failed to load current rates: {e}")
            return {}
    
    def save_to_history(self, rates: Dict[str, Dict[str, Any]]) -> int:
        """
        Сохраняет курсы в историческое хранилище.
        
        Args:
            rates: Словарь курсов для сохранения в историю
            
        Returns:
            Количество сохраненных исторических записей
        """
        try:
            saved_count = 0
            
            for pair, rate_data in rates.items():
                # Создаем историческую запись
                history_record = self._create_history_record(pair, rate_data)
                
                # Сохраняем через DatabaseManager
                self.db.save_exchange_rate_history(history_record)
                saved_count += 1
            
            logger.debug(f"Saved {saved_count} records to history")
            return saved_count
            
        except Exception as e:
            logger.error(f"Failed to save to history: {e}")
            return 0
    
    def load_history(self, from_currency: Optional[str] = None,
                    to_currency: Optional[str] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """
        Загружает исторические данные о курсах валют.
        
        Args:
            from_currency: Фильтр по исходной валюте
            to_currency: Фильтр по целевой валюте
            limit: Максимальное количество записей
            
        Returns:
            Список исторических записей
        """
        return self.db.get_exchange_rate_history(from_currency, to_currency, limit)
    
    def get_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Получает текущий курс для пары валют.
        
        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            
        Returns:
            Курс или None если не найден
        """
        return self.db.get_exchange_rate(from_currency, to_currency)
    
    def get_all_rates(self) -> Dict[str, Dict[str, Any]]:
        """
        Получает все текущие курсы.
        
        Returns:
            Словарь всех курсов
        """
        return self.load_current_rates()
    
    def cleanup_old_history(self, days_to_keep: int = 30) -> int:
        """
        Удаляет старые исторические записи.
        
        Args:
            days_to_keep: Количество дней для хранения
            
        Returns:
            Количество удаленных записей
        """
        try:
            # Загружаем всю историю
            all_history = self.load_history()
            
            if not all_history:
                return 0
            
            # Фильтруем старые записи
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            filtered_history = []
            deleted_count = 0
            
            for record in all_history:
                timestamp_str = record.get('timestamp')
                if not timestamp_str:
                    continue
                
                try:
                    record_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    record_timestamp = record_time.timestamp()
                    
                    if record_timestamp > cutoff_date:
                        filtered_history.append(record)
                    else:
                        deleted_count += 1
                except Exception:
                    # Если не можем распарсить timestamp, сохраняем запись
                    filtered_history.append(record)
            
            # Сохраняем отфильтрованную историю
            if deleted_count > 0:
                self._save_history_to_file(filtered_history)
                logger.info(f"Cleaned up {deleted_count} old history records (older than {days_to_keep} days)")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old history: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику хранилища.
        
        Returns:
            Словарь со статистикой
        """
        current_rates = self.load_current_rates()
        history = self.load_history(limit=1000)  # Первые 1000 записей для оценки
        
        # Размер файлов
        rates_file_size = self.rates_file.stat().st_size if self.rates_file.exists() else 0
        history_file_size = self.history_file.stat().st_size if self.history_file.exists() else 0
        
        # Анализ валют
        currency_pairs = list(current_rates.keys())
        crypto_pairs = [p for p in currency_pairs if self._is_crypto_pair(p)]
        fiat_pairs = [p for p in currency_pairs if not self._is_crypto_pair(p)]
        
        # Время последнего обновления
        last_refresh = None
        if self.rates_file.exists():
            try:
                with open(self.rates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                last_refresh = data.get('last_refresh')
            except:
                pass
        
        return {
            'current_rates_count': len(current_rates),
            'history_records_count': len(history),
            'crypto_pairs_count': len(crypto_pairs),
            'fiat_pairs_count': len(fiat_pairs),
            'rates_file_size_kb': round(rates_file_size / 1024, 2),
            'history_file_size_kb': round(history_file_size / 1024, 2),
            'last_refresh': last_refresh,
            'storage_path': str(self.rates_file.parent.absolute()),
        }
    
    def _create_history_record(self, pair: str, rate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает историческую запись для курса валюты.
        
        Args:
            pair: Валютная пара (например, "BTC_USD")
            rate_data: Данные о курсе
            
        Returns:
            Историческая запись
        """
        from_currency, to_currency = pair.split('_')[:2]
        
        return {
            'id': str(uuid4()),
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate_data.get('rate'),
            'timestamp': rate_data.get('updated_at', datetime.now().isoformat()),
            'source': rate_data.get('source', 'Unknown'),
            'pair': pair,
            'meta': {
                'record_type': 'exchange_rate',
                'created_at': datetime.now().isoformat(),
            }
        }
    
    def _should_update_rate(self, pair: str, new_rate_data: Dict[str, Any], 
                           existing_rates: Dict[str, Dict[str, Any]]) -> bool:
        """
        Определяет, нужно ли обновлять курс.
        
        Args:
            pair: Валютная пара
            new_rate_data: Новые данные о курсе
            existing_rates: Существующие курсы
            
        Returns:
            True если нужно обновить
        """
        if pair not in existing_rates:
            return True
        
        existing_rate = existing_rates[pair]
        existing_timestamp = existing_rate.get('updated_at')
        new_timestamp = new_rate_data.get('updated_at')
        
        if not existing_timestamp or not new_timestamp:
            return True
        
        try:
            # Сравниваем время обновления
            existing_time = datetime.fromisoformat(existing_timestamp.replace('Z', '+00:00'))
            new_time = datetime.fromisoformat(new_timestamp.replace('Z', '+00:00'))
            
            # Обновляем если новые данные свежее
            return new_time > existing_time
            
        except Exception:
            # Если не можем сравнить время, обновляем
            return True
    
    def _is_valid_currency_pair(self, pair: str) -> bool:
        """
        Проверяет валидность валютной пары.
        
        Args:
            pair: Валютная пара (например, "BTC_USD")
            
        Returns:
            True если пара валидна
        """
        if '_' not in pair:
            return False
        
        parts = pair.split('_')
        if len(parts) != 2:
            return False
        
        from_currency, to_currency = parts
        
        # Проверяем что обе валюты существуют
        try:
            CurrencyRegistry.get_currency(from_currency)
            CurrencyRegistry.get_currency(to_currency)
            return True
        except:
            return False
    
    def _is_crypto_pair(self, pair: str) -> bool:
        """
        Определяет, является ли пара криптовалютной.
        
        Args:
            pair: Валютная пара
            
        Returns:
            True если это криптовалютная пара
        """
        if '_' not in pair:
            return False
        
        from_currency = pair.split('_')[0]
        
        try:
            currency = CurrencyRegistry.get_currency(from_currency)
            return hasattr(currency, 'algorithm')  # Криптовалюты имеют алгоритм
        except:
            return False
    
    def _save_to_file(self, filepath: Path, data: Dict[str, Any]):
        """
        Сохраняет данные в файл.
        
        Args:
            filepath: Путь к файлу
            data: Данные для сохранения
        """
        try:
            # Создаем временный файл для атомарной записи
            temp_filepath = filepath.with_suffix('.tmp')
            
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Атомарно заменяем старый файл новым
            temp_filepath.replace(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save to file {filepath}: {e}")
            raise
    
    def _save_history_to_file(self, history: List[Dict[str, Any]]):
        """
        Сохраняет исторические данные в файл.
        
        Args:
            history: Список исторических записей
        """
        try:
            self._save_to_file(self.history_file, history)
        except Exception as e:
            logger.error(f"Failed to save history to file: {e}")
    
    def backup(self, backup_dir: str = "backups") -> str:
        """
        Создает резервную копию данных.
        
        Args:
            backup_dir: Директория для бэкапов
            
        Returns:
            Путь к созданному бэкапу
        """
        try:
            import zipfile
            from datetime import datetime
            
            # Создаем директорию для бэкапов
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Генерируем имя файла с timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"rates_backup_{timestamp}.zip"
            
            # Создаем zip архив
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Добавляем файлы
                if self.rates_file.exists():
                    zipf.write(self.rates_file, self.rates_file.name)
                
                if self.history_file.exists():
                    zipf.write(self.history_file, self.history_file.name)
            
            logger.info(f"Created backup: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return ""
