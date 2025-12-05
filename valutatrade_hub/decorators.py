"""
Декораторы для логирования операций
"""

import functools
from datetime import datetime
from typing import Callable

from .infra.database import DatabaseManager
from .logging_config import logger


def log_action(action: str, verbose: bool = False):
    """
    Декоратор для логирования действий пользователя

    Args:
        action: Название действия (BUY, SELL, REGISTER, LOGIN и т.д.)
        verbose: Подробное логирование с состоянием кошелька
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Пытаемся извлечь информацию о пользователе
            user_id = None
            username = None
            result = "OK"
            error_info = None
            # additional_info = ""

            try:
                # Извлекаем user_id из аргументов
                for arg in args:
                    if isinstance(arg, int) and arg > 0:
                        user_id = arg
                        break

                # Или из kwargs
                if not user_id:
                    user_id = kwargs.get("user_id")

                # Получаем имя пользователя по ID
                if user_id:
                    db = DatabaseManager()
                    users = db.load_users()
                    user = users.get(user_id)
                    if user:
                        username = user.username

                # Выполняем функцию
                result_value = func(*args, **kwargs)

                # Логируем успешное выполнение
                log_data = {
                    "action": action,
                    "user_id": user_id,
                    "username": username,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                }

                # Добавляем дополнительные поля из kwargs
                for key in ["currency_code", "amount", "rate", "base"]:
                    if key in kwargs:
                        log_data[key] = kwargs[key]

                # Если нужно подробное логирование
                if verbose and user_id:
                    db = DatabaseManager()
                    portfolio = db.get_portfolio_by_user_id(user_id)
                    if portfolio:
                        wallets_info = {
                            code: wallet.balance
                            for code, wallet in portfolio.wallets.items()
                        }
                        log_data["wallets_state"] = wallets_info

                logger.info(f"Action logged: {log_data}")

                return result_value

            except Exception as e:
                # Логируем ошибку
                result = "ERROR"
                error_info = {"type": e.__class__.__name__, "message": str(e)}

                log_data = {
                    "action": action,
                    "user_id": user_id,
                    "username": username,
                    "result": result,
                    "error": error_info,
                    "timestamp": datetime.now().isoformat(),
                }

                # Добавляем дополнительные поля из kwargs
                for key in ["currency_code", "amount", "rate", "base"]:
                    if key in kwargs:
                        log_data[key] = kwargs[key]

                logger.error(f"Action failed: {log_data}")

                # Пробрасываем исключение дальше
                raise

        return wrapper

    return decorator
