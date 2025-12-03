class InsufficientFundsError(Exception):
    def __init__(self, available: float, required: float, currency: str):
        self.available = available
        self.required = required
        self.currency = currency
        super().__init__(
            f"Insufficient funds: available {available:.4f} {currency}, "
            f"required {required:.4f} {currency}"
        )


class CurrencyNotFoundError(Exception):
    def __init__(self, currency_code: str):
        self.currency_code = currency_code
        super().__init__(f"Unknown currency '{currency_code}'")


class ApiRequestError(Exception):
    def __init__(self, reason: str, status_code: int = None):
        self.reason = reason
        self.status_code = status_code
        message = f"API request error: {reason}"
        if status_code:
            message += f" (status: {status_code})"
        super().__init__(message)


class AuthenticationError(Exception):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error in '{field}': {message}")


class PortfolioNotFoundError(Exception):
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Portfolio for user {user_id} not found")


class SessionError(Exception):
    def __init__(self, message: str = "Session error"):
        super().__init__(message)