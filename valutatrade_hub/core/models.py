import hashlib
import os
from datetime import datetime

class User:
    def __init__(self, user_id: int, username: str, hashed_password: str, 
                 salt: str, registration_date: datetime):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date
    
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def username(self) -> str:
        return self._username
    
    @username.setter
    def username(self, value: str):
        if not value or not value.strip():
            raise ValueError("Username cannot be empty")
        self._username = value
    
    def verify_password(self, password: str) -> bool:
        test_hash = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return test_hash == self._hashed_password
    
    def change_password(self, new_password: str):
        if len(new_password) < 4:
            raise ValueError("Password must be at least 4 characters long")
        
        self._salt = os.urandom(16).hex()
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode()
        ).hexdigest()
    
    def get_user_info(self) -> str:
        return (f"User ID: {self._user_id}, "
                f"Username: {self._username}, "
                f"Registered: {self._registration_date}")
                
class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = balance
    
    @property
    def balance(self) -> float:
        return self._balance
    
    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)):
            raise ValueError("Balance must be a number")
        if value < 0:
            raise ValueError("Balance cannot be negative")
        self._balance = value
    
    def deposit(self, amount: float):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
    
    def withdraw(self, amount: float):
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
    
    def get_balance_info(self) -> str:
        return f"{self.currency_code}: {self.balance:.2f}"
        
class Portfolio:
    def __init__(self, user_id: int, wallets: dict = None):
        self._user_id = user_id
        self._wallets = wallets or {}
    
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def wallets(self) -> dict:
        return self._wallets.copy()
    
    def add_currency(self, currency_code: str):
        if currency_code in self._wallets:
            raise ValueError(f"Wallet for {currency_code} already exists")
        self._wallets[currency_code] = Wallet(currency_code)
    
    def get_wallet(self, currency_code: str) -> Wallet:
        return self._wallets.get(currency_code)
    
    def get_total_value(self, base_currency: str = 'USD') -> float:
        # Временная заглушка для курсов
        exchange_rates = {
            'USD_USD': 1.0,
            'EUR_USD': 1.08,
            'BTC_USD': 50000.0,
        }
        
        total = 0.0
        for currency, wallet in self._wallets.items():
            if currency == base_currency:
                total += wallet.balance
            else:
                rate_key = f"{currency}_{base_currency}"
                if rate_key in exchange_rates:
                    total += wallet.balance * exchange_rates[rate_key]
        
        return total
