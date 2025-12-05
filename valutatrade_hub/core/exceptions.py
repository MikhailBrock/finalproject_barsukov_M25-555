"""
Пользовательские исключения
"""


class InsufficientFundsError(Exception):
    """Недостаточно средств"""

    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available} {code}, "
            f"требуется {required} {code}"
        )


class CurrencyNotFoundError(Exception):
    """Неизвестная валюта"""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Сбой внешнего API"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class UserNotFoundError(Exception):
    """Пользователь не найден"""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Пользователь '{username}' не найден")


class AuthenticationError(Exception):
    """Ошибка аутентификации"""

    def __init__(self, message: str = "Неверный пароль"):
        super().__init__(message)
