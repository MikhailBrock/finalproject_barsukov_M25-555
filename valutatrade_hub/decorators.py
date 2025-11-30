import functools
import logging
from datetime import datetime
from typing import Any, Callable

def log_action(action_name: str = None, verbose: bool = False):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger('valutatrade.actions')
            
            # Получаем имя действия
            action = action_name or func.__name__.upper()
            
            # Подготавливаем контекст для логирования
            log_context = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'function': func.__name__,
            }
            
            try:
                # Добавляем аргументы в контекст
                if args and len(args) > 1:
                    log_context['user_id'] = args[1] if len(args) > 1 else 'unknown'
                
                if 'currency_code' in kwargs:
                    log_context['currency'] = kwargs['currency_code']
                if 'amount' in kwargs:
                    log_context['amount'] = kwargs['amount']
                
                # Выполняем функцию
                result = func(*args, **kwargs)
                
                # Логируем успех
                log_context['result'] = 'OK'
                if verbose:
                    log_context['details'] = str(result)
                
                logger.info(f"Action completed: {log_context}")
                return result
                
            except Exception as e:
                # Логируем ошибку
                log_context['result'] = 'ERROR'
                log_context['error_type'] = type(e).__name__
                log_context['error_message'] = str(e)
                
                logger.error(f"Action failed: {log_context}")
                raise
        
        return wrapper
    return decorator