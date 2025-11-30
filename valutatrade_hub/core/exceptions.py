class InsufficientFundsError(Exception):
    def __init__(self, available: float, required: float, currency: str):
        self.available = available
        self.required = required
        self.currency = currency
        super().__init__(f"Insufficient funds: available {available:.4f} {currency}, required {required:.4f} {currency}")

class CurrencyNotFoundError(Exception):
    def __init__(self, currency_code: str):
        self.currency_code = currency_code
        super().__init__(f"Unknown currency '{currency_code}'")

class ApiRequestError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"API request error: {reason}")