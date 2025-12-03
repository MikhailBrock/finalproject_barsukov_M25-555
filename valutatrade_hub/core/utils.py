import re
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from valutatrade_hub.core.currencies import CurrencyRegistry

logger = logging.getLogger('valutatrade.utils')


class Validators:
    """Класс для валидации данных"""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """Валидация имени пользователя"""
        if not username or len(username.strip()) == 0:
            return False, "Username cannot be empty"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 50:
            return False, "Username cannot exceed 50 characters"
        
        # Разрешаем буквы, цифры, подчеркивания и точки
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            return False, "Username can only contain letters, numbers, dots, hyphens and underscores"
        
        return True, "Username is valid"
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Валидация пароля"""
        if not password or len(password.strip()) == 0:
            return False, "Password cannot be empty"
        
        if len(password) < 4:
            return False, "Password must be at least 4 characters long"
        
        if len(password) > 100:
            return False, "Password cannot exceed 100 characters"
        
        return True, "Password is valid"
    
    @staticmethod
    def validate_currency_code(currency_code: str) -> Tuple[bool, str]:
        """Валидация кода валюты"""
        if not currency_code or len(currency_code.strip()) == 0:
            return False, "Currency code cannot be empty"
        
        currency_code = currency_code.upper()
        
        # Проверка формата
        if not re.match(r'^[A-Z]{2,5}$', currency_code):
            return False, "Currency code must be 2-5 uppercase letters"
        
        # Проверка существования в реестре
        try:
            CurrencyRegistry.get_currency(currency_code)
            return True, "Currency code is valid"
        except Exception:
            return False, f"Unknown currency code: {currency_code}"
    
    @staticmethod
    def validate_amount(amount: Any) -> Tuple[bool, str]:
        """Валидация суммы"""
        try:
            amount_float = float(amount)
        except (ValueError, TypeError):
            return False, "Amount must be a number"
        
        if amount_float <= 0:
            return False, "Amount must be positive"
        
        if amount_float > 1_000_000_000:  # 1 миллиард
            return False, "Amount is too large"
        
        return True, "Amount is valid"
    
    @staticmethod
    def validate_currency_pair(from_currency: str, to_currency: str) -> Tuple[bool, str]:
        """Валидация пары валют"""
        # Проверка отдельных валют
        from_valid, from_msg = Validators.validate_currency_code(from_currency)
        if not from_valid:
            return False, from_msg
        
        to_valid, to_msg = Validators.validate_currency_code(to_currency)
        if not to_valid:
            return False, to_msg
        
        # Проверка что это не одна и та же валюта
        if from_currency.upper() == to_currency.upper():
            return False, "From and to currencies cannot be the same"
        
        return True, "Currency pair is valid"


class Formatters:
    """Класс для форматирования данных"""
    
    @staticmethod
    def format_currency(amount: float, currency_code: str) -> str:
        """Форматирование денежной суммы"""
        currency_code = currency_code.upper()
        
        # Определяем количество знаков после запятой в зависимости от валюты
        if currency_code in ['JPY', 'KRW']:
            # Для йен и вон обычно 0 знаков
            return f"{amount:,.0f} {currency_code}"
        elif currency_code in ['BTC', 'ETH']:
            # Для криптовалют больше знаков
            return f"{amount:.8f} {currency_code}"
        else:
            # Для большинства валют 2 знака
            return f"{amount:,.2f} {currency_code}"
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Форматирование даты и времени"""
        return dt.strftime(format_str)
    
    @staticmethod
    def format_timedelta(td: timedelta) -> str:
        """Форматирование временного интервала"""
        total_seconds = int(td.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def format_rate(rate: float, from_currency: str, to_currency: str) -> str:
        """Форматирование курса валюты"""
        if rate >= 1:
            return f"1 {from_currency} = {rate:.4f} {to_currency}"
        else:
            # Для очень маленьких курсов (типа BTC/USD)
            return f"1 {to_currency} = {1/rate:.4f} {from_currency}"


class Converters:
    """Класс для конвертации данных"""
    
    @staticmethod
    def convert_amount(amount: float, from_currency: str, to_currency: str, 
                      rates: Dict[str, float]) -> Optional[float]:
        """Конвертация суммы из одной валюты в другую"""
        if from_currency == to_currency:
            return amount
        
        # Прямой курс
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key in rates:
            return amount * rates[rate_key]
        
        # Обратный курс
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in rates:
            return amount / rates[reverse_key]
        
        # Попробуем через USD как промежуточную валюту
        usd_from_key = f"{from_currency}_USD"
        usd_to_key = f"{to_currency}_USD"
        
        if usd_from_key in rates and usd_to_key in rates:
            usd_amount = amount * rates[usd_from_key]
            return usd_amount / rates[usd_to_key]
        
        # Не смогли найти подходящий курс
        return None
    
    @staticmethod
    def normalize_currency_code(currency_code: str) -> str:
        """Нормализация кода валюты (в верхний регистр)"""
        return currency_code.strip().upper()
    
    @staticmethod
    def parse_currency_pair(pair_str: str) -> Tuple[Optional[str], Optional[str]]:
        """Парсинг строки пары валют (например, 'USD_EUR' -> ('USD', 'EUR'))"""
        if not pair_str or '_' not in pair_str:
            return None, None
        
        parts = pair_str.split('_')
        if len(parts) != 2:
            return None, None
        
        from_currency = parts[0].upper().strip()
        to_currency = parts[1].upper().strip()
        
        return from_currency, to_currency


class Security:
    """Класс для безопасности и защиты данных"""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Хеширование пароля с солью"""
        import hashlib
        import os
        
        if salt is None:
            salt = os.urandom(16).hex()
        
        # Используем SHA-256 с солью
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        
        # Дополнительная защита - повторное хеширование
        hashed = hashlib.sha256((hashed + salt).encode()).hexdigest()
        
        return hashed, salt
    
    @staticmethod
    def generate_api_key() -> str:
        """Генерация API ключа"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Санитизация пользовательского ввода"""
        import html
        
        # Экранирование HTML тегов
        sanitized = html.escape(input_str)
        
        # Удаление опасных символов
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        
        # Обрезка пробелов
        sanitized = sanitized.strip()
        
        return sanitized


class Cache:
    """Простой кэш в памяти"""
    
    _cache: Dict[str, Tuple[Any, datetime]] = {}
    
    @classmethod
    def set(cls, key: str, value: Any, ttl_seconds: int = 300):
        """Установка значения в кэш"""
        expiry_time = datetime.now() + timedelta(seconds=ttl_seconds)
        cls._cache[key] = (value, expiry_time)
        logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        if key not in cls._cache:
            return None
        
        value, expiry_time = cls._cache[key]
        
        if datetime.now() > expiry_time:
            # Срок действия истек
            del cls._cache[key]
            logger.debug(f"Cache expired: {key}")
            return None
        
        logger.debug(f"Cache hit: {key}")
        return value
    
    @classmethod
    def clear(cls):
        """Очистка кэша"""
        cls._cache.clear()
        logger.debug("Cache cleared")
    
    @classmethod
    def clear_expired(cls):
        """Очистка просроченных записей"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry_time) in cls._cache.items()
            if now > expiry_time
        ]
        
        for key in expired_keys:
            del cls._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired cache entries")
