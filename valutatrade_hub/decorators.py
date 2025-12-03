import functools
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from valutatrade_hub.infra.settings import SettingsLoader

logger = logging.getLogger('valutatrade.decorators')
settings = SettingsLoader()


def log_action(action_name: Optional[str] = None, verbose: bool = False):
    """
    Декоратор для логирования действий пользователя.
    
    Args:
        action_name: Имя действия (если None, используется имя функции)
        verbose: Если True, логирует дополнительные детали
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Получаем имя действия
            action = action_name or func.__name__.upper()
            
            # Подготавливаем контекст для логирования
            log_context: Dict[str, Any] = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'function': func.__name__,
                'module': func.__module__,
            }
            
            # Извлекаем user_id из аргументов если возможно
            if args and len(args) > 0:
                # Первый аргумент часто self, второй может быть user_id
                if len(args) > 1 and isinstance(args[1], (int, str)):
                    log_context['user_id'] = args[1]
                elif hasattr(args[0], 'current_user'):
                    # Если это метод класса с current_user
                    current_user = getattr(args[0], 'current_user', None)
                    if current_user and hasattr(current_user, 'user_id'):
                        log_context['user_id'] = current_user.user_id
            
            # Добавляем важные аргументы из kwargs
            important_keys = ['username', 'currency', 'currency_code', 'amount', 
                            'from_currency', 'to_currency', 'base_currency']
            for key in important_keys:
                if key in kwargs and kwargs[key] is not None:
                    log_context[key] = kwargs[key]
            
            # Замер времени выполнения
            start_time = time.time()
            
            try:
                # Выполняем функцию
                result = func(*args, **kwargs)
                
                # Добавляем информацию о результате
                log_context['execution_time_ms'] = int((time.time() - start_time) * 1000)
                log_context['result'] = 'SUCCESS'
                
                if verbose:
                    log_context['details'] = str(result)[:200]  # Ограничиваем длину
                
                # Логируем успех
                logger.info(f"Action completed: {log_context}")
                return result
                
            except Exception as e:
                # Логируем ошибку
                log_context['execution_time_ms'] = int((time.time() - start_time) * 1000)
                log_context['result'] = 'ERROR'
                log_context['error_type'] = type(e).__name__
                log_context['error_message'] = str(e)
                
                # Дополнительная информация для некоторых типов ошибок
                if hasattr(e, 'available') and hasattr(e, 'required'):
                    log_context['available'] = getattr(e, 'available')
                    log_context['required'] = getattr(e, 'required')
                
                logger.error(f"Action failed: {log_context}")
                raise
        
        return wrapper
    return decorator


def validate_input(validators: Dict[str, Callable]):
    """
    Декоратор для валидации входных параметров функции.
    
    Args:
        validators: Словарь {имя_параметра: функция_валидации}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from valutatrade_hub.core.exceptions import ValidationError
            
            # Получаем сигнатуру функции для определения параметров
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Валидируем каждый параметр
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    try:
                        validator(value)
                    except Exception as e:
                        raise ValidationError(param_name, str(e))
            
            # Выполняем функцию
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, 
                    exceptions: tuple = (Exception,)):
    """
    Декоратор для повторных попыток при неудачном выполнении.
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Задержка между попытками в секундах
        exceptions: Кортеж исключений, при которых повторять
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: "
                            f"{str(e)[:100]}. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: "
                            f"{str(e)}"
                        )
            
            # Все попытки провалились
            raise last_exception
        
        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 300, maxsize: int = 128):
    """
    Декоратор для кэширования результатов функции.
    
    Args:
        ttl_seconds: Время жизни кэша в секундах
        maxsize: Максимальный размер кэша
    """
    def decorator(func: Callable) -> Callable:
        cache: Dict[str, tuple] = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from valutatrade_hub.core.utils import Cache
            
            # Создаем ключ кэша на основе аргументов
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = '|'.join(key_parts)
            
            # Проверяем кэш
            cached_result = Cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            Cache.set(cache_key, result, ttl_seconds)
            
            # Ограничиваем размер кэша
            if len(Cache._cache) > maxsize:
                # Удаляем самые старые записи
                oldest_keys = sorted(
                    Cache._cache.keys(),
                    key=lambda k: Cache._cache[k][1]
                )[:len(Cache._cache) - maxsize]
                for old_key in oldest_keys:
                    del Cache._cache[old_key]
            
            return result
        
        return wrapper
    return decorator


def measure_performance(threshold_ms: int = 1000):
    """
    Декоратор для измерения производительности функции.
    
    Args:
        threshold_ms: Порог для предупреждения о медленной работе (мс)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            result = func(*args, **kwargs)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            if execution_time_ms > threshold_ms:
                logger.warning(
                    f"Slow performance detected in {func.__name__}: "
                    f"{execution_time_ms:.2f}ms (threshold: {threshold_ms}ms)"
                )
            else:
                logger.debug(
                    f"{func.__name__} executed in {execution_time_ms:.2f}ms"
                )
            
            return result
        
        return wrapper
    return decorator


def require_authentication():
    """
    Декоратор для проверки аутентификации пользователя.
    Требует, чтобы у self был current_user.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            from valutatrade_hub.core.exceptions import AuthenticationError
            
            if not hasattr(self, 'current_user') or self.current_user is None:
                raise AuthenticationError("User must be authenticated")
            
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


def transactional():
    """
    Декоратор для выполнения операций в транзакции.
    В случае ошибки откатывает изменения в базе данных.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from valutatrade_hub.infra.database import DatabaseManager
            
            db = DatabaseManager()
            
            try:
                # Создаем backup текущего состояния
                backup_data = {}
                for filename in ['users.json', 'portfolios.json', 'rates.json']:
                    filepath = db.data_dir / filename
                    if filepath.exists():
                        with open(filepath, 'r', encoding='utf-8') as f:
                            backup_data[filename] = json.loads(f.read())
                
                # Выполняем функцию
                result = func(*args, **kwargs)
                
                logger.debug(f"Transaction completed successfully: {func.__name__}")
                return result
                
            except Exception as e:
                # Восстанавливаем из backup
                logger.error(f"Transaction failed, rolling back: {func.__name__} - {e}")
                
                for filename, data in backup_data.items():
                    filepath = db.data_dir / filename
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                
                raise
        
        return wrapper
    return decorator


def rate_limit(requests_per_minute: int = 60):
    """
    Декоратор для ограничения частоты вызовов функции.
    
    Args:
        requests_per_minute: Максимальное количество запросов в минуту
    """
    import threading
    
    calls = []
    lock = threading.Lock()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal calls
            
            with lock:
                now = time.time()
                
                # Удаляем старые записи (старше 1 минуты)
                calls = [call_time for call_time in calls 
                        if now - call_time < 60]
                
                # Проверяем лимит
                if len(calls) >= requests_per_minute:
                    wait_time = 60 - (now - calls[0])
                    if wait_time > 0:
                        raise Exception(
                            f"Rate limit exceeded. Try again in {wait_time:.1f} seconds."
                        )
                
                # Добавляем текущий вызов
                calls.append(now)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def deprecated(new_function: Optional[str] = None):
    """
    Декоратор для пометки устаревших функций.
    
    Args:
        new_function: Имя новой функции, если есть замена
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warning_msg = f"Function {func.__name__} is deprecated."
            if new_function:
                warning_msg += f" Use {new_function} instead."
            
            logger.warning(warning_msg)
            print(f"{warning_msg}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def debug_trace():
    """
    Декоратор для отладки, который выводит информацию о вызове функции.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"DEBUG: Calling {func.__name__}")
            print(f"   Args: {args}")
            print(f"   Kwargs: {kwargs}")
            
            result = func(*args, **kwargs)
            
            print(f"DEBUG: {func.__name__} returned: {result}")
            return result
        
        return wrapper
    return decorator