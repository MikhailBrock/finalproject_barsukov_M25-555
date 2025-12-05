"""
Модели данных: User, Wallet, Portfolio
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional


class User:
    """Класс пользователя системы"""

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str,
        salt: Optional[str] = None,
        registration_date: Optional[datetime] = None,
    ):
        self._user_id = user_id
        self._username = username
        self._salt = salt or self._generate_salt()
        self._hashed_password = self._hash_password(password, self._salt)
        self._registration_date = registration_date or datetime.now()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def _generate_salt(self) -> str:
        """Генерирует соль для хеширования пароля"""
        import secrets

        return secrets.token_hex(8)

    def _hash_password(self, password: str, salt: str) -> str:
        """Хеширует пароль с солью"""
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        # Простое хеширование для демонстрации
        hash_input = (password + salt).encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()

    def change_password(self, new_password: str):
        """Изменяет пароль пользователя"""
        self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет введенный пароль"""
        test_hash = self._hash_password(password, self._salt)
        return test_hash == self._hashed_password

    def get_user_info(self) -> Dict[str, Any]:
        """Возвращает информацию о пользователе (без пароля)"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует пользователя в словарь"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Создает пользователя из словаря"""
        user = cls(
            user_id=data["user_id"],
            username=data["username"],
            password="dummy_password",  # Любой пароль, он перезапишется
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )
        # Восстанавливаем сохраненный хэш
        user._hashed_password = data["hashed_password"]
        return user


class Wallet:
    """Кошелек пользователя для одной конкретной валюты"""

    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = float(balance)

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        value = float(value)
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value

    def deposit(self, amount: float):
        """Пополнение баланса"""
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        self._balance += float(amount)

    def withdraw(self, amount: float):
        """Снятие средств"""
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")
        if amount > self._balance:
            raise ValueError(f"Недостаточно средств. Доступно: {self._balance}")
        self._balance -= float(amount)

    def get_balance_info(self) -> Dict[str, Any]:
        """Возвращает информацию о балансе"""
        return {"currency_code": self.currency_code, "balance": self._balance}

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует кошелек в словарь"""
        return {"currency_code": self.currency_code, "balance": self._balance}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Wallet":
        """Создает кошелек из словаря"""
        return cls(currency_code=data["currency_code"], balance=data["balance"])


class Portfolio:
    """Управление всеми кошельками одного пользователя"""

    def __init__(self, user_id: int, wallets: Optional[Dict[str, Wallet]] = None):
        self._user_id = user_id
        self._wallets = wallets or {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелек в портфель"""
        currency_code = currency_code.upper()
        if currency_code in self._wallets:
            raise ValueError(f"Кошелек для валюты {currency_code} уже существует")

        wallet = Wallet(currency_code)
        self._wallets[currency_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """Возвращает кошелек по коду валюты"""
        currency_code = currency_code.upper()
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Возвращает общую стоимость всех валют в базовой валюте"""
        # Для демонстрации используем фиксированные курсы
        exchange_rates = {
            "USD_USD": 1.0,
            "EUR_USD": 1.0786,
            "BTC_USD": 59337.21,
            "RUB_USD": 0.01016,
            "ETH_USD": 3720.00,
            "GBP_USD": 1.25,
        }

        total = 0.0
        base_currency = base_currency.upper()

        for wallet in self._wallets.values():
            if wallet.currency_code == base_currency:
                total += wallet.balance
            else:
                pair = f"{wallet.currency_code}_{base_currency}"
                if pair in exchange_rates:
                    total += wallet.balance * exchange_rates[pair]
                else:
                    # Если курса нет, считаем по цепочке через USD
                    usd_pair = f"{wallet.currency_code}_USD"
                    if usd_pair in exchange_rates:
                        usd_value = wallet.balance * exchange_rates[usd_pair]
                        total += usd_value

        return total

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует портфель в словарь"""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: wallet.to_dict() for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Portfolio":
        """Создает портфель из словаря"""
        wallets = {}
        for code, wallet_data in data["wallets"].items():
            wallets[code] = Wallet.from_dict(wallet_data)

        return cls(user_id=data["user_id"], wallets=wallets)
