"""
Бизнес-логика приложения
"""

from typing import Any, Dict

from ..decorators import log_action
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader
from .currencies import get_currency
from .exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    UserNotFoundError,
)
from .models import User
from .utils import is_rate_fresh, validate_amount, validate_currency_code


class UseCases:
    """Класс с бизнес-логикой приложения"""

    def __init__(self):
        self.db = DatabaseManager()
        self.settings = SettingsLoader()

    @log_action("REGISTER", verbose=True)
    def register_user(self, username: str, password: str) -> User:
        """Регистрирует нового пользователя"""
        # Проверяем уникальность имени
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

        # Проверяем длину пароля
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        # Создаем пользователя
        user_id = self.db.get_next_user_id()
        user = User(user_id, username, password)

        # Сохраняем пользователя
        self.db.save_user(user)

        # Создаем пустой портфель
        self.db.create_user_portfolio(user_id)

        return user

    @log_action("LOGIN")
    def login_user(self, username: str, password: str) -> User:
        """Аутентифицирует пользователя"""
        user = self.db.get_user_by_username(username)
        if not user:
            raise UserNotFoundError(username)

        if not user.verify_password(password):
            raise AuthenticationError()

        return user

    @log_action("GET_PORTFOLIO", verbose=True)
    def get_user_portfolio(
        self, user_id: int, base_currency: str = "USD"
    ) -> Dict[str, Any]:
        """Возвращает портфель пользователя с конвертацией в базовую валюту"""
        portfolio = self.db.get_portfolio_by_user_id(user_id)
        if not portfolio:
            raise ValueError("Портфель не найден")

        # Получаем пользователя для имени
        users = self.db.load_users()
        user = users.get(user_id)
        username = user.username if user else f"user_{user_id}"

        # Получаем текущие курсы
        rates = self.db.load_rates()

        # Рассчитываем стоимость каждого кошелька
        wallet_values = []
        total_value = 0.0

        for currency_code, wallet in portfolio.wallets.items():
            wallet_info = {
                "currency_code": currency_code,
                "balance": wallet.balance,
                "value_in_base": 0.0,
            }

            # Конвертируем в базовую валюту
            if currency_code == base_currency:
                value = wallet.balance
            else:
                pair = f"{currency_code}_{base_currency}"
                if pair in rates.get("pairs", {}):
                    rate = rates["pairs"][pair]["rate"]
                    value = wallet.balance * rate
                else:
                    # Попробуем через USD
                    usd_pair = f"{currency_code}_USD"
                    if usd_pair in rates.get("pairs", {}):
                        usd_rate = rates["pairs"][usd_pair]["rate"]
                        usd_value = wallet.balance * usd_rate

                        # Конвертируем USD в базовую валюту
                        if base_currency != "USD":
                            base_pair = f"USD_{base_currency}"
                            if base_pair in rates.get("pairs", {}):
                                base_rate = rates["pairs"][base_pair]["rate"]
                                value = usd_value * base_rate
                            else:
                                value = 0.0
                        else:
                            value = usd_value
                    else:
                        value = 0.0

            wallet_info["value_in_base"] = value
            wallet_values.append(wallet_info)
            total_value += value

        return {
            "user_id": user_id,
            "username": username,
            "base_currency": base_currency,
            "wallets": wallet_values,
            "total_value": total_value,
        }

    @log_action("BUY", verbose=True)
    def buy_currency(
        self, user_id: int, currency_code: str, amount: float
    ) -> Dict[str, Any]:
        """Покупает валюту"""
        # Валидация входных данных
        currency_code = validate_currency_code(currency_code)
        amount = validate_amount(amount)

        # Получаем портфель пользователя
        portfolio = self.db.get_portfolio_by_user_id(user_id)
        if not portfolio:
            portfolio = self.db.create_user_portfolio(user_id)

        # Проверяем наличие валюты в реестре
        try:
            currency = get_currency(currency_code)
            print(f"Валюта: {currency}")
        except CurrencyNotFoundError:
            # Если валюта не найдена в реестре, все равно позволяем создать кошелек
            pass

        # Создаем кошелек если не существует
        wallet = portfolio.get_wallet(currency_code)
        if not wallet:
            wallet = portfolio.add_currency(currency_code)

        # Пополняем кошелек
        wallet.deposit(amount)

        # Получаем курс для расчета стоимости
        rates = self.db.load_rates()
        rate = None
        cost_in_usd = None

        pair = f"{currency_code}_USD"
        if "pairs" in rates and pair in rates["pairs"]:
            rate = rates["pairs"][pair]["rate"]
            cost_in_usd = amount * rate

        # Сохраняем изменения
        self.db.save_portfolio(portfolio)

        result = {
            "currency_code": currency_code,
            "amount": amount,
            "new_balance": wallet.balance,
            "rate": rate,
            "estimated_cost_usd": cost_in_usd,
        }

        return result

    @log_action("SELL", verbose=True)
    def sell_currency(
        self, user_id: int, currency_code: str, amount: float
    ) -> Dict[str, Any]:
        """Продает валюту"""
        # Валидация входных данных
        currency_code = validate_currency_code(currency_code)
        amount = validate_amount(amount)

        # Получаем портфель пользователя
        portfolio = self.db.get_portfolio_by_user_id(user_id)
        if not portfolio:
            raise ValueError("Портфель не найден")

        # Проверяем наличие кошелька
        wallet = portfolio.get_wallet(currency_code)
        if not wallet:
            raise ValueError(f"У вас нет кошелька '{currency_code}'")

        # Проверяем достаточность средств
        if amount > wallet.balance:
            raise InsufficientFundsError(
                available=wallet.balance, required=amount, code=currency_code
            )

        # Снимаем средства
        old_balance = wallet.balance
        wallet.withdraw(amount)

        # Получаем курс для расчета выручки
        rates = self.db.load_rates()
        rate = None
        revenue_in_usd = None

        pair = f"{currency_code}_USD"
        if "pairs" in rates and pair in rates["pairs"]:
            rate = rates["pairs"][pair]["rate"]
            revenue_in_usd = amount * rate

        # Сохраняем изменения
        self.db.save_portfolio(portfolio)

        result = {
            "currency_code": currency_code,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": wallet.balance,
            "rate": rate,
            "estimated_revenue_usd": revenue_in_usd,
        }

        return result

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Возвращает курс обмена между валютами"""
        # Валидация кодов валют
        from_currency = validate_currency_code(from_currency)
        to_currency = validate_currency_code(to_currency)

        # Проверяем валюты в реестре
        try:
            get_currency(from_currency)
            get_currency(to_currency)
        except CurrencyNotFoundError as e:
            raise CurrencyNotFoundError(e.code)

        # Получаем курсы из кэша
        rates = self.db.load_rates()

        # Проверяем актуальность данных
        pairs = rates.get("pairs", {})
        last_refresh = rates.get("last_refresh")

        if not pairs or not last_refresh:
            raise ApiRequestError("Нет данных о курсах. Выполните update-rates")

        # Проверяем свежесть данных
        if not is_rate_fresh(last_refresh, self.settings.rates_ttl_seconds):
            raise ApiRequestError("Данные устарели. Выполните update-rates")

        # Ищем прямой курс
        pair = f"{from_currency}_{to_currency}"
        if pair in pairs:
            return {
                "from": from_currency,
                "to": to_currency,
                "rate": pairs[pair]["rate"],
                "updated_at": pairs[pair]["updated_at"],
                "source": pairs[pair].get("source", "unknown"),
            }

        # Ищем обратный курс
        reverse_pair = f"{to_currency}_{from_currency}"
        if reverse_pair in pairs:
            return {
                "from": from_currency,
                "to": to_currency,
                "rate": 1.0 / pairs[reverse_pair]["rate"],
                "updated_at": pairs[reverse_pair]["updated_at"],
                "source": pairs[reverse_pair].get("source", "unknown"),
            }

        # Пробуем через USD
        if from_currency != "USD" and to_currency != "USD":
            usd_pair1 = f"{from_currency}_USD"
            usd_pair2 = f"USD_{to_currency}"

            if usd_pair1 in pairs and usd_pair2 in pairs:
                rate = pairs[usd_pair1]["rate"] * pairs[usd_pair2]["rate"]
                # Берем более свежее время обновления
                updated_at = max(
                    pairs[usd_pair1]["updated_at"], pairs[usd_pair2]["updated_at"]
                )
                return {
                    "from": from_currency,
                    "to": to_currency,
                    "rate": rate,
                    "updated_at": updated_at,
                    "source": "calculated",
                }

        raise ApiRequestError(f"Не удалось получить курс {from_currency}→{to_currency}")
