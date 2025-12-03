import hashlib
import os
from datetime import datetime
from typing import Dict, Optional
from valutatrade_hub.core.exceptions import InsufficientFundsError


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
    
    @property
    def hashed_password(self) -> str:
        return self._hashed_password
    
    @property
    def salt(self) -> str:
        return self._salt
    
    @property
    def registration_date(self) -> datetime:
        return self._registration_date
    
    def verify_password(self, password: str) -> bool:
        """Проверяет пароль пользователя"""
        test_hash = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return test_hash == self._hashed_password
    
    def change_password(self, new_password: str):
        """Изменяет пароль пользователя"""
        if len(new_password) < 4:
            raise ValueError("Password must be at least 4 characters long")
        
        self._salt = os.urandom(16).hex()
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode()
        ).hexdigest()
    
    def get_user_info(self) -> str:
        """Возвращает информацию о пользователе"""
        return (f"User ID: {self._user_id}, "
                f"Username: {self._username}, "
                f"Registered: {self._registration_date}")
    
    def to_dict(self) -> dict:
        """Конвертирует объект User в словарь для JSON"""
        return {
            'user_id': self._user_id,
            'username': self._username,
            'hashed_password': self._hashed_password,
            'salt': self._salt,
            'registration_date': self._registration_date.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создает объект User из словаря"""
        return cls(
            user_id=data['user_id'],
            username=data['username'],
            hashed_password=data['hashed_password'],
            salt=data['salt'],
            registration_date=datetime.fromisoformat(data['registration_date'])
        )


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self._currency_code = currency_code
        self._balance = balance
    
    @property
    def currency_code(self) -> str:
        return self._currency_code
    
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
        """Пополнение баланса"""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
    
    def withdraw(self, amount: float):
        """Снятие средств"""
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise InsufficientFundsError(self.balance, amount, self.currency_code)
        self.balance -= amount
    
    def get_balance_info(self) -> str:
        """Информация о балансе"""
        return f"{self._currency_code}: {self._balance:.2f}"
    
    def to_dict(self) -> dict:
        """Конвертирует объект Wallet в словарь для JSON"""
        return {
            'currency_code': self._currency_code,
            'balance': self._balance
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Wallet':
        """Создает объект Wallet из словаря"""
        return cls(
            currency_code=data['currency_code'],
            balance=data['balance']
        )


class Portfolio:
    def __init__(self, user_id: int, wallets: Dict[str, Wallet] = None):
        self._user_id = user_id
        self._wallets = wallets or {}
    
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()
    
    def add_wallet(self, currency_code: str, initial_balance: float = 0.0) -> Wallet:
        """Добавляет новый кошелек в портфель"""
        if currency_code in self._wallets:
            raise ValueError(f"Wallet for {currency_code} already exists")
        
        wallet = Wallet(currency_code, initial_balance)
        self._wallets[currency_code] = wallet
        return wallet
    
    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """Возвращает кошелек по коду валюты"""
        return self._wallets.get(currency_code)
    
    def get_total_value(self, base_currency: str = 'USD', 
                       exchange_rates: Dict[str, float] = None) -> float:
        """Рассчитывает общую стоимость портфеля в базовой валюте"""
        if exchange_rates is None:
            exchange_rates = {}
        
        total = 0.0
        for currency, wallet in self._wallets.items():
            if currency == base_currency:
                total += wallet.balance
            else:
                rate_key = f"{currency}_{base_currency}"
                if rate_key in exchange_rates:
                    total += wallet.balance * exchange_rates[rate_key]
                else:
                    # Обратная пара
                    reverse_key = f"{base_currency}_{currency}"
                    if reverse_key in exchange_rates:
                        total += wallet.balance / exchange_rates[reverse_key]
        
        return total
    
    def to_dict(self) -> dict:
        """Конвертирует объект Portfolio в словарь для JSON"""
        return {
            'user_id': self._user_id,
            'wallets': {code: wallet.to_dict() 
                       for code, wallet in self._wallets.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        """Создает объект Portfolio из словаря"""
        wallets = {}
        for code, wallet_data in data.get('wallets', {}).items():
            wallets[code] = Wallet.from_dict(wallet_data)
        
        return cls(
            user_id=data['user_id'],
            wallets=wallets
        )